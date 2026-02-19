"""Concept Runner MCP Server — turn research ideas into markdown articles."""

import asyncio
import json
import logging
from datetime import datetime, timezone
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool
from sqlmodel import Session, select

from .database import get_engine
from .models import Concept, Paper, WebSource
from .services import gemini, pubmed, tavily

logger = logging.getLogger(__name__)

server = Server("concept-runner")

# ── Helpers ──


def _now():
    return datetime.now(timezone.utc)


def _get_concept(concept_id: int) -> Concept | None:
    with Session(get_engine()) as session:
        return session.get(Concept, concept_id)


def _update_concept(concept_id: int, **kwargs):
    with Session(get_engine()) as session:
        concept = session.get(Concept, concept_id)
        if not concept:
            return
        for k, v in kwargs.items():
            setattr(concept, k, v)
        concept.updated_at = _now()
        session.add(concept)
        session.commit()


def _fail_concept(concept_id: int, error: str):
    _update_concept(concept_id, status="failed", error_message=error)


def _json_loads(text: str | None) -> list | dict:
    if not text:
        return []
    return json.loads(text)


# ── Tool definitions ──


@server.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="concept_create",
            description="Create a new research concept from an idea. Gemini generates search queries and a slug. Use source='pubmed' for biomedical, 'web' for industry/tech/web3, 'both' for cross-domain.",
            inputSchema={
                "type": "object",
                "properties": {
                    "idea": {"type": "string", "description": "The research idea to explore"},
                    "source": {"type": "string", "enum": ["pubmed", "web", "both"], "description": "Search source: pubmed (biomedical), web (industry/tech via Tavily), both (default: pubmed)"},
                },
                "required": ["idea"],
            },
        ),
        Tool(
            name="concept_search",
            description="Search for sources matching the concept's queries. Uses PubMed, Tavily, or both depending on the concept's source setting.",
            inputSchema={
                "type": "object",
                "properties": {
                    "concept_id": {"type": "integer", "description": "The concept ID"},
                },
                "required": ["concept_id"],
            },
        ),
        Tool(
            name="concept_retrieve_fulltext",
            description="Retrieve full text for found sources. PubMed sources: PMC API. Web sources: Tavily Extract API.",
            inputSchema={
                "type": "object",
                "properties": {
                    "concept_id": {"type": "integer", "description": "The concept ID"},
                },
                "required": ["concept_id"],
            },
        ),
        Tool(
            name="concept_analyze",
            description="Analyze each paper using Gemini — extract key findings, methodology, limitations, and relevance.",
            inputSchema={
                "type": "object",
                "properties": {
                    "concept_id": {"type": "integer", "description": "The concept ID"},
                },
                "required": ["concept_id"],
            },
        ),
        Tool(
            name="concept_get_analyses",
            description="Get all analyses, source metadata, and search data for a concept. Use this to read the research data so you (the agent) can reflect on gaps and write the article yourself.",
            inputSchema={
                "type": "object",
                "properties": {
                    "concept_id": {"type": "integer", "description": "The concept ID"},
                },
                "required": ["concept_id"],
            },
        ),
        Tool(
            name="concept_save_article",
            description="Save the agent-written article back to the concept. Call this after you've written the article content yourself.",
            inputSchema={
                "type": "object",
                "properties": {
                    "concept_id": {"type": "integer", "description": "The concept ID"},
                    "title": {"type": "string", "description": "Article title"},
                    "excerpt": {"type": "string", "description": "1-2 sentence summary (max 200 chars)"},
                    "content": {"type": "string", "description": "Full markdown article body (no title heading)"},
                    "cover_image_url": {"type": "string", "description": "Public URL for cover image (e.g. from gemini_generate_image)"},
                    "sources": {
                        "type": "array",
                        "description": "List of source objects with ref, title, and pmid or url",
                        "items": {
                            "type": "object",
                            "properties": {
                                "ref": {"type": "integer"},
                                "title": {"type": "string"},
                                "pmid": {"type": "string"},
                                "url": {"type": "string"},
                            },
                            "required": ["ref", "title"],
                        },
                    },
                },
                "required": ["concept_id", "title", "content"],
            },
        ),
        Tool(
            name="concept_publish",
            description="Mark a concept as published. Sets completed_at timestamp.",
            inputSchema={
                "type": "object",
                "properties": {
                    "concept_id": {"type": "integer", "description": "The concept ID"},
                },
                "required": ["concept_id"],
            },
        ),
        Tool(
            name="concept_status",
            description="Get the current status of a concept including progress percentage and all pipeline data.",
            inputSchema={
                "type": "object",
                "properties": {
                    "concept_id": {"type": "integer", "description": "The concept ID"},
                },
                "required": ["concept_id"],
            },
        ),
        Tool(
            name="concept_list",
            description="List all concepts, optionally filtered by status.",
            inputSchema={
                "type": "object",
                "properties": {
                    "status": {"type": "string", "description": "Filter by status (optional)"},
                    "limit": {"type": "integer", "description": "Max results (default 20)"},
                },
            },
        ),
    ]


# ── Tool handlers ──


async def _handle_concept_create(arguments: dict) -> str:
    idea = arguments["idea"]
    source = arguments.get("source", "pubmed")
    if source not in ("pubmed", "web", "both"):
        source = "pubmed"

    # Adjust query generation prompt based on source
    if source == "pubmed":
        query_prompt = (
            "Given this research idea, generate 3-5 optimized PubMed search queries and a URL-friendly slug.\n\n"
            f"Research idea: {idea}\n\n"
            "Respond with JSON:\n"
            '{\n  "queries": ["query1", "query2", "query3"],\n  "slug": "short-url-slug"\n}\n\n'
            "Make queries specific with MeSH terms and Boolean operators where helpful.\n"
            "The slug should be 3-5 words separated by hyphens, descriptive of the topic."
        )
    elif source == "web":
        query_prompt = (
            "Given this research idea, generate 3-5 optimized web search queries and a URL-friendly slug.\n\n"
            f"Research idea: {idea}\n\n"
            "Respond with JSON:\n"
            '{\n  "queries": ["query1", "query2", "query3"],\n  "slug": "short-url-slug"\n}\n\n'
            "Make queries specific and varied to find authoritative articles, reports, and analysis.\n"
            "Include queries targeting industry reports, expert analysis, recent developments.\n"
            "The slug should be 3-5 words separated by hyphens, descriptive of the topic."
        )
    else:  # both
        query_prompt = (
            "Given this research idea, generate 3-5 search queries (mix of PubMed-style and web-style) and a URL-friendly slug.\n\n"
            f"Research idea: {idea}\n\n"
            "Respond with JSON:\n"
            '{\n  "queries": ["query1", "query2", "query3"],\n  "slug": "short-url-slug"\n}\n\n'
            "Include both academic-style queries (with MeSH terms) and general web queries targeting industry reports.\n"
            "The slug should be 3-5 words separated by hyphens, descriptive of the topic."
        )

    result = await gemini.chat_json(query_prompt)

    queries = result.get("queries", [])
    slug = result.get("slug", "untitled")

    with Session(get_engine()) as session:
        # Ensure unique slug
        existing = session.exec(select(Concept).where(Concept.slug == slug)).first()
        if existing:
            slug = f"{slug}-{int(_now().timestamp())}"

        concept = Concept(
            idea=idea,
            slug=slug,
            source=source,
            status="created",
            progress=5,
            search_queries=json.dumps(queries),
        )
        session.add(concept)
        session.commit()
        session.refresh(concept)

        return json.dumps({
            "concept_id": concept.id,
            "slug": concept.slug,
            "source": source,
            "search_queries": queries,
            "status": "created",
            "progress": 5,
        })


async def _search_pubmed_sources(concept: Concept, queries: list) -> list[dict]:
    """Search PubMed and return found paper dicts with pmid keys."""
    all_papers = {}

    for query_text in queries:
        pmids = await pubmed.search_pubmed(query_text, max_results=15)
        if not pmids:
            continue

        with Session(get_engine()) as session:
            cached = session.exec(select(Paper).where(Paper.pmid.in_(pmids))).all()
            cached_map = {p.pmid: p for p in cached}

        uncached_pmids = [p for p in pmids if p not in cached_map]
        new_papers = []
        if uncached_pmids:
            fetched = await pubmed.fetch_paper_metadata(uncached_pmids)
            with Session(get_engine()) as session:
                for p in fetched:
                    paper = Paper(
                        pmid=p["pmid"], pmc_id=p.get("pmc_id"), title=p["title"],
                        abstract=p.get("abstract"), authors=json.dumps(p.get("authors", [])),
                        journal=p.get("journal"), year=p.get("year"), doi=p.get("doi"),
                    )
                    session.merge(paper)
                    new_papers.append(p)
                session.commit()

        paper_list = []
        for pmid in pmids:
            if pmid in cached_map:
                p = cached_map[pmid]
                paper_list.append({"pmid": p.pmid, "title": p.title, "abstract": (p.abstract or "")[:300], "year": p.year})
            else:
                match = next((np for np in new_papers if np["pmid"] == pmid), None)
                if match:
                    paper_list.append({"pmid": match["pmid"], "title": match["title"], "abstract": (match.get("abstract") or "")[:300], "year": match.get("year")})

        if not paper_list:
            continue

        try:
            ranked = await gemini.chat_json(
                "Rank these papers by relevance to the research idea and query. Return only the top 5 most relevant.\n\n"
                f"Research idea: {concept.idea}\nSearch query: {query_text}\n\n"
                f"Papers:\n{json.dumps(paper_list, indent=1)}\n\n"
                'Respond with JSON:\n{\n  "top_pmids": ["pmid1", "pmid2", "pmid3", "pmid4", "pmid5"]\n}\n\n'
                "Select papers that are most directly relevant and cover diverse angles."
            )
            top_pmids = ranked.get("top_pmids", [p["pmid"] for p in paper_list[:5]])
        except Exception:
            top_pmids = [p["pmid"] for p in paper_list[:5]]

        for pmid in top_pmids:
            if pmid not in all_papers:
                match = next((p for p in paper_list if p["pmid"] == pmid), None)
                if match:
                    all_papers[pmid] = match

    return list(all_papers.values())


async def _search_web_sources(concept: Concept, queries: list) -> list[dict]:
    """Search web via Tavily and return found source dicts with url keys."""
    all_sources = {}  # url -> source dict

    for query_text in queries:
        results = await tavily.search_with_content(query_text, max_results=5)
        if not results:
            continue

        # Cache in DB
        with Session(get_engine()) as session:
            for r in results:
                url = r.get("url", "")
                if not url or url in all_sources:
                    continue
                ws = WebSource(
                    url=url,
                    title=r.get("title", ""),
                    snippet=r.get("content", ""),
                    fulltext=r.get("raw_content", "") or None,
                    domain=r.get("domain", ""),
                )
                session.merge(ws)
                all_sources[url] = {
                    "url": url,
                    "title": r.get("title", ""),
                    "snippet": (r.get("content") or "")[:300],
                    "domain": r.get("domain", ""),
                    "type": "web",
                }
            session.commit()

    # Rank with Gemini
    source_list = list(all_sources.values())
    if len(source_list) > 5:
        try:
            ranked = await gemini.chat_json(
                "Rank these web sources by relevance and authority for the research idea. Return the top 8 most relevant.\n\n"
                f"Research idea: {concept.idea}\n\n"
                f"Sources:\n{json.dumps(source_list, indent=1)}\n\n"
                'Respond with JSON:\n{\n  "top_urls": ["url1", "url2", ...]\n}\n\n'
                "Prefer authoritative sources, in-depth articles, and diverse perspectives."
            )
            top_urls = ranked.get("top_urls", [s["url"] for s in source_list[:8]])
            source_list = [s for s in source_list if s["url"] in top_urls]
        except Exception:
            source_list = source_list[:8]

    return source_list


async def _handle_concept_search(arguments: dict) -> str:
    concept_id = arguments["concept_id"]
    concept = _get_concept(concept_id)
    if not concept:
        return json.dumps({"error": "Concept not found"})

    _update_concept(concept_id, status="searching", progress=10)

    queries = _json_loads(concept.search_queries)
    if not queries:
        _fail_concept(concept_id, "No search queries found")
        return json.dumps({"error": "No search queries"})

    source = concept.source or "pubmed"
    new_found = []

    if source in ("pubmed", "both"):
        new_found.extend(await _search_pubmed_sources(concept, queries))

    if source in ("web", "both"):
        new_found.extend(await _search_web_sources(concept, queries))

    # Merge with existing found_papers
    existing = _json_loads(concept.found_papers)
    existing_keys = set()
    for p in existing:
        existing_keys.add(p.get("pmid") or p.get("url", ""))
    for item in new_found:
        key = item.get("pmid") or item.get("url", "")
        if key and key not in existing_keys:
            existing.append(item)
            existing_keys.add(key)

    _update_concept(concept_id, status="searching", progress=25, found_papers=json.dumps(existing))

    return json.dumps({
        "concept_id": concept_id,
        "source": source,
        "sources_found": len(existing),
        "new_sources": len(new_found),
        "status": "searching",
        "progress": 25,
    })


async def _handle_concept_retrieve_fulltext(arguments: dict) -> str:
    concept_id = arguments["concept_id"]
    concept = _get_concept(concept_id)
    if not concept:
        return json.dumps({"error": "Concept not found"})

    _update_concept(concept_id, status="retrieving", progress=28)

    found_items = _json_loads(concept.found_papers)
    if not found_items:
        _update_concept(concept_id, progress=40)
        return json.dumps({"concept_id": concept_id, "message": "No sources to retrieve", "progress": 40})

    retrieved_count = 0

    # Separate PubMed papers and web sources
    pubmed_items = [p for p in found_items if p.get("pmid")]
    web_items = [p for p in found_items if p.get("type") == "web" and p.get("url")]

    # PubMed fulltext retrieval (PMC API)
    if pubmed_items:
        with Session(get_engine()) as session:
            for paper_dict in pubmed_items:
                pmid = paper_dict["pmid"]
                db_paper = session.get(Paper, pmid)
                if not db_paper:
                    continue
                if db_paper.fulltext:
                    retrieved_count += 1
                    continue
                pmc_id = db_paper.pmc_id
                if not pmc_id:
                    if db_paper.abstract:
                        db_paper.fulltext = f"[Abstract only]\n{db_paper.abstract}"
                        retrieved_count += 1
                    continue
                fulltext = await pubmed.fetch_pmc_fulltext(pmc_id)
                if fulltext:
                    db_paper.fulltext = fulltext
                    retrieved_count += 1
                elif db_paper.abstract:
                    db_paper.fulltext = f"[Abstract only]\n{db_paper.abstract}"
                    retrieved_count += 1
            session.commit()

    # Web fulltext retrieval (Tavily Extract)
    if web_items:
        # Find URLs that need extraction (no fulltext in cache yet)
        urls_to_extract = []
        with Session(get_engine()) as session:
            for item in web_items:
                url = item["url"]
                ws = session.exec(select(WebSource).where(WebSource.url == url)).first()
                if ws and ws.fulltext:
                    retrieved_count += 1
                else:
                    urls_to_extract.append(url)

        if urls_to_extract:
            extracted = await tavily.extract_urls(urls_to_extract)
            with Session(get_engine()) as session:
                for ext in extracted:
                    url = ext.get("url", "")
                    raw = ext.get("raw_content", "")
                    if not url or not raw:
                        continue
                    ws = session.exec(select(WebSource).where(WebSource.url == url)).first()
                    if ws:
                        ws.fulltext = raw[:15000]
                    else:
                        ws = WebSource(url=url, fulltext=raw[:15000])
                        session.add(ws)
                    retrieved_count += 1
                session.commit()

    _update_concept(concept_id, status="retrieving", progress=40)

    return json.dumps({
        "concept_id": concept_id,
        "sources_with_text": retrieved_count,
        "total_sources": len(found_items),
        "status": "retrieving",
        "progress": 40,
    })


async def _handle_concept_analyze(arguments: dict) -> str:
    concept_id = arguments["concept_id"]
    concept = _get_concept(concept_id)
    if not concept:
        return json.dumps({"error": "Concept not found"})

    _update_concept(concept_id, status="analyzing", progress=42)

    found_items = _json_loads(concept.found_papers)
    if not found_items:
        _update_concept(concept_id, progress=60)
        return json.dumps({"concept_id": concept_id, "message": "No sources to analyze", "progress": 60})

    existing_analyses = _json_loads(concept.paper_analyses)
    analyzed_keys = set()
    for a in existing_analyses:
        analyzed_keys.add(a.get("pmid") or a.get("url", ""))

    new_analyses = []

    with Session(get_engine()) as session:
        for item in found_items:
            pmid = item.get("pmid")
            url = item.get("url")
            key = pmid or url or ""
            if not key or key in analyzed_keys:
                continue

            if pmid:
                # PubMed paper analysis
                db_paper = session.get(Paper, pmid)
                if not db_paper:
                    continue
                text_preview = (db_paper.fulltext or db_paper.abstract or "")[:12000]
                if not text_preview:
                    continue
                authors = _json_loads(db_paper.authors)
                author_str = ", ".join(authors[:5]) if authors else "Unknown"
                try:
                    analysis = await gemini.chat_json(
                        "Analyze this scientific paper and provide a structured summary.\n\n"
                        f"Title: {db_paper.title}\nAuthors: {author_str}\n"
                        f"Journal: {db_paper.journal or 'Unknown'} ({db_paper.year or 'Unknown'})\n\n"
                        f"Text:\n{text_preview}\n\n"
                        "Respond with JSON:\n{\n"
                        '  "key_findings": ["finding1", "finding2", "finding3"],\n'
                        '  "methodology": "brief description of methods used",\n'
                        '  "limitations": ["limitation1", "limitation2"],\n'
                        '  "relevance": "how this relates to the broader research topic",\n'
                        '  "confidence": "high/medium/low - quality and reliability assessment"\n}'
                    )
                    analysis["pmid"] = pmid
                    analysis["title"] = db_paper.title
                    new_analyses.append(analysis)
                except Exception as e:
                    logger.warning(f"Analysis failed for PMID {pmid}: {e}")

            elif url:
                # Web source analysis
                ws = session.exec(select(WebSource).where(WebSource.url == url)).first()
                text_preview = ""
                title = item.get("title", "")
                if ws:
                    text_preview = (ws.fulltext or ws.snippet or "")[:12000]
                    title = ws.title or title
                if not text_preview:
                    continue
                try:
                    analysis = await gemini.chat_json(
                        "Analyze this web article and provide a structured summary.\n\n"
                        f"Title: {title}\nURL: {url}\nDomain: {item.get('domain', '')}\n\n"
                        f"Text:\n{text_preview}\n\n"
                        "Respond with JSON:\n{\n"
                        '  "key_findings": ["finding1", "finding2", "finding3"],\n'
                        '  "methodology": "brief description of the approach or evidence presented",\n'
                        '  "limitations": ["limitation1", "limitation2"],\n'
                        '  "relevance": "how this relates to the broader research topic",\n'
                        '  "confidence": "high/medium/low - source credibility and evidence quality"\n}'
                    )
                    analysis["url"] = url
                    analysis["title"] = title
                    new_analyses.append(analysis)
                except Exception as e:
                    logger.warning(f"Analysis failed for URL {url}: {e}")

    all_analyses = existing_analyses + new_analyses
    _update_concept(concept_id, status="analyzing", progress=60, paper_analyses=json.dumps(all_analyses))

    return json.dumps({
        "concept_id": concept_id,
        "sources_analyzed": len(all_analyses),
        "new_analyses": len(new_analyses),
        "status": "analyzing",
        "progress": 60,
    })


async def _handle_concept_get_analyses(arguments: dict) -> str:
    concept_id = arguments["concept_id"]
    concept = _get_concept(concept_id)
    if not concept:
        return json.dumps({"error": "Concept not found"})

    analyses = _json_loads(concept.paper_analyses)
    found_papers = _json_loads(concept.found_papers)
    search_queries = _json_loads(concept.search_queries)

    # Build enriched analyses with source metadata
    enriched = []
    with Session(get_engine()) as session:
        for a in analyses:
            entry = dict(a)
            pmid = a.get("pmid")
            url = a.get("url")
            if pmid:
                db_paper = session.get(Paper, pmid)
                if db_paper:
                    entry["authors"] = _json_loads(db_paper.authors)[:5]
                    entry["journal"] = db_paper.journal
                    entry["year"] = db_paper.year
                    entry["doi"] = db_paper.doi
                    entry["has_fulltext"] = bool(db_paper.fulltext and not db_paper.fulltext.startswith("[Abstract only]"))
            elif url:
                ws = session.exec(select(WebSource).where(WebSource.url == url)).first()
                if ws:
                    entry["domain"] = ws.domain
                    entry["has_fulltext"] = bool(ws.fulltext)
            enriched.append(entry)

    return json.dumps({
        "concept_id": concept_id,
        "idea": concept.idea,
        "source": concept.source,
        "status": concept.status,
        "progress": concept.progress,
        "gap_iteration": concept.gap_iteration,
        "search_queries": search_queries,
        "found_sources_count": len(found_papers),
        "analyses": enriched,
    })


async def _handle_concept_save_article(arguments: dict) -> str:
    concept_id = arguments["concept_id"]
    concept = _get_concept(concept_id)
    if not concept:
        return json.dumps({"error": "Concept not found"})

    title = arguments["title"]
    content = arguments["content"]
    excerpt = arguments.get("excerpt", "")
    cover_image_url = arguments.get("cover_image_url")
    sources = arguments.get("sources", [])

    update_kwargs = dict(
        status="writing",
        progress=90,
        title=title,
        excerpt=excerpt,
        content=content,
        sources=json.dumps(sources) if sources else None,
    )
    if cover_image_url:
        update_kwargs["cover_image_path"] = cover_image_url

    _update_concept(concept_id, **update_kwargs)

    return json.dumps({
        "concept_id": concept_id,
        "title": title,
        "excerpt": excerpt,
        "content_length": len(content),
        "sources_count": len(sources),
        "cover_image_url": cover_image_url,
        "status": "writing",
        "progress": 90,
    })


async def _handle_concept_publish(arguments: dict) -> str:
    concept_id = arguments["concept_id"]
    concept = _get_concept(concept_id)
    if not concept:
        return json.dumps({"error": "Concept not found"})

    if not concept.content:
        return json.dumps({"error": "No content to publish. Save an article with concept_save_article first."})

    _update_concept(
        concept_id,
        status="published",
        progress=100,
        completed_at=_now(),
    )

    return json.dumps({
        "concept_id": concept_id,
        "slug": concept.slug,
        "title": concept.title,
        "slug_path": f"/research/{concept.slug}",
        "status": "published",
        "progress": 100,
    })


async def _handle_concept_status(arguments: dict) -> str:
    concept_id = arguments["concept_id"]
    concept = _get_concept(concept_id)
    if not concept:
        return json.dumps({"error": "Concept not found"})

    return json.dumps({
        "concept_id": concept.id,
        "idea": concept.idea,
        "slug": concept.slug,
        "source": concept.source,
        "status": concept.status,
        "progress": concept.progress,
        "gap_iteration": concept.gap_iteration,
        "title": concept.title,
        "excerpt": concept.excerpt,
        "has_content": bool(concept.content),
        "content_length": len(concept.content) if concept.content else 0,
        "cover_image_path": concept.cover_image_path,
        "search_queries_count": len(_json_loads(concept.search_queries)),
        "found_papers_count": len(_json_loads(concept.found_papers)),
        "paper_analyses_count": len(_json_loads(concept.paper_analyses)),
        "sources_count": len(_json_loads(concept.sources)),
        "error_message": concept.error_message,
        "created_at": concept.created_at.isoformat(),
        "updated_at": concept.updated_at.isoformat(),
        "completed_at": concept.completed_at.isoformat() if concept.completed_at else None,
    })


async def _handle_concept_list(arguments: dict) -> str:
    status_filter = arguments.get("status")
    limit = arguments.get("limit", 20)

    with Session(get_engine()) as session:
        q = select(Concept)
        if status_filter:
            q = q.where(Concept.status == status_filter)
        q = q.order_by(Concept.created_at.desc()).limit(limit)
        concepts = session.exec(q).all()

    return json.dumps([
        {
            "concept_id": c.id,
            "idea": c.idea[:100],
            "slug": c.slug,
            "title": c.title,
            "status": c.status,
            "progress": c.progress,
            "created_at": c.created_at.isoformat(),
        }
        for c in concepts
    ])


# ── Dispatcher ──


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    handlers = {
        "concept_create": _handle_concept_create,
        "concept_search": _handle_concept_search,
        "concept_retrieve_fulltext": _handle_concept_retrieve_fulltext,
        "concept_analyze": _handle_concept_analyze,
        "concept_get_analyses": _handle_concept_get_analyses,
        "concept_save_article": _handle_concept_save_article,
        "concept_publish": _handle_concept_publish,
        "concept_status": _handle_concept_status,
        "concept_list": _handle_concept_list,
    }
    handler = handlers.get(name)
    if not handler:
        return [TextContent(type="text", text=f"Unknown tool: {name}")]

    try:
        result = await handler(arguments)
    except Exception as e:
        logger.exception(f"Error in tool {name}")
        cid = arguments.get("concept_id")
        if cid:
            try:
                _fail_concept(cid, str(e))
            except Exception:
                pass
        result = json.dumps({"error": str(e)})

    return [TextContent(type="text", text=result)]


# ── Entry point ──


async def run():
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options(),
        )


def main():
    asyncio.run(run())


if __name__ == "__main__":
    main()

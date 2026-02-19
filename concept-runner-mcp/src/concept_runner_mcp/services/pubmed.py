"""PubMed / NCBI service — search, metadata, and PMC fulltext retrieval."""

import asyncio
import logging
import os

import httpx
from Bio import Entrez
from xml.etree import ElementTree as ET

logger = logging.getLogger(__name__)

Entrez.email = os.environ.get("NCBI_EMAIL", "research@loader.land")


async def search_pubmed(query: str, max_results: int = 10) -> list[str]:
    """Search PubMed and return a list of PMIDs."""
    def _search():
        handle = Entrez.esearch(db="pubmed", term=query, retmax=max_results, sort="relevance")
        record = Entrez.read(handle)
        handle.close()
        return record.get("IdList", [])

    try:
        return await asyncio.to_thread(_search)
    except Exception as e:
        logger.exception(f"PubMed search failed: {e}")
        return []


async def fetch_paper_metadata(pmids: list[str]) -> list[dict]:
    """Fetch metadata for a list of PMIDs from NCBI."""
    if not pmids:
        return []

    def _fetch():
        handle = Entrez.efetch(db="pubmed", id=",".join(pmids), rettype="xml", retmode="xml")
        xml_data = handle.read()
        handle.close()
        root = ET.fromstring(xml_data)

        papers = []
        for article in root.findall(".//PubmedArticle"):
            medline = article.find(".//MedlineCitation")
            if medline is None:
                continue

            pmid_el = medline.find("PMID")
            pmid = pmid_el.text if pmid_el is not None else ""

            article_el = medline.find("Article")
            if article_el is None:
                continue

            # Title
            title_el = article_el.find("ArticleTitle")
            title = "".join(title_el.itertext()) if title_el is not None else ""

            # Abstract
            abstract_parts = []
            abstract_el = article_el.find("Abstract")
            if abstract_el is not None:
                for at in abstract_el.findall("AbstractText"):
                    label = at.get("Label", "")
                    text = "".join(at.itertext())
                    if label:
                        abstract_parts.append(f"{label}: {text}")
                    else:
                        abstract_parts.append(text)
            abstract = "\n".join(abstract_parts)

            # Authors
            authors = []
            author_list = article_el.find("AuthorList")
            if author_list is not None:
                for author in author_list.findall("Author"):
                    last = author.findtext("LastName", "")
                    first = author.findtext("ForeName", "")
                    if last:
                        authors.append(f"{last} {first}".strip())

            # Journal
            journal_el = article_el.find("Journal/Title")
            journal = journal_el.text if journal_el is not None else ""

            # Year
            year = ""
            pub_date = article_el.find("Journal/JournalIssue/PubDate")
            if pub_date is not None:
                year_el = pub_date.find("Year")
                if year_el is not None:
                    year = year_el.text

            # DOI
            doi = ""
            for id_el in article.findall(".//ArticleId"):
                if id_el.get("IdType") == "doi":
                    doi = id_el.text or ""
                    break

            # PMC ID
            pmc_id = ""
            for id_el in article.findall(".//ArticleId"):
                if id_el.get("IdType") == "pmc":
                    pmc_id = id_el.text or ""
                    break

            papers.append({
                "pmid": pmid,
                "pmc_id": pmc_id,
                "title": title,
                "abstract": abstract,
                "authors": authors,
                "journal": journal,
                "year": year,
                "doi": doi,
            })

        return papers

    try:
        return await asyncio.to_thread(_fetch)
    except Exception as e:
        logger.exception(f"PubMed metadata fetch failed: {e}")
        return []


async def fetch_pmc_fulltext(pmc_id: str, max_chars: int = 15000) -> str | None:
    """Fetch full text from PMC via BioC XML API."""
    url = f"https://www.ncbi.nlm.nih.gov/research/bionlp/RESTful/pmcoa.cgi/BioC_xml/{pmc_id}/unicode"
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(url)
            if response.status_code != 200:
                return None

            root = ET.fromstring(response.text)
            passages = []
            for passage in root.findall(".//passage"):
                text_el = passage.find("text")
                if text_el is not None and text_el.text:
                    passages.append(text_el.text)

            fulltext = "\n\n".join(passages)
            if len(fulltext) > max_chars:
                fulltext = fulltext[:max_chars] + "\n\n[Truncated]"
            return fulltext if fulltext else None

    except Exception as e:
        logger.exception(f"PMC fulltext fetch failed for {pmc_id}: {e}")
        return None

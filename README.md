# Local Agent MCPs

MCP (Model Context Protocol) servers designed for local AI agents. These tools give your agent the ability to **edit code** and **write research articles** autonomously.

Agents with persistent memory benefit the most from these tools — a memory-equipped agent can track ongoing projects, recall past research topics, remember coding patterns across sessions, and make increasingly informed decisions over time. Without memory, each invocation starts from scratch; with memory, the agent builds expertise.

## Servers

### code-mcp

An MCP server that wraps the [Claude Code](https://docs.anthropic.com/en/docs/claude-code) CLI, giving your agent the ability to perform coding tasks with **session persistence**. Subsequent calls within the same working directory automatically resume the previous session, so Claude remembers all prior edits, file reads, and context.

**Tool: `code`**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `task` | string | Yes | The coding task to perform |
| `cwd` | string | No | Working directory (default: server's cwd) |
| `model` | string | No | Model: `sonnet`, `opus`, `haiku` |
| `max_turns` | integer | No | Max agentic turns (default: 60) |
| `new_session` | boolean | No | Force a fresh session |

**Environment Variables:**

| Variable | Default | Description |
|----------|---------|-------------|
| `CLAUDE_CLI` | `claude` | Path to Claude Code CLI binary |
| `CODE_MCP_MODEL` | `opus` | Default model |
| `CODE_MCP_MAX_TURNS` | `60` | Default max turns |

### concept-runner-mcp

An MCP server that turns research ideas into structured markdown articles. It orchestrates a multi-step pipeline: idea → search queries → source discovery → full-text retrieval → AI analysis → agent-written article.

Supports three source modes:
- **`pubmed`** — biomedical literature via PubMed/NCBI
- **`web`** — industry/tech articles via Tavily
- **`both`** — cross-domain research

**Tools (9 total):**

| Tool | Description |
|------|-------------|
| `concept_create` | Create a new research concept from an idea |
| `concept_search` | Search for sources matching the concept's queries |
| `concept_retrieve_fulltext` | Retrieve full text for found sources |
| `concept_analyze` | Analyze each source using Gemini |
| `concept_get_analyses` | Get all analyses for agent reflection and writing |
| `concept_save_article` | Save the agent-written article |
| `concept_publish` | Mark a concept as published |
| `concept_status` | Get current status and progress |
| `concept_list` | List all concepts |

**Pipeline:** `created` → `searching` → `retrieving` → `analyzing` → `reflecting` → `writing` → `published`

**Environment Variables:**

| Variable | Default | Description |
|----------|---------|-------------|
| `GOOGLE_API_KEY` | (required) | Google Gemini API key |
| `TAVILY_API_KEY` | (required for web search) | Tavily API key |
| `NCBI_EMAIL` | `research@loader.land` | Email for PubMed API (set your own) |
| `GEMINI_MODEL` | `gemini-2.5-flash` | Gemini model to use |
| `DATA_DIR` | `./data` (relative to package) | SQLite database directory |

## Installation & Usage

### Prerequisites

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) (recommended) or pip
- [Claude Code CLI](https://docs.anthropic.com/en/docs/claude-code) installed (for code-mcp)
- API keys as needed (Gemini, Tavily)

### Running with uv (recommended)

```bash
# code-mcp
uv run --directory /path/to/local-agent-mcps/code-mcp code-mcp

# concept-runner-mcp
GOOGLE_API_KEY=your-key TAVILY_API_KEY=your-key \
  uv run --directory /path/to/local-agent-mcps/concept-runner-mcp concept-runner-mcp
```

### Running with pip

```bash
# code-mcp
cd code-mcp
pip install -e .
code-mcp

# concept-runner-mcp
cd concept-runner-mcp
pip install -e .
GOOGLE_API_KEY=your-key concept-runner-mcp
```

### Connecting to Claude Code

Add to your `.mcp.json` (or Claude Desktop config):

```json
{
  "mcpServers": {
    "code-mcp": {
      "command": "uv",
      "args": ["run", "--directory", "/path/to/local-agent-mcps/code-mcp", "code-mcp"]
    },
    "concept-runner-mcp": {
      "command": "uv",
      "args": ["run", "--directory", "/path/to/local-agent-mcps/concept-runner-mcp", "concept-runner-mcp"],
      "env": {
        "GOOGLE_API_KEY": "your-google-api-key",
        "TAVILY_API_KEY": "your-tavily-api-key"
      }
    }
  }
}
```

### Connecting to Claude Agent SDK

```python
from claude_agent_sdk import McpStdioServerConfig

mcp_servers = [
    McpStdioServerConfig(
        command="uv",
        args=["run", "--directory", "/path/to/code-mcp", "code-mcp"],
        env={"CODE_MCP_MODEL": "sonnet"},
    ),
    McpStdioServerConfig(
        command="uv",
        args=["run", "--directory", "/path/to/concept-runner-mcp", "concept-runner-mcp"],
        env={
            "GOOGLE_API_KEY": "your-key",
            "TAVILY_API_KEY": "your-key",
        },
    ),
]
```

## Why Memory Matters / 為什麼記憶很重要

These MCP servers are designed to be used by AI agents. While they work with any MCP-compatible client, agents with **persistent memory** unlock their full potential:

- **code-mcp** maintains session context *within* a single agent run. But an agent with memory can recall *across* runs — remembering which files were modified, what patterns were established, and what architectural decisions were made in previous sessions.
- **concept-runner-mcp** builds research articles through a multi-step pipeline. A memory-equipped agent can track which topics have been explored, avoid duplicate research, build on previous findings, and develop a coherent body of work over time.

Without memory, every agent invocation is isolated. With memory, the agent becomes a persistent collaborator that grows more effective with each interaction.

---

# Local Agent MCPs（本地代理 MCP 工具）

專為本地 AI 代理設計的 MCP（Model Context Protocol）伺服器。這些工具讓你的 AI 代理能夠**自主編輯程式碼**並**撰寫研究文章**。

擁有持久記憶的代理能從這些工具中獲得最大效益——具備記憶的代理可以追蹤進行中的專案、回憶過去的研究主題、記住跨 session 的程式碼模式，並隨著時間做出越來越明智的決策。沒有記憶，每次呼叫都從零開始；有了記憶，代理會不斷累積專業知識。

## 伺服器

### code-mcp

封裝 [Claude Code](https://docs.anthropic.com/en/docs/claude-code) CLI 的 MCP 伺服器，讓你的代理能夠執行程式碼任務，並具有**對話持久性**。在同一工作目錄中的後續呼叫會自動恢復先前的 session，因此 Claude 會記住所有先前的編輯、檔案讀取和上下文。

**工具：`code`**

| 參數 | 類型 | 必填 | 說明 |
|------|------|------|------|
| `task` | string | 是 | 要執行的程式碼任務 |
| `cwd` | string | 否 | 工作目錄（預設：伺服器的工作目錄） |
| `model` | string | 否 | 模型：`sonnet`、`opus`、`haiku` |
| `max_turns` | integer | 否 | 最大代理回合數（預設：60） |
| `new_session` | boolean | 否 | 強制開始新 session |

**環境變數：**

| 變數 | 預設值 | 說明 |
|------|--------|------|
| `CLAUDE_CLI` | `claude` | Claude Code CLI 的路徑 |
| `CODE_MCP_MODEL` | `opus` | 預設模型 |
| `CODE_MCP_MAX_TURNS` | `60` | 預設最大回合數 |

### concept-runner-mcp

將研究構想轉化為結構化 Markdown 文章的 MCP 伺服器。它協調一個多步驟流程：構想 → 搜尋查詢 → 來源發現 → 全文擷取 → AI 分析 → 代理撰寫文章。

支援三種來源模式：
- **`pubmed`** — 透過 PubMed/NCBI 搜尋生物醫學文獻
- **`web`** — 透過 Tavily 搜尋產業/科技文章
- **`both`** — 跨領域研究

**工具（共 9 個）：**

| 工具 | 說明 |
|------|------|
| `concept_create` | 從構想建立新的研究概念 |
| `concept_search` | 搜尋符合概念查詢的來源 |
| `concept_retrieve_fulltext` | 擷取找到的來源的全文 |
| `concept_analyze` | 使用 Gemini 分析每個來源 |
| `concept_get_analyses` | 取得所有分析結果供代理反思和寫作 |
| `concept_save_article` | 儲存代理撰寫的文章 |
| `concept_publish` | 標記概念為已發佈 |
| `concept_status` | 取得目前狀態和進度 |
| `concept_list` | 列出所有概念 |

**流程：** `created` → `searching` → `retrieving` → `analyzing` → `reflecting` → `writing` → `published`

**環境變數：**

| 變數 | 預設值 | 說明 |
|------|--------|------|
| `GOOGLE_API_KEY` | （必填） | Google Gemini API 金鑰 |
| `TAVILY_API_KEY` | （web 搜尋必填） | Tavily API 金鑰 |
| `NCBI_EMAIL` | `research@loader.land` | PubMed API 的電子郵件（請設定你自己的） |
| `GEMINI_MODEL` | `gemini-2.5-flash` | 使用的 Gemini 模型 |
| `DATA_DIR` | `./data`（相對於套件） | SQLite 資料庫目錄 |

## 安裝與使用

### 前置需求

- Python 3.11+
- [uv](https://docs.astral.sh/uv/)（建議）或 pip
- 已安裝 [Claude Code CLI](https://docs.anthropic.com/en/docs/claude-code)（code-mcp 需要）
- 所需的 API 金鑰（Gemini、Tavily）

### 使用 uv 執行（建議）

```bash
# code-mcp
uv run --directory /path/to/local-agent-mcps/code-mcp code-mcp

# concept-runner-mcp
GOOGLE_API_KEY=your-key TAVILY_API_KEY=your-key \
  uv run --directory /path/to/local-agent-mcps/concept-runner-mcp concept-runner-mcp
```

### 使用 pip 執行

```bash
# code-mcp
cd code-mcp
pip install -e .
code-mcp

# concept-runner-mcp
cd concept-runner-mcp
pip install -e .
GOOGLE_API_KEY=your-key concept-runner-mcp
```

### 連接到 Claude Code

在你的 `.mcp.json`（或 Claude Desktop 設定）中加入：

```json
{
  "mcpServers": {
    "code-mcp": {
      "command": "uv",
      "args": ["run", "--directory", "/path/to/local-agent-mcps/code-mcp", "code-mcp"]
    },
    "concept-runner-mcp": {
      "command": "uv",
      "args": ["run", "--directory", "/path/to/local-agent-mcps/concept-runner-mcp", "concept-runner-mcp"],
      "env": {
        "GOOGLE_API_KEY": "your-google-api-key",
        "TAVILY_API_KEY": "your-tavily-api-key"
      }
    }
  }
}
```

### 連接到 Claude Agent SDK

```python
from claude_agent_sdk import McpStdioServerConfig

mcp_servers = [
    McpStdioServerConfig(
        command="uv",
        args=["run", "--directory", "/path/to/code-mcp", "code-mcp"],
        env={"CODE_MCP_MODEL": "sonnet"},
    ),
    McpStdioServerConfig(
        command="uv",
        args=["run", "--directory", "/path/to/concept-runner-mcp", "concept-runner-mcp"],
        env={
            "GOOGLE_API_KEY": "your-key",
            "TAVILY_API_KEY": "your-key",
        },
    ),
]
```

## 為什麼記憶很重要

這些 MCP 伺服器專為 AI 代理設計。雖然它們可以與任何 MCP 相容的客戶端搭配使用，但具有**持久記憶**的代理能釋放它們的全部潛力：

- **code-mcp** 在單次代理執行*期間*維持 session 上下文。但具有記憶的代理可以*跨執行*回憶——記住哪些檔案被修改過、建立了什麼模式，以及先前 session 中做出的架構決策。
- **concept-runner-mcp** 透過多步驟流程建構研究文章。具備記憶的代理可以追蹤已探索的主題、避免重複研究、基於先前的發現持續發展，並隨時間建立一套連貫的知識體系。

沒有記憶，每次代理呼叫都是孤立的。有了記憶，代理成為一個持續的協作者，每次互動都更有效率。

## License

MIT

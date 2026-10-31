# Claude Code to Google Antigravity Tool Mapping (TOOL_GLOSSARY.md)

When executing canonical specifications inside `.claude/commands/*.md` and `.claude/skills/**/*.md` on **Google Antigravity**, map Claude Code tool names and conventions to their native Antigravity equivalents:

| Claude Code Reference | Google Antigravity Equivalent | Notes |
| :--- | :--- | :--- |
| `Read` (file / PDF) | `view_file` / `read_file` | Use on `.tex`, `.md`, and compiled `.pdf` files for visual layout inspection. |
| `Write` / `Edit` / `MultiEdit` | `write_to_file` / `edit_file` | Edit profile files and LaTeX drafts in place. |
| `Bash(...)` | `run_command` / terminal execution | Run `bun`, `python3`, `lualatex`, `xelatex`, and `tools/*.py` scripts. |
| `WebFetch` | `read_url_content` | Fetch job postings or company pages (after `tools/robots_check.py` / `tools/fetch_page.py`). |
| `WebSearch` | `search_web` | Independently verify company facts, products, and salary benchmarks. |
| `Task` / Subagent spawn | `invoke_subagent` (or fresh critique pass) | Used in `/apply` Step 4 (Reviewer Agent) and `/rank` parallel scoring. |
| `AskUserQuestion` | `ask_question` / direct chat prompt | Pause for human confirmation before proceeding with drafting or saving outcomes. |
| `mcp__claude_ai_Gmail__*` (`list_labels`, `search_threads`, `get_thread`, `get_message`) | `mcp_gmail_*` or `call_mcp_tool` (`ServerName: "gmail"`) | Provided by the local `tools/gmail_mcp_server.py` stdio MCP server (standard Gmail API v1 OAuth, no Developer Preview account needed). |
| `mcp__notion__*` | `mcp_notion_*` or `call_mcp_tool` (`ServerName: "notion"`) | Used by `/notion-sync` to publish ranked jobs and applications to Notion. |
| `Claude Code` (in CV/Cover Letter) | `Google Antigravity` / `Gemini` | When a spec says to reference Claude Code for agentic workflows, reference Google Antigravity / Gemini as appropriate. |

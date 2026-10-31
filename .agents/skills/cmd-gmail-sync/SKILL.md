---
name: gmail-sync
description: "Scan Gmail for application status signals and propose batch updates for approval. Triggered when the user types /gmail-sync or asks to run the gmail-sync workflow."
---
# /gmail-sync — Thin-Pointer Skill for Google Antigravity

1. Read and follow the canonical command specification in `.claude/commands/gmail-sync.md` step by step.
2. Consult `AGENTS.md`, `CLAUDE.md`, and `.claude/skills/job-application-assistant/` as the single source of truth for candidate profile data and evaluation rules.
3. Map any Claude Code tool names in `.claude/commands/gmail-sync.md` to Google Antigravity tools using `TOOL_GLOSSARY.md` (specifically, treat the `gmail` MCP server tools `mcp_gmail_list_labels`, `mcp_gmail_search_threads`, `mcp_gmail_get_thread`, `mcp_gmail_get_message` — or `call_mcp_tool` with `ServerName: "gmail"` — as satisfying the `mcp__claude_ai_Gmail__*` prerequisite in Step 0).

---
name: scrape
description: "Search enabled job portals under .agents/skills/*-search, deduplicate postings against job_scraper/seen_jobs.json, and present matches sorted by fit. Triggered when the user types /scrape or asks to run the scrape workflow."
---
# /scrape — Thin-Pointer Skill for Google Antigravity

1. Read and follow the canonical command specification in `.claude/commands/scrape.md` step by step.
2. Consult `AGENTS.md`, `CLAUDE.md`, and `.claude/skills/job-application-assistant/` as the single source of truth for candidate profile data and evaluation rules.
3. Map any Claude Code tool names in `.claude/commands/scrape.md` to Google Antigravity tools using `TOOL_GLOSSARY.md`.

#!/usr/bin/env python3
"""
Bootstrap Google Antigravity thin-pointer skills & tool glossary for ai-job-search.
Run this script from the root of your ai-job-search repository:
    python3 setup_antigravity.py
"""
import os
from pathlib import Path

COMMANDS = {
    "setup": "Onboard and populate your candidate profile (CLAUDE.md and .claude/skills/job-application-assistant/01..07) from documents/, a pasted CV, or an interactive interview.",
    "scrape": "Search enabled job portals under .agents/skills/*-search, deduplicate postings against job_scraper/seen_jobs.json, and present matches sorted by fit.",
    "rank": "Batch-score newly scraped postings against the 5-dimension evaluation framework in .claude/skills/job-application-assistant/04-job-evaluation.md.",
    "apply": "Run the end-to-end drafter-reviewer application workflow: posting integrity gate, fit evaluation, tailored LaTeX CV & cover letter, independent review pass, PDF compilation (lualatex/xelatex), layout check, and ATS text verification.",
    "interview": "Build a stage-specific interview preparation pack from the application archive, verify company/interviewer facts, map questions to STAR examples, and run a mock interview.",
    "outcome": "Record application outcomes (interview stages, offers, rejections, silence), archive submitted materials, and draft follow-up or thank-you notes.",
    "expand": "Enrich your candidate profile by scanning linked public sources (GitHub, portfolio, Kaggle, Google Scholar) and course syllabi.",
    "upskill": "Analyze skill gaps across tracked and ranked job postings and generate a prioritized learning plan.",
    "html-report": "Generate a self-contained offline HTML dashboard from job_search_tracker.csv and application archives.",
    "notion-sync": "Publish a one-way read-only pipeline view to a Notion database via MCP.",
    "gmail-sync": "Scan Gmail for application status signals and propose batch updates for approval.",
    "add-template": "Register and test-compile a custom CV or cover letter template (LaTeX, Typst, etc.).",
    "add-portal": "Investigate a job board URL, scaffold a contract-compliant Bun CLI skill under .agents/skills/<name>-search, and test-run a live query.",
    "reset": "Reset personalized profile files back to clean [YOUR_*] placeholders or clear the documents folder."
}

CORE_SKILLS = {
    "job-application-assistant": (
        ".claude/skills/job-application-assistant/SKILL.md",
        "Core candidate profile, behavioral profile, writing style, job fit rubric, LaTeX CV/cover letter templates, and interview prep methodology."
    ),
    "job-scraper": (
        ".claude/skills/job-scraper/SKILL.md",
        "Orchestrates all enabled portal search CLIs in .agents/skills/*-search and manages job_scraper/seen_jobs.json."
    ),
    "upskill- methodology": (
        ".claude/skills/upskill/SKILL.md",
        "Methodology for skill gap heatmap generation and study plan curation."
    )
}

TOOL_GLOSSARY = """# Claude Code to Google Antigravity Tool Mapping (TOOL_GLOSSARY.md)

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
| `Claude Code` (in CV/Cover Letter) | `Google Antigravity` / `Gemini` | When a spec says to reference Claude Code for agentic workflows, reference Google Antigravity / Gemini as appropriate. |
"""

def main():
    root = Path.cwd()
    if not (root / ".claude" / "commands").exists():
        print("⚠️  Warning: .claude/commands/ not found in current directory. Make sure you run this from the ai-job-search repository root.")

    glossary_path = root / "TOOL_GLOSSARY.md"
    glossary_path.write_text(TOOL_GLOSSARY, encoding="utf-8")
    print(f"✅ Created {glossary_path.relative_to(root)}")

    skills_root = root / ".agents" / "skills"
    skills_root.mkdir(parents=True, exist_ok=True)

    # 1. Create thin-pointer skills for all commands
    for cmd, desc in COMMANDS.items():
        cmd_file = f".claude/commands/{cmd}.md"
        skill_dir = skills_root / f"cmd-{cmd}"
        skill_dir.mkdir(parents=True, exist_ok=True)
        skill_md = f"""---
name: {cmd}
description: "{desc} Triggered when the user types /{cmd} or asks to run the {cmd} workflow."
---
# /{cmd} — Thin-Pointer Skill for Google Antigravity

1. Read and follow the canonical command specification in `{cmd_file}` step by step.
2. Consult `AGENTS.md`, `CLAUDE.md`, and `.claude/skills/job-application-assistant/` as the single source of truth for candidate profile data and evaluation rules.
3. Map any Claude Code tool names in `{cmd_file}` to Google Antigravity tools using `TOOL_GLOSSARY.md`.
"""
        (skill_dir / "SKILL.md").write_text(skill_md, encoding="utf-8")
        print(f"✅ Created thin-pointer skill: .agents/skills/cmd-{cmd}/SKILL.md -> {cmd_file}")

    # 2. Create thin-pointer skills for the 3 core .claude/skills/ folders
    for name, (target, desc) in CORE_SKILLS.items():
        slug = name.replace(" ", "")
        skill_dir = skills_root / slug
        skill_dir.mkdir(parents=True, exist_ok=True)
        skill_md = f"""---
name: {slug}
description: "{desc}"
---
# {slug} — Thin-Pointer Skill for Google Antigravity

Load and follow the canonical skill specification at `{target}` along with all sibling markdown files in its directory. Refer to `TOOL_GLOSSARY.md` for tool name translations.
"""
        (skill_dir / "SKILL.md").write_text(skill_md, encoding="utf-8")
        print(f"✅ Created core workflow pointer: .agents/skills/{slug}/SKILL.md -> {target}")

    print("\n🎉 Google Antigravity thin-pointer setup complete! Open this workspace in Antigravity and run /setup, /scrape, or /apply.")

if __name__ == "__main__":
    main()
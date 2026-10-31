---
name: vietnamworks-search
version: 1.0.0
description: >
  Search live job listings on VietnamWorks.com — one of Vietnam's largest
  general job boards (IT, data, AI and every other sector; Ho Chi Minh City,
  Ha Noi, Da Nang). Use when the user wants jobs in Vietnam, e.g. "find AI
  engineer jobs in Ho Chi Minh City", or to look up a specific VietnamWorks
  posting. Trigger phrases: vietnamworks, tìm việc làm, việc làm Việt Nam,
  tuyển dụng, việc làm AI, việc làm IT, việc làm Hồ Chí Minh, việc làm Hà Nội,
  jobs in Vietnam, Vietnam job search, find work in Vietnam.
context: fork
enabled: true  # set to false to keep this portal installed but have /scrape skip it
allowed-tools: Bash(bun run .agents/skills/vietnamworks-search/cli/src/cli.ts *)
---

# VietnamWorks Search Skill

Search public job listings from [VietnamWorks](https://www.vietnamworks.com). No
login, no API key, **zero runtime dependencies** — just `bun`.

## ⚠️ Personal use only

This reads the same anonymous search service the website itself calls
(`ms.vietnamworks.com`). `robots.txt` does not disallow search or job pages, but
VietnamWorks' terms may restrict automated access. **Keep volume low and don't use
it commercially or for bulk collection.** Run it on your own responsibility.

## Commands

### Search

```bash
bun run .agents/skills/vietnamworks-search/cli/src/cli.ts search -q "<keywords>" [flags]
```

- `--query` / `-q` — keywords (required). Matching is **fuzzy**: expect some loosely
  related titles, so pre-filter by title before fetching details.
- `--location` / `-l` — `Ho Chi Minh`, `Ha Noi`, `Da Nang`, `Binh Duong` (server-side city filter). Other values exit 1 (`BAD_LOCATION`).
- `--jobage <days>` — keep postings from the last N days. VietnamWorks has no recency
  parameter, so this is a client-side filter on `date`; results are requested newest-first.
- `--page <n>` (1-indexed), `--limit` / `-n <n>` (per page, max 100, default 20), `--format json|table|plain`.

### Detail

```bash
bun run .agents/skills/vietnamworks-search/cli/src/cli.ts detail <id|url> [--format json|plain]
```

`id` is the numeric `id` from search results; a full `.../<alias>-<id>-jv` URL also works.
Returns the full description, requirements, benefits, posting date and deadline.

## Examples

```bash
# AI / ML roles in Ho Chi Minh City, last 14 days
bun run .agents/skills/vietnamworks-search/cli/src/cli.ts search -q "AI Engineer" -l "Ho Chi Minh" --jobage 14 --limit 20 --format table
# Data engineering in Ha Noi
bun run .agents/skills/vietnamworks-search/cli/src/cli.ts search -q "Data Engineer" -l "Ha Noi" --limit 20
# Vietnamese keywords
bun run .agents/skills/vietnamworks-search/cli/src/cli.ts search -q "kỹ sư dữ liệu" -l "Ho Chi Minh" --format table
# Full text of one posting
bun run .agents/skills/vietnamworks-search/cli/src/cli.ts detail 2109586 --format plain
```

## Output

| Format | Best for |
|--------|----------|
| `json` | Default — `{ meta: { count, page }, results: [{ id, title, company, location, date, url, salary, tags }] }` |
| `table` | Quick scanning |
| `plain` | One line per job, or a single job's full detail |

Errors go to **stderr** as `{ "error": "...", "code": "..." }` with exit code `1`.

## Notes

- `date` is the portal's `approvedOn` date. `salary` is `null` unless the employer made it visible.
- The search API truncates `jobDescription`/`jobRequirement`; `detail` recovers the full text from the page's Next.js flight data and falls back to the truncated API text if that parse finds nothing.
- Parsing anchors and endpoints are in `url-reference.md`.

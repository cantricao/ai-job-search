# ITviec URL Reference

Verified live 2026-10-28.

## Search

**Endpoint:** `https://itviec.com/it-jobs/<keyword-slug>[/<city-slug>]?page=<n>`
**Method:** GET (server-rendered HTML)

| Part | Example | Notes |
|------|---------|-------|
| keyword slug | `ai-engineer` | query with spaces → hyphens (CLI lowercases it) |
| city slug | `ho-chi-minh-hcm`, `ha-noi`, `da-nang` | optional; the CLI also filters again on the card's location text |
| `page` | `?page=2` | 20 cards per page |

### Job card anchors

Each card starts at the attribute `data-search--job-selection-job-slug-value='<slug>'` (that
slug is the job `id`). The parser splits the page on that attribute and reads every field from
that card's own chunk only:

| Field | Anchor inside the card chunk |
|-------|------------------------------|
| title | `<h3 …><a …>TITLE</a></h3>` — **the title is wrapped in an `<a>`**, so tags must be stripped |
| company | `<a … class="…text-rich-grey…" href="/companies/<slug>…">NAME</a>` |
| location | `<div class='… text-nowrap … stretched-link …' title='Ha Noi - Ho Chi Minh'>` |
| work mode | `<div class='text-rich-grey flex-shrink-0'>At office|Hybrid|Remote</div>` (stored as tag `mode:…`) |
| posted date | `<span class='small-text text-dark-grey'>Posted 3 days ago</span>` → converted to `YYYY-MM-DD` |
| skills | `<a href="/it-jobs/<skill>?click_source=Skill+tag">Skill</a>` |
| salary | "Sign in to view salary" link → `"Confidential"` |

## Detail

**Endpoint:** `https://itviec.com/it-jobs/<slug>` (GET, server-rendered HTML)

| Field | Anchor |
|-------|--------|
| title | `<h1>` |
| company | `<div class='employer-name'>` |
| city, skills, salary | JSON in `data-jobs--save-data-layer-value='{…}'` (`job_by_city`, `job_required_skill`, `salary_range`) |
| description / requirements / benefits | `<div class='… paragraph'><h2>Job description</h2>…`, `…Your skills and experience…`, `…Why you'll love working here…` |

Pages contain no JSON-LD.

## API endpoints (authentication required — not used)

- `https://itviec.com/api/v1/jobs` — `{"message":"Bad credentials!"}` without auth
- `https://itviec.com/api/v2/jobs` — empty `{}` without auth

## Access notes

- `robots.txt` allows `/` (disallows only `/subscriptions/new`).
- ITviec sits behind Cloudflare. A request with an honest `Mozilla/5.0 (compatible; …)` UA and with a Chrome UA both returned HTTP 200 from an Australian IP on 2026-10-28. If it starts returning 403/a challenge, report the portal as blocked rather than trying to get around it.
- 2026-10-28 fix: the old parser anchored on the "Sign in to view salary" link, took the first `<h3>` in a 3500-char window (could read a neighbouring card), and kept the `<a>` wrapper in titles. It now splits per card and strips tags.

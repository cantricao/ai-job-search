# VietnamWorks URL Reference

Verified live 2026-10-28.

## Search

**Endpoint:** `POST https://ms.vietnamworks.com/job-search/v1.0/search`
Anonymous (no cookie/token). `Content-Type: application/json`.

Body:

```json
{
  "userId": 0,
  "query": "AI Engineer",
  "filter": [{ "field": "workingLocations.cityId", "value": "29" }],
  "ranges": [],
  "order": [{ "field": "approvedOn", "value": "desc" }],
  "hitsPerPage": 20,
  "page": 0,
  "retrieveFields": ["jobId", "jobTitle", "alias", "jobUrl", "companyName", "workingLocations", "approvedOn", "expiredOn", "prettySalary", "isSalaryVisible", "skills", "jobDescription", "jobRequirement", "benefits"]
}
```

| Item | Notes |
|------|-------|
| `page` | 0-indexed (the CLI's `--page` is 1-indexed) |
| `workingLocations.cityId` | Ho Chi Minh `29`, Ha Noi `24`, Da Nang `17`, Binh Duong `11`, Other `66` (from the search page's `__NEXT_DATA__` → `seoSearch.selectData.location`) |
| `filter` `jobId` | `{ "field": "jobId", "value": "<id>" }` returns one posting (used by `detail`) |
| `order` | `approvedOn desc` = newest first |
| Response | `{ meta: { nbHits, nbPages, page }, data: [...] }` |
| `approvedOn` | ISO with offset in some responses, `MM/DD/YYYY HH:mm:ss` in sorted ones - both handled |
| `jobDescription` / `jobRequirement` | Truncated to ~300 chars with `...` in search results |
| `jobUrl` | Present when `jobUrl` is requested; fallback `https://www.vietnamworks.com/<alias>-<jobId>-jv` |

Query matching is fuzzy (title/skills/description), so results include loosely related jobs.

## Detail page

**URL:** `https://www.vietnamworks.com/<alias>-<jobId>-jv` (server-rendered Next.js app router).
There is no `__NEXT_DATA__` and no JSON-LD. Full description/requirement HTML is shipped in
flight chunks: `self.__next_f.push([1,"24:T766,<p>…</p>"])`. Decode each pushed JSON string,
then match blobs of the form `<hex>:T<hex>,<html>`. The CLI pairs each blob with the API's
truncated `jobDescription` / `jobRequirement` by leading text.

## Access notes

- `robots.txt` disallows only profile, login, apply and print paths — not search or job pages.
- No Cloudflare challenge observed with an honest `Mozilla/5.0 (compatible; vietnamworks-cli/1.0)` UA from an Australian IP.
- If the portal changes the flight-chunk shape, `detail` degrades to the truncated API text rather than failing.

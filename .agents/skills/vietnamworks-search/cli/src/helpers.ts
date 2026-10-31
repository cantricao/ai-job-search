// Data source: VietnamWorks' own public search service (ms.vietnamworks.com), the same
// anonymous JSON endpoint the vietnamworks.com search page calls from the browser.
// Full job descriptions are only on the server-rendered detail page (the search API
// truncates them), so `detail` reads the page's Next.js flight data.

export const SEARCH_API = "https://ms.vietnamworks.com/job-search/v1.0/search"
export const SITE = "https://www.vietnamworks.com"

/** VietnamWorks city ids (from the search page's selectData.location). */
export const CITY_IDS: Record<string, number> = {
  "ha noi": 24,
  "ho chi minh": 29,
  "da nang": 17,
  "binh duong": 11,
}

export function writeError(error: string, code: string): void {
  process.stderr.write(JSON.stringify({ error, code }) + "\n")
}

const UA = "Mozilla/5.0 (compatible; vietnamworks-cli/1.0)"

async function withBackoff(doFetch: () => Promise<Response>): Promise<Response | null> {
  const maxRetries = 6
  let delay = 500
  for (let attempt = 0; attempt <= maxRetries; attempt++) {
    const resp = await doFetch()
    if (resp.status === 429 || resp.status >= 500) {
      if (attempt === maxRetries) throw new Error(`${resp.status}`)
      await new Promise((r) => setTimeout(r, delay + Math.random() * 500))
      delay = Math.min(delay * 2, 8000)
      continue
    }
    if (resp.status === 404) return null
    if (!resp.ok) throw new Error(`${resp.status}`)
    return resp
  }
  throw new Error("Max retries")
}

export async function htmlFetch(url: string): Promise<string> {
  const resp = await withBackoff(() =>
    fetch(url, { headers: { "User-Agent": UA, "Accept-Language": "vi,en;q=0.8" }, redirect: "follow" }),
  )
  return resp ? resp.text() : ""
}

export interface JobCard {
  id: string; title: string; company: string | null
  location: string | null; date: string | null; url: string
  salary: string | null; tags: string[]
}

export interface JobDetail extends JobCard {
  description: string | null; requirements: string | null
  benefits: string | null; applyUrl: string | null
  deadline: string | null
}

const RETRIEVE_FIELDS = [
  "jobId", "jobTitle", "alias", "jobUrl", "companyName", "workingLocations", "approvedOn",
  "expiredOn", "prettySalary", "isSalaryVisible", "skills", "typeWorkingId",
  "jobDescription", "jobRequirement", "benefits",
]

export interface SearchOptions {
  query: string
  page: number // 1-indexed
  limit: number
  cityId?: number
  jobId?: string
}

export async function apiSearch(opts: SearchOptions): Promise<{ hits: any[]; nbHits: number }> {
  const filter: { field: string; value: string }[] = []
  if (opts.cityId) filter.push({ field: "workingLocations.cityId", value: String(opts.cityId) })
  if (opts.jobId) filter.push({ field: "jobId", value: opts.jobId })
  const body = {
    userId: 0,
    query: opts.query,
    filter,
    ranges: [],
    // Newest first, so a bounded --limit is the freshest slice of the portal's matches.
    order: opts.jobId ? [] : [{ field: "approvedOn", value: "desc" }],
    hitsPerPage: Math.max(1, Math.min(opts.limit, 100)),
    page: Math.max(0, opts.page - 1),
    retrieveFields: RETRIEVE_FIELDS,
  }
  const resp = await withBackoff(() =>
    fetch(SEARCH_API, {
      method: "POST",
      headers: { "User-Agent": UA, "Content-Type": "application/json", Accept: "application/json" },
      body: JSON.stringify(body),
    }),
  )
  if (!resp) return { hits: [], nbHits: 0 }
  const json: any = await resp.json()
  return { hits: Array.isArray(json.data) ? json.data : [], nbHits: json.meta?.nbHits ?? 0 }
}

function decodeHtml(text: string): string {
  return text
    .replace(/&amp;/g, "&").replace(/&lt;/g, "<").replace(/&gt;/g, ">")
    .replace(/&quot;/g, '"').replace(/&#39;/g, "'").replace(/&apos;/g, "'")
    .replace(/&#(\d+);/g, (_, d) => String.fromCodePoint(+d))
    .replace(/&#[xX]([0-9a-fA-F]+);/g, (_, h) => String.fromCodePoint(parseInt(h, 16)))
    .replace(/&nbsp;/g, " ").replace(/[ \t]+/g, " ").trim()
}

/** HTML fragment -> readable text, keeping paragraph and bullet structure. */
export function htmlToText(fragment: string): string {
  const withBreaks = fragment
    .replace(/<li[^>]*>/gi, "\n- ")
    .replace(/<\/(p|div|h\d|ul|ol|li)>/gi, "\n")
    .replace(/<br\s*\/?>/gi, "\n")
    .replace(/<[^>]+>/g, "")
  return withBreaks
    .split("\n")
    .map((l) => decodeHtml(l))
    .filter((l, i, a) => l !== "" || (i > 0 && a[i - 1] !== ""))
    .join("\n")
    .trim()
}

/** "2026-10-15T17:33:25+10:00" or "10/27/2026 18:24:13" -> "YYYY-MM-DD" (the date as the portal prints it). */
export function normalizeDate(raw: unknown): string | null {
  if (typeof raw !== "string" || !raw) return null
  const iso = raw.match(/^(\d{4})-(\d{2})-(\d{2})/)
  if (iso) return `${iso[1]}-${iso[2]}-${iso[3]}`
  const us = raw.match(/^(\d{1,2})\/(\d{1,2})\/(\d{4})/)
  if (us) return `${us[3]}-${us[1].padStart(2, "0")}-${us[2].padStart(2, "0")}`
  return null
}

export function jobUrl(hit: any): string {
  if (hit.jobUrl) return hit.jobUrl
  return `${SITE}/${hit.alias}-${hit.jobId}-jv`
}

export function toCard(hit: any): JobCard {
  const locs: any[] = Array.isArray(hit.workingLocations) ? hit.workingLocations : []
  const cities = [...new Set(locs.map((l) => l.cityName).filter(Boolean))]
  const salary = hit.isSalaryVisible && hit.prettySalary ? String(hit.prettySalary) : null
  return {
    id: String(hit.jobId),
    title: decodeHtml(String(hit.jobTitle ?? "")),
    company: hit.companyName ? decodeHtml(String(hit.companyName)) : null,
    location: cities.length ? cities.join(", ") : null,
    date: normalizeDate(hit.approvedOn),
    url: jobUrl(hit),
    salary,
    tags: Array.isArray(hit.skills) ? hit.skills.map((s: any) => s.skillName).filter(Boolean) : [],
  }
}

/**
 * The detail page ships its content inside Next.js flight chunks:
 *   self.__next_f.push([1,"...<row>..."])
 * Rows are either inline JSON (`"jobDescription":"<p>…</p>"`) or, for long text, a
 * reference (`"jobDescription":"$24"`) to a text row `24:T<hexByteLen>,<text>`.
 * Rows are concatenated without separators, so a text row is cut by its byte length.
 */
export interface PageJob {
  description: string | null
  requirements: string | null
  benefits: string | null
}

function flightText(pageHtml: string): string {
  const pushRe = /self\.__next_f\.push\(\[1,("(?:[^"\\]|\\.)*")\]\)/g
  let m: RegExpExecArray | null
  let joined = ""
  while ((m = pushRe.exec(pageHtml)) !== null) {
    try { joined += JSON.parse(m[1]) as string } catch { /* skip a malformed chunk */ }
  }
  return joined
}

function resolveRef(joined: string, ref: string): string | null {
  const rowRe = new RegExp(`(?:^|[^0-9a-zA-Z])${ref.slice(1)}:T([0-9a-f]+),`)
  const m = rowRe.exec(joined)
  if (!m) return null
  const len = parseInt(m[1], 16)
  const rest = joined.slice(m.index + m[0].length)
  return Buffer.from(rest.slice(0, len), "utf8").subarray(0, len).toString("utf8")
}

function fieldValue(joined: string, from: number, key: string): string | null {
  const re = new RegExp(`"${key}":("(?:[^"\\\\]|\\\\.)*")`, "g")
  re.lastIndex = from
  const m = re.exec(joined)
  if (!m) return null
  let value: string
  try { value = JSON.parse(m[1]) as string } catch { return null }
  if (/^\$[0-9a-f]+$/.test(value)) return resolveRef(joined, value)
  return value
}

export function extractPageJob(pageHtml: string, jobId: string): PageJob {
  const joined = flightText(pageHtml)
  const anchor = joined.indexOf(`"jobId":${jobId},"jobTitle"`)
  if (anchor < 0) return { description: null, requirements: null, benefits: null }

  const desc = fieldValue(joined, anchor, "jobDescription")
  const req = fieldValue(joined, anchor, "jobRequirement")

  // benefits is an array of {benefitName, benefitValue, ...} objects
  let benefits: string | null = null
  const bAt = joined.indexOf('"benefits":[{', anchor)
  if (bAt >= 0) {
    const lines: string[] = []
    for (const om of joined.slice(bAt, bAt + 8000).matchAll(/\{"benefitId":\d+[^{}]*\}/g)) {
      try {
        const o = JSON.parse(om[0])
        const v = o.benefitValue ? htmlToText(String(o.benefitValue)) : ""
        if (v) lines.push(o.benefitName ? `${o.benefitName}: ${v}` : v)
      } catch { /* skip */ }
    }
    benefits = lines.join("\n") || null
  }

  return {
    description: desc ? htmlToText(desc) : null,
    requirements: req ? htmlToText(req) : null,
    benefits,
  }
}
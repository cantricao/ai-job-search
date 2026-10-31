// Data source: ITviec.com public job pages (server-rendered HTML).
// Requires Vietnam IP. We parse the HTML directly — jobs are in SSR markup
// around "Sign in to view salary" anchor tags.

export const SEARCH_URL = "https://itviec.com/it-jobs"
export const DETAIL_URL = "https://itviec.com/it-jobs"

export function writeError(error: string, code: string): void {
  process.stderr.write(JSON.stringify({ error, code }) + "\n")
}

const UA = "Mozilla/5.0 (compatible; itviec-cli/1.0)"

export async function htmlFetch(url: string): Promise<string> {
  const maxRetries = 6
  let delay = 500
  for (let attempt = 0; attempt <= maxRetries; attempt++) {
    const resp = await fetch(url, {
      headers: { "User-Agent": UA, "Accept-Language": "en-US,en;q=0.9,vi;q=0.8" },
      redirect: "follow",
    })
    if (resp.status === 429 || resp.status >= 500) {
      if (attempt === maxRetries) throw new Error(`${resp.status}`)
      await new Promise((r) => setTimeout(r, delay + Math.random() * 500))
      delay = Math.min(delay * 2, 8000)
      continue
    }
    if (resp.status === 404) return ""
    if (!resp.ok) throw new Error(`${resp.status}`)
    return resp.text()
  }
  throw new Error("Max retries")
}

export interface JobCard {
  id: string; title: string; company: string | null
  location: string | null; date: string | null; url: string
  salary: string | null; tags: string[]
}

export interface JobDetail extends JobCard {
  description: string | null; requirements: string | null
  benefits: string | null; applyUrl: string | null
}

function decodeHtml(text: string): string {
  return text
    .replace(/&amp;/g, "&").replace(/&lt;/g, "<").replace(/&gt;/g, ">")
    .replace(/&quot;/g, '"').replace(/&#39;/g, "'").replace(/&apos;/g, "'")
    .replace(/&#(\d+);/g, (_, d) => String.fromCodePoint(+d))
    .replace(/&#[xX]([0-9a-fA-F]+);/g, (_, h) => String.fromCodePoint(parseInt(h, 16)))
    .replace(/&nbsp;/g, " ").replace(/\s+/g, " ").trim()
}

/** Strip tags, then decode entities. Titles/company names can wrap their text in <a>/<span>. */
function textOf(fragment: string): string {
  return decodeHtml(fragment.replace(/<[^>]+>/g, " "))
}

/** Like textOf, but keeps list/paragraph structure so requirement bullets stay readable. */
function htmlToText(fragment: string): string {
  const withBreaks = fragment
    .replace(/<svg[\s\S]*?<\/svg>/gi, "")
    .replace(/<li[^>]*>/gi, "\n- ")
    .replace(/<\/(p|div|h\d|ul|ol)>/gi, "\n")
    .replace(/<br\s*\/?>/gi, "\n")
    .replace(/<[^>]+>/g, "")
  return withBreaks
    .split("\n")
    .map((l) => decodeHtml(l))
    .filter((l, i, a) => l !== "" || (i > 0 && a[i - 1] !== ""))
    .join("\n")
    .trim()
}

/** "Posted 3 days ago" / "Posted 5 hours ago" -> YYYY-MM-DD (local date), or null. */
export function parsePostedDate(text: string, now: Date = new Date()): string | null {
  const m = text.match(/Posted\s+(\d+)\s+(minute|hour|day|week|month)s?\s+ago/i)
  if (!m) return /Posted\s+(today|just now)/i.test(text) ? isoDate(now) : null
  const n = +m[1]
  const unit = m[2].toLowerCase()
  const d = new Date(now)
  if (unit === "day") d.setDate(d.getDate() - n)
  else if (unit === "week") d.setDate(d.getDate() - 7 * n)
  else if (unit === "month") d.setMonth(d.getMonth() - n)
  // minutes/hours: same calendar day (approximately) is fine for a 14-day window
  return isoDate(d)
}

function isoDate(d: Date): string {
  const p = (x: number) => String(x).padStart(2, "0")
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}`
}

/**
 * Parse job cards from ITviec search HTML.
 * Jobs are server-rendered. Each card is a `.job-card` block that carries its slug in
 * `data-search--job-selection-job-slug-value`. We split the page on that attribute so
 * fields from a neighbouring card can never bleed into this one.
 */
export function parseJobCards(html: string, now: Date = new Date()): JobCard[] {
  const results: JobCard[] = []
  const seen = new Set<string>()

  const startRe = /data-search--job-selection-job-slug-value='([^']+)'/g
  const starts: { slug: string; index: number }[] = []
  let match: RegExpExecArray | null
  while ((match = startRe.exec(html)) !== null) {
    starts.push({ slug: decodeHtml(match[1]), index: match.index })
  }

  for (let i = 0; i < starts.length; i++) {
    const { slug, index } = starts[i]
    if (seen.has(slug)) continue
    seen.add(slug)
    const chunk = html.slice(index, i + 1 < starts.length ? starts[i + 1].index : html.length)

    const h3 = chunk.match(/<h3[^>]*>([\s\S]*?)<\/h3>/i)
    const title = h3 ? textOf(h3[1]) : ""

    const companyLink = chunk.match(/<a[^>]*class="[^"]*text-rich-grey[^"]*"[^>]*href="\/companies\/[^"]*"[^>]*>([^<]+)<\/a>/i)
      || chunk.match(/href="\/companies\/[^"]*"[^>]*>([^<]+)<\/a>/i)
    const company = companyLink ? decodeHtml(companyLink[1]) : null

    // Location lives in the title attribute of the stretched-link div, e.g. title='Ha Noi - Ho Chi Minh'
    const locMatch = chunk.match(/<div class='[^']*text-nowrap[^']*stretched-link[^']*' title='([^']*)'/i)
    const workMode = chunk.match(/<div class='text-rich-grey flex-shrink-0'>\s*([^<]+?)\s*<\/div>/i)
    const location = locMatch ? decodeHtml(locMatch[1]) : null

    const tags: string[] = []
    const skillRe = /href="\/it-jobs\/([^"?]+)\?click_source=Skill\+tag"[^>]*>([^<]+)<\/a>/gi
    let sm: RegExpExecArray | null
    while ((sm = skillRe.exec(chunk)) !== null) {
      const tag = decodeHtml(sm[2])
      if (!tags.includes(tag)) tags.push(tag)
    }
    if (workMode) tags.unshift(`mode:${decodeHtml(workMode[1])}`)

    const salary = chunk.includes("Sign in to view salary")
      ? "Confidential"
      : (() => {
          const s = chunk.match(/class='[^']*\bsalary\b[^']*'>([\s\S]*?)<\/div>/i)
          return s ? textOf(s[1]) || null : null
        })()

    results.push({
      id: slug,
      title,
      company,
      location,
      date: parsePostedDate(textOf(chunk.slice(0, 1500)), now),
      url: `https://itviec.com/it-jobs/${slug}`,
      salary,
      tags,
    })
  }

  return results
}

export function parseJobDetail(html: string, id: string): JobDetail {
  const h1 = html.match(/<h1[^>]*>([\s\S]*?)<\/h1>/i)
  const titleTag = html.match(/<title>([^<]*)<\/title>/i)
  const title = h1
    ? textOf(h1[1])
    : titleTag ? decodeHtml(titleTag[1].replace(/\s*\|\s*ITviec.*/i, "")) : id

  const emp = html.match(/<div class='employer-name'>([\s\S]*?)<\/div>/i)
  const company = emp ? textOf(emp[1]) || null : null

  // The save-job button carries a JSON data-layer with city, skills and (when public) salary.
  let location: string | null = null
  let tags: string[] = []
  let salary: string | null = html.includes("Sign in to view salary") ? "Confidential" : null
  const layer = html.match(/data-jobs--save-data-layer-value='([^']*)'/i)
  if (layer) {
    try {
      const data = JSON.parse(decodeHtml(layer[1]).replace(/&quot;/g, '"'))
      location = data.job_by_city || null
      tags = String(data.job_required_skill || "").split(",").map((s: string) => s.trim()).filter(Boolean)
      if (data.salary_range) salary = data.salary_range
    } catch { /* leave the fields null rather than guess */ }
  }

  // Each content section is <div class='... paragraph'><h2>Heading</h2>...</div>
  const sections: Record<string, string> = {}
  const secRe = /<div class='[^']*\bparagraph\b[^']*'>\s*<h2[^>]*>([\s\S]*?)<\/h2>([\s\S]*?)(?=<div class='border-bottom-dashed'|<div class='[^']*\bparagraph\b|<\/section|$)/gi
  let sm: RegExpExecArray | null
  while ((sm = secRe.exec(html)) !== null) {
    sections[textOf(sm[1]).toLowerCase()] = htmlToText(sm[2])
  }
  const pick = (re: RegExp) => Object.entries(sections).find(([k]) => re.test(k))?.[1] || null

  return {
    id, title, company, location, date: null,
    url: `https://itviec.com/it-jobs/${id}`,
    salary, tags,
    description: pick(/job description/),
    requirements: pick(/skills and experience|requirement/),
    benefits: pick(/why you|love working|benefit/),
    applyUrl: `https://itviec.com/sign_in?applying=true&job=${id}`,
  }
}
/** Convert query to ITviec URL path slug (spaces -> hyphens, lowercased for stable URLs) */
export function queryToPath(query: string): string {
  return encodeURIComponent(query.trim().toLowerCase()).replace(/%20/g, "-")
}

/** City name -> ITviec location slug. Unknown cities return null (client-side filter still applies). */
export function locationToPath(location: string): string | null {
  const l = location.trim().toLowerCase()
  if (/ho chi minh|hcm|saigon|sai gon|h[oồ] ch[ií] minh/.test(l)) return "ho-chi-minh-hcm"
  if (/ha noi|hanoi|h[aà] n[oộ]i/.test(l)) return "ha-noi"
  if (/da nang|[dđ][aà] n[aẵ]ng/.test(l)) return "da-nang"
  return null
}
import { describe, test, expect } from "bun:test"
import { runCLI, parseJSON } from "./helpers"
import { parseJobCards, parseJobDetail, parsePostedDate, queryToPath, locationToPath } from "../src/helpers"

const CARD = (slug: string, title: string, company: string, posted: string, loc: string) => `
<div class='job-card ipt-2' data-search--job-selection-job-slug-value='${slug}' data-search--pagination-target='jobCard'>
<span class='small-text text-dark-grey'>
${posted}
</span>
<h3 class='imt-3 text-break' data-url='https://itviec.com/it-jobs/${slug}'>
<a target="_blank" class="text-it-black" href="https://itviec.com/it-jobs/${slug}?lab_feature=preview_jd_page">${title}</a>
</h3>
<span class='ims-2'><a target="_blank" class="text-rich-grey" href="/companies/acme?lab_feature=x">${company}</a></span>
<a class="sign-in-view-salary" href="/sign_in?job=${slug}&amp;view_salary_source=search_page">Sign in to view salary</a>
<div class='text-rich-grey flex-shrink-0'>
Hybrid
</div>
<div class='text-rich-grey text-truncate text-nowrap stretched-link position-relative' title='${loc}'>
${loc}
</div>
<a class="itag" href="/it-jobs/python?click_source=Skill+tag">Python</a>
</div>`

describe("itviec-search offline parsing", () => {
  const now = new Date(2026, 9, 28, 12, 0, 0) // 2026-10-28 local

  test("parseJobCards strips the <a> wrapper from titles and keeps cards separate", () => {
    const html = CARD("ai-engineer-acme-1", "AI Engineer", "Acme &amp; Co", "Posted 3 days ago", "Ho Chi Minh") +
      CARD("data-engineer-beta-2", "Data Engineer", "Beta", "Posted 2 hours ago", "Ha Noi")
    const cards = parseJobCards(html, now)
    expect(cards.map((c) => c.title)).toEqual(["AI Engineer", "Data Engineer"])
    expect(cards[0].company).toBe("Acme & Co")
    expect(cards[1].company).toBe("Beta")
    expect(cards[0].location).toBe("Ho Chi Minh")
    expect(cards[0].date).toBe("2026-10-25")
    expect(cards[1].date).toBe("2026-10-28")
    expect(cards[0].tags).toContain("Python")
    expect(cards[0].title).not.toContain("<")
  })

  test("parsePostedDate", () => {
    expect(parsePostedDate("Posted 1 day ago", now)).toBe("2026-10-27")
    expect(parsePostedDate("Posted 2 weeks ago", now)).toBe("2026-10-14")
    expect(parsePostedDate("no date here", now)).toBeNull()
  })

  test("parseJobDetail reads title, company, city and sections", () => {
    const html = `<h1 class='x'>AI Engineer</h1><div class='employer-name'>Acme</div>
<div data-jobs--save-data-layer-value='{&quot;job_by_city&quot;:&quot;Ho Chi Minh&quot;,&quot;job_required_skill&quot;:&quot;Python, LLM&quot;,&quot;salary_range&quot;:&quot;&quot;}'></div>
<div class='imy-5 paragraph'><h2>Job description</h2><ul><li>Build RAG</li></ul></div>
<div class='border-bottom-dashed'></div>
<div class='imy-5 paragraph'><h2>Your skills and experience</h2><p>2 years Python</p></div>
<div class='border-bottom-dashed'></div>`
    const d = parseJobDetail(html, "ai-engineer-acme-1")
    expect(d.title).toBe("AI Engineer")
    expect(d.company).toBe("Acme")
    expect(d.location).toBe("Ho Chi Minh")
    expect(d.tags).toEqual(["Python", "LLM"])
    expect(d.description).toBe("- Build RAG")
    expect(d.requirements).toBe("2 years Python")
  })

  test("queryToPath and locationToPath", () => {
    expect(queryToPath("AI Engineer")).toBe("ai-engineer")
    expect(locationToPath("Ho Chi Minh")).toBe("ho-chi-minh-hcm")
    expect(locationToPath("Ha Noi")).toBe("ha-noi")
    expect(locationToPath("Brisbane")).toBeNull()
  })
})

describe("itviec-search CLI", () => {
  test("search with --help shows usage", () => {
    const { stderr, exitCode } = runCLI(["--help"])
    expect(exitCode).toBe(0)
    expect(stderr).toContain("Usage:")
  })

  test("search without --query exits 1", () => {
    const { stderr, exitCode } = runCLI(["search"])
    expect(exitCode).toBe(1)
    expect(stderr).toContain("error")
  })

  test("search with bogus flag still runs (ignores unknown flags)", () => {
    const { exitCode } = runCLI(["search", "-q", "test", "--bogus"])
    // Unknown flags are silently ignored; the search still runs
    expect(exitCode).toBe(0)
  })

  test("detail without id exits 1", () => {
    const { stderr, exitCode } = runCLI(["detail"])
    expect(exitCode).toBe(1)
    expect(stderr).toContain("error")
  })

  // Live test — titles must be clean text, not HTML fragments
  test("search returns real, clean results", () => {
    const { stdout, exitCode } = runCLI([
      "search", "-q", "AI Engineer", "--limit", "3", "--format", "json",
    ])
    expect(exitCode).toBe(0)
    const data = parseJSON(stdout)
    expect(data.results.length).toBeGreaterThan(0)
    for (const r of data.results) {
      expect(r.id).toBeTruthy()
      expect(r.title).toBeTruthy()
      expect(r.title).not.toContain("<")
      expect(r.url).toContain("itviec.com")
    }
  })
})

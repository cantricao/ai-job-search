import { describe, test, expect } from "bun:test"
import { runCLI, parseJSON } from "./helpers"
import { extractPageJob, normalizeDate, toCard } from "../src/helpers"

describe("vietnamworks-search offline parsing", () => {
  test("normalizeDate handles ISO and US-style dates", () => {
    expect(normalizeDate("2026-10-15T17:33:25+10:00")).toBe("2026-10-15")
    expect(normalizeDate("10/27/2026 18:24:13")).toBe("2026-10-27")
    expect(normalizeDate("")).toBeNull()
    expect(normalizeDate(undefined)).toBeNull()
  })

  test("toCard never omits fields and decodes entities", () => {
    const card = toCard({
      jobId: 1,
      jobTitle: "Data &amp; AI Engineer",
      alias: "data-ai-engineer",
      companyName: null,
      workingLocations: [{ cityName: "Ho Chi Minh" }, { cityName: "Ho Chi Minh" }],
      approvedOn: "2026-10-26T10:00:00+07:00",
      isSalaryVisible: false,
    })
    expect(card.title).toBe("Data & AI Engineer")
    expect(card.company).toBeNull()
    expect(card.location).toBe("Ho Chi Minh")
    expect(card.url).toBe("https://www.vietnamworks.com/data-ai-engineer-1-jv")
    expect(card.salary).toBeNull()
  })

  test("extractPageJob resolves inline values and $-references to text rows", () => {
    const rows =
      `1:{"jobId":42,"jobTitle":"T","jobDescription":"$2a","jobRequirement":"<ul><li>Python</li></ul>","jobLevelId":5}\n` +
      `2a:T10,<p>Xin chào</p>`
    const html = `<script>self.__next_f.push([1,${JSON.stringify(rows)}])</script>`
    const job = extractPageJob(html, "42")
    // "<p>Xin chào</p>" is 16 bytes in UTF-8 (the "à" is 2), 0x10 = 16
    expect(job.description).toBe("Xin chào")
    expect(job.requirements).toBe("- Python")
  })

  test("extractPageJob returns nulls when the job is not in the page", () => {
    expect(extractPageJob("<html></html>", "42")).toEqual({ description: null, requirements: null, benefits: null })
  })
})

describe("vietnamworks-search CLI", () => {
  test("--help shows usage", () => {
    const { stderr, exitCode } = runCLI(["--help"])
    expect(exitCode).toBe(0)
    expect(stderr).toContain("Usage:")
  })

  test("search without --query exits 1 with a JSON error on stderr", () => {
    const { stderr, exitCode } = runCLI(["search"])
    expect(exitCode).toBe(1)
    expect(stderr).toContain('"code":"MISSING_QUERY"')
  })

  test("unknown --location exits 1", () => {
    const { stderr, exitCode } = runCLI(["search", "-q", "python", "-l", "Atlantis"])
    expect(exitCode).toBe(1)
    expect(stderr).toContain("BAD_LOCATION")
  })

  test("detail without id exits 1", () => {
    const { stderr, exitCode } = runCLI(["detail"])
    expect(exitCode).toBe(1)
    expect(stderr).toContain("error")
  })

  // Live test
  test("search returns real results", () => {
    const { stdout, exitCode } = runCLI(["search", "-q", "AI Engineer", "-l", "Ho Chi Minh", "--limit", "3", "--format", "json"])
    expect(exitCode).toBe(0)
    const data = parseJSON(stdout)
    expect(data.results.length).toBeGreaterThan(0)
    for (const r of data.results) {
      expect(r.id).toBeTruthy()
      expect(r.title).toBeTruthy()
      expect(r.url).toContain("vietnamworks.com")
    }
  })
})

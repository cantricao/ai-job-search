import { CITY_IDS, apiSearch, toCard, writeError, type JobCard } from "../helpers.js"

interface SearchArgs {
  query: string
  location?: string
  jobage?: number
  page: number
  limit: number
  format: "json" | "table" | "plain"
}

function formatTable(results: JobCard[]): string {
  if (results.length === 0) return "(no results)"
  const titleW = Math.max(8, ...results.map((r) => Math.min(r.title.length, 50)))
  const companyW = Math.max(8, ...results.map((r) => Math.min((r.company || "").length, 30)))
  const lines = [
    `ID       DATE        ${"TITLE".padEnd(titleW)}  ${"COMPANY".padEnd(companyW)}  LOCATION`,
    `-------  ----------  ${"-".repeat(titleW)}  ${"-".repeat(companyW)}  ----------`,
  ]
  for (const r of results) {
    lines.push(
      `${r.id.padEnd(7)}  ${(r.date || "?").padEnd(10)}  ${r.title.slice(0, titleW).padEnd(titleW)}  ${(r.company || "?").slice(0, companyW).padEnd(companyW)}  ${r.location || "?"}`,
    )
  }
  return lines.join("\n")
}

export async function runSearch(args: SearchArgs): Promise<void> {
  let cityId: number | undefined
  if (args.location) {
    const key = args.location.trim().toLowerCase()
    cityId = Object.entries(CITY_IDS).find(([name]) => key.includes(name))?.[1]
    if (cityId === undefined) {
      writeError(
        `Unknown --location "${args.location}". Supported: ${Object.keys(CITY_IDS).join(", ")}`,
        "BAD_LOCATION",
      )
      process.exit(1)
    }
  }

  let hits: any[]
  try {
    hits = (await apiSearch({ query: args.query, page: args.page, limit: args.limit > 0 ? args.limit : 20, cityId })).hits
  } catch (e: any) {
    writeError(e.message || "Fetch failed", "FETCH_ERROR")
    process.exit(1)
  }

  let results = hits.map(toCard)

  if (args.jobage && args.jobage > 0) {
    const cutoff = new Date()
    cutoff.setDate(cutoff.getDate() - args.jobage)
    const cut = cutoff.toISOString().slice(0, 10)
    // Results with no parseable date are kept (never dropped on a guess).
    results = results.filter((r) => !r.date || r.date >= cut)
  }

  switch (args.format) {
    case "json":
      process.stdout.write(JSON.stringify({ meta: { count: results.length, page: args.page }, results }) + "\n")
      break
    case "table":
      process.stdout.write(formatTable(results) + "\n")
      break
    case "plain":
      for (const r of results) process.stdout.write(`${r.id} | ${r.title} | ${r.company || "?"} | ${r.location || "?"} | ${r.date || "?"}\n`)
      break
  }
}

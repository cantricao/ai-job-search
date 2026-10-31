#!/usr/bin/env bun

import { writeError } from "./helpers.js"
import { runSearch } from "./commands/search.js"
import { runDetail } from "./commands/detail.js"

function usage(): void {
  process.stderr.write(`VietnamWorks Job Search CLI

Usage:
  bun run cli.ts search --query <text> [flags]
  bun run cli.ts detail <id|url> [flags]

Search flags:
  --query, -q <text>      Search query (required)
  --location, -l <text>   City: "Ho Chi Minh", "Ha Noi", "Da Nang", "Binh Duong"
  --jobage <days>         Only postings from the last N days (client-side, on the posting date)
  --page <n>              Page number, 1-indexed (default: 1)
  --limit, -n <n>         Results per page, max 100 (default: 20)
  --format <fmt>          json|table|plain (default: json)

Detail flags:
  --format <fmt>          json|plain (default: json)
`)
}

function flagVal(args: string[], flags: string[]): string | undefined {
  for (const f of flags) {
    const idx = args.indexOf(f)
    if (idx !== -1 && idx + 1 < args.length) return args[idx + 1]
  }
  return undefined
}

function hasFlag(args: string[], flags: string[]): boolean {
  return flags.some((f) => args.includes(f))
}

const args = process.argv.slice(2)

if (args.length === 0 || hasFlag(args, ["--help", "-h"])) {
  usage()
  process.exit(0)
}

const command = args[0]
const rest = args.slice(1)

switch (command) {
  case "search": {
    const query = flagVal(rest, ["--query", "-q"])
    if (!query) {
      writeError("--query is required", "MISSING_QUERY")
      usage()
      process.exit(1)
    }
    const location = flagVal(rest, ["--location", "-l"])
    const jobageRaw = flagVal(rest, ["--jobage"])
    const jobage = jobageRaw ? parseInt(jobageRaw, 10) : undefined
    const page = parseInt(flagVal(rest, ["--page"]) || "1", 10)
    const limit = parseInt(flagVal(rest, ["--limit", "-n"]) || "20", 10)
    const format = (flagVal(rest, ["--format"]) || "json") as "json" | "table" | "plain"

    await runSearch({ query, location, jobage, page, limit, format })
    break
  }
  case "detail": {
    const idOrUrl = rest.find((a) => !a.startsWith("-"))
    if (!idOrUrl) {
      writeError("Job ID or URL is required", "MISSING_ID")
      usage()
      process.exit(1)
    }
    const format = (flagVal(rest, ["--format"]) || "json") as "json" | "plain"

    await runDetail({ id: idOrUrl, format })
    break
  }
  default:
    writeError(`Unknown command: ${command}`, "UNKNOWN_COMMAND")
    usage()
    process.exit(1)
}

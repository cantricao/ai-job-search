import {
  apiSearch,
  extractPageJob,
  htmlFetch,
  htmlToText,
  jobUrl,
  normalizeDate,
  toCard,
  writeError,
  type JobDetail,
} from "../helpers.js"

interface DetailArgs {
  id: string
  format: "json" | "plain"
}

export async function runDetail(args: DetailArgs): Promise<void> {
  // Accept a numeric job id or a full vietnamworks.com/...-<id>-jv URL.
  const m = args.id.match(/-(\d+)-jv(?:[/?#]|$)/) || args.id.match(/^(\d+)$/)
  if (!m) {
    writeError("Expected a numeric job id or a vietnamworks.com .../<alias>-<id>-jv URL", "BAD_ID")
    process.exit(1)
  }
  const id = m[1]

  let hit: any
  try {
    hit = (await apiSearch({ query: "", page: 1, limit: 1, jobId: id })).hits[0]
  } catch (e: any) {
    writeError(e.message || "Fetch failed", "FETCH_ERROR")
    process.exit(1)
  }
  if (!hit) {
    writeError("Job not found (it may have expired)", "NOT_FOUND")
    process.exit(1)
  }

  // The API truncates descriptions ("..."); the detail page carries the full text.
  const url = jobUrl(hit)
  let description: string | null = hit.jobDescription ? htmlToText(hit.jobDescription) : null
  let requirements: string | null = hit.jobRequirement ? htmlToText(hit.jobRequirement) : null
  let pageBenefits: string | null = null
  try {
    const page = await htmlFetch(url)
    const full = extractPageJob(page, id)
    description = full.description ?? description
    requirements = full.requirements ?? requirements
    pageBenefits = full.benefits
  } catch { /* keep the truncated API text rather than fail the whole lookup */ }

  const detail: JobDetail = {
    ...toCard(hit),
    description,
    requirements,
    benefits: pageBenefits,
    applyUrl: url,
    deadline: normalizeDate(hit.expiredOn),
  }

  switch (args.format) {
    case "json":
      process.stdout.write(JSON.stringify(detail) + "\n")
      break
    case "plain":
      process.stdout.write(`${detail.title}\n`)
      process.stdout.write(`${detail.company || "?"} — ${detail.location || "?"}\n`)
      process.stdout.write(`Posted: ${detail.date || "?"}  Deadline: ${detail.deadline || "?"}\n`)
      process.stdout.write(`${"-".repeat(60)}\n\n`)
      if (detail.description) process.stdout.write("MÔ TẢ CÔNG VIỆC:\n" + detail.description + "\n\n")
      if (detail.requirements) process.stdout.write("YÊU CẦU:\n" + detail.requirements + "\n\n")
      if (detail.benefits) process.stdout.write("PHÚC LỢI:\n" + detail.benefits + "\n\n")
      process.stdout.write(`Apply: ${detail.applyUrl}\n`)
      break
  }
}

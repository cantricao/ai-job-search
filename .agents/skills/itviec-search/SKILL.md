---
name: itviec-search
version: 1.0.0
description: >
  Tìm kiếm việc làm IT tại Việt Nam trên ITviec.com — trang tuyển dụng IT
  hàng đầu Việt Nam. Dùng khi người dùng muốn tìm việc IT, lập trình,
  AI/ML, DevOps tại Việt Nam. Trigger phrases: tìm việc IT, itviec,
  việc làm IT Việt Nam, IT jobs Vietnam, tuyển dụng IT, tìm job IT,
  "có job nào ở", việc làm AI, việc làm lập trình.
context: fork
enabled: true  # set to false to keep this portal installed but have /scrape skip it
allowed-tools: Bash(bun run .agents/skills/itviec-search/cli/src/cli.ts *)
---

# ITviec Search Skill

Tìm kiếm việc làm IT trực tiếp từ [ITviec.com](https://itviec.com) — trang tuyển dụng
IT chuyên biệt lớn nhất Việt Nam với 28,000+ reviews công ty và báo cáo lương IT.

> ℹ️ **Truy cập.** obots.txt của ITviec cho phép crawl trang job công khai. Lần kiểm tra gần nhất (2026-10-28) từ IP Úc trả về HTTP 200, nhưng ITviec dùng Cloudflare nên có thể thay đổi - nếu bị chặn (403/challenge), skill báo lỗi chứ không tìm cách vượt qua.

## ⚠️ Personal use only

Dữ liệu từ trang public của ITviec. Tự động truy cập có thể vi phạm điều khoản
sử dụng. **Giữ volume thấp, không dùng cho mục đích thương mại hoặc thu thập
dữ liệu hàng loạt.** Chạy với trách nhiệm của bạn.

## When to use this skill

- Tìm việc IT tại Việt Nam (HCMC, Hanoi, Da Nang...)
- Lọc theo level (Fresher, Junior, Middle, Senior)
- Lọc theo working model (Remote, Hybrid, On-site)
- Lọc theo mức lương
- Xem chi tiết một job posting cụ thể

## Commands

### Search job listings

```bash
bun run .agents/skills/itviec-search/cli/src/cli.ts search --query "AI Engineer" [flags]
```

Key flags:
- `--query <text>` / `-q <text>` — từ khóa tìm kiếm (title, skill). **Required.**
- `--location <text>` / `-l <text>` — thành phố: "Ho Chi Minh", "Ha Noi", "Da Nang" (map sang URL slug + lọc lại theo cột location)
- Không có `--jobage`: mỗi kết quả có `date` (tính từ "Posted N days ago" trên trang) - lọc 14 ngày phía client
- `--page <n>` — số trang (1-indexed, ~20 results per page)
- `--limit <n>` / `-n <n>` — giới hạn tổng kết quả (client-side)
- `--format json|table|plain` — default `json`

### Fetch full job detail

```bash
bun run .agents/skills/itviec-search/cli/src/cli.ts detail <id|url> [--format json|plain]
```

## Usage examples

```bash
# AI Engineer jobs, Ho Chi Minh
bun run .agents/skills/itviec-search/cli/src/cli.ts search -q "AI Engineer" -l "Ho Chi Minh" --format table

# Python jobs nationwide
bun run .agents/skills/itviec-search/cli/src/cli.ts search -q "Python" --format table

# Full details for a specific job
bun run .agents/skills/itviec-search/cli/src/cli.ts detail 12345 --format plain
```

## Output formats

| Format | Best for |
|--------|----------|
| `json` | Default — programmatic use, passing IDs to `detail` |
| `table` | Quick human-readable scanning |
| `plain` | Reading a single job's full detail (`detail` command) |

All errors are written to **stderr** as `{ "error": "...", "code": "..." }` and the process exits with code `1`.

## Notes

- Trang search/detail được render server-side trong HTML gốc; URL dạng `/it-jobs/ai-engineer/ho-chi-minh-hcm` (keyword + slug thành phố)
- `id` là slug của job (vd `agentic-ai-engineer-llm-python-nexlab-0423`), truyền nguyên cho `detail`
- Mỗi trang ~20 kết quả
- API v1 (`api/v1/jobs`) cần authentication, skill này scrape HTML
- Job ID được extract từ URL chi tiết: `https://itviec.com/jobs/<id>`
- Lương hiển thị "Confidential" (cần đăng nhập để xem)

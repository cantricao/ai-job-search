# vietnamworks-cli

Zero-runtime-dependency Bun CLI for VietnamWorks job search. See `../SKILL.md` for usage
and `../url-reference.md` for the endpoints and parsing anchors.

```bash
bun install        # dev types only
bun run typecheck
bun run test       # offline parser tests + a small live smoke test
bun run src/cli.ts search -q "AI Engineer" -l "Ho Chi Minh" --limit 5 --format table
```

No parsing library is used: search is a JSON API, and `detail` decodes Next.js flight chunks with plain string/regex handling.

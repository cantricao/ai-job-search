#!/usr/bin/env python3
"""Local read-only Gmail MCP Server using standard Gmail REST API v1 (Desktop OAuth).

Works with any regular Google account via a standard Google Cloud Console OAuth 2.0
Client ID (no Google Workspace Developer Preview Program required).

Exposes the exact read-only MCP tools required by `/gmail-sync`:
  - `list_labels`
  - `search_threads`
  - `get_thread`
  - `get_message`

CLI usage:
  python tools/gmail_mcp_server.py           # Run as an MCP stdio server
  python tools/gmail_mcp_server.py --auth    # Authenticate in browser & save gmail_sync/token.json
  python tools/gmail_mcp_server.py --check   # Verify credentials, token, and Gmail API access

Stdlib only (Python 3.10+).
"""

from __future__ import annotations

import argparse
import base64
from concurrent.futures import ThreadPoolExecutor
import html
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import os
from pathlib import Path
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import webbrowser

ROOT = Path(__file__).resolve().parent.parent
STATE_DIR = ROOT / "gmail_sync"
DEFAULT_CREDENTIALS_PATH = STATE_DIR / "credentials.json"
DEFAULT_TOKEN_PATH = STATE_DIR / "token.json"
GLOBAL_MCP_CONFIG_PATH = Path.home() / ".gemini" / "config" / "mcp_config.json"

GMAIL_API_BASE = "https://gmail.googleapis.com/gmail/v1/users/me"
OAUTH_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
OAUTH_TOKEN_URL = "https://oauth2.googleapis.com/token"
GMAIL_READONLY_SCOPE = "https://www.googleapis.com/auth/gmail.readonly"


def _err(msg: str) -> None:
    sys.stderr.write(f"[gmail-mcp] {msg}\n")
    sys.stderr.flush()


def get_credentials_path() -> Path:
    env_path = os.environ.get("GMAIL_CREDENTIALS_PATH")
    return Path(env_path) if env_path else DEFAULT_CREDENTIALS_PATH


def get_token_path() -> Path:
    env_path = os.environ.get("GMAIL_TOKEN_PATH")
    return Path(env_path) if env_path else DEFAULT_TOKEN_PATH


def load_client_credentials() -> tuple[str, str]:
    """Resolve Google OAuth client_id and client_secret from env, credentials.json, or mcp_config.json."""
    client_id = os.environ.get("GMAIL_CLIENT_ID", "").strip()
    client_secret = os.environ.get("GMAIL_CLIENT_SECRET", "").strip()
    if client_id and client_secret:
        return client_id, client_secret

    cred_path = get_credentials_path()
    if cred_path.is_file():
        try:
            raw = json.loads(cred_path.read_text(encoding="utf-8"))
            block = raw.get("installed") or raw.get("web") or raw
            cid = str(block.get("client_id") or block.get("clientId") or "").strip()
            csec = str(block.get("client_secret") or block.get("clientSecret") or "").strip()
            if cid and csec:
                return cid, csec
        except (OSError, json.JSONDecodeError) as exc:
            raise RuntimeError(f"Failed to parse {cred_path}: {exc}") from exc

    if GLOBAL_MCP_CONFIG_PATH.is_file():
        try:
            cfg = json.loads(GLOBAL_MCP_CONFIG_PATH.read_text(encoding="utf-8"))
            gmail_cfg = (cfg.get("mcpServers") or {}).get("gmail") or {}
            oauth = gmail_cfg.get("oauth") or {}
            env = gmail_cfg.get("env") or {}
            cid = str(oauth.get("clientId") or env.get("GMAIL_CLIENT_ID") or "").strip()
            csec = str(oauth.get("clientSecret") or env.get("GMAIL_CLIENT_SECRET") or "").strip()
            if cid and csec:
                return cid, csec
        except (OSError, json.JSONDecodeError):
            pass

    raise RuntimeError(
        "Missing Google OAuth client credentials. Either:\n"
        f"  1. Save your Google Cloud Desktop OAuth JSON to {DEFAULT_CREDENTIALS_PATH}, or\n"
        "  2. Set GMAIL_CLIENT_ID and GMAIL_CLIENT_SECRET in your MCP server 'env' in ~/.gemini/config/mcp_config.json."
    )


def _post_form(url: str, data: dict[str, str]) -> dict:
    encoded = urllib.parse.urlencode(data).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=encoded,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"OAuth token endpoint returned HTTP {exc.code}: {body}") from exc


def run_oauth_flow(port: int = 0) -> dict:
    """Run interactive loopback OAuth2 flow in the user's browser and persist token.json."""
    client_id, client_secret = load_client_credentials()
    STATE_DIR.mkdir(parents=True, exist_ok=True)

    result: dict[str, str | None] = {"code": None, "error": None}

    class CallbackHandler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802
            parsed = urllib.parse.urlparse(self.path)
            params = urllib.parse.parse_qs(parsed.query)
            if "error" in params:
                result["error"] = params["error"][0]
                self._respond(400, "Authentication failed. Check the terminal for details.")
            elif "code" in params:
                result["code"] = params["code"][0]
                self._respond(
                    200,
                    "Gmail MCP authentication complete! You can close this tab and return to Antigravity.",
                )
            else:
                self._respond(400, "Missing authorization code.")

        def _respond(self, status: int, message: str) -> None:
            body = (
                "<!doctype html><html><head><meta charset='utf-8'><title>Gmail MCP</title></head>"
                "<body style='font-family:system-ui,sans-serif;padding:2rem;max-width:36rem;margin:auto;'>"
                f"<h2>{html.escape(message)}</h2></body></html>"
            ).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, format: str, *args: object) -> None:  # noqa: A002
            return

    server = HTTPServer(("127.0.0.1", port), CallbackHandler)
    actual_port = server.server_port
    redirect_uri = f"http://localhost:{actual_port}"

    auth_params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": GMAIL_READONLY_SCOPE,
        "access_type": "offline",
        "prompt": "consent",
    }
    auth_url = f"{OAUTH_AUTH_URL}?{urllib.parse.urlencode(auth_params)}"

    _err("Opening browser for Google OAuth (gmail.readonly)...")
    _err(f"If the browser does not open automatically, visit:\n  {auth_url}")
    webbrowser.open(auth_url)

    server.timeout = 180
    while result["code"] is None and result["error"] is None:
        server.handle_request()
        if result["code"] is None and result["error"] is None:
            break
    server.server_close()

    if result["error"]:
        raise RuntimeError(f"Google OAuth authorization declined or failed: {result['error']}")
    if not result["code"]:
        raise RuntimeError("Timed out waiting for Google OAuth callback in browser.")

    token_resp = _post_form(
        OAUTH_TOKEN_URL,
        {
            "code": result["code"],
            "client_id": client_id,
            "client_secret": client_secret,
            "redirect_uri": redirect_uri,
            "grant_type": "authorization_code",
        },
    )

    now = int(time.time())
    token_data = {
        "access_token": token_resp["access_token"],
        "refresh_token": token_resp.get("refresh_token"),
        "token_type": token_resp.get("token_type", "Bearer"),
        "scope": token_resp.get("scope", GMAIL_READONLY_SCOPE),
        "expiry": now + int(token_resp.get("expires_in", 3600)),
    }
    token_path = get_token_path()
    token_path.parent.mkdir(parents=True, exist_ok=True)
    token_path.write_text(json.dumps(token_data, indent=2), encoding="utf-8")
    _err(f"Saved OAuth token to {token_path}")
    return token_data


def get_access_token(allow_interactive: bool = True) -> str:
    """Return a valid OAuth2 access token, refreshing or authenticating as needed."""
    token_path = get_token_path()
    if token_path.is_file():
        try:
            token_data = json.loads(token_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            token_data = {}

        access_token = token_data.get("access_token")
        expiry = int(token_data.get("expiry") or 0)
        if access_token and time.time() < expiry - 60:
            return str(access_token)

        refresh_token = token_data.get("refresh_token")
        if refresh_token:
            client_id, client_secret = load_client_credentials()
            refreshed = _post_form(
                OAUTH_TOKEN_URL,
                {
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "refresh_token": str(refresh_token),
                    "grant_type": "refresh_token",
                },
            )
            token_data["access_token"] = refreshed["access_token"]
            token_data["expiry"] = int(time.time()) + int(refreshed.get("expires_in", 3600))
            if refreshed.get("refresh_token"):
                token_data["refresh_token"] = refreshed["refresh_token"]
            token_path.write_text(json.dumps(token_data, indent=2), encoding="utf-8")
            return str(token_data["access_token"])

    if not allow_interactive:
        raise RuntimeError(
            f"No OAuth token found at {token_path}. Run `python tools/gmail_mcp_server.py --auth` first."
        )

    token_data = run_oauth_flow()
    return str(token_data["access_token"])


def gmail_get(path: str, params: dict[str, object] | None = None, allow_interactive: bool = True) -> dict:
    """Perform an authenticated GET request against the standard Gmail REST API v1."""
    token = get_access_token(allow_interactive=allow_interactive)
    url = f"{GMAIL_API_BASE}/{path.lstrip('/')}"
    if params:
        pairs: list[tuple[str, str]] = []
        for k, v in params.items():
            if v is None:
                continue
            if isinstance(v, (list, tuple)):
                for item in v:
                    pairs.append((k, str(item)))
            else:
                pairs.append((k, str(v)))
        if pairs:
            url = f"{url}?{urllib.parse.urlencode(pairs)}"

    req = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
        },
        method="GET",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        if exc.code == 403 and "accessNotConfigured" in body:
            raise RuntimeError(
                "Gmail API is not enabled yet in your Google Cloud project. "
                "Enable it at: https://console.cloud.google.com/apis/library/gmail.googleapis.com "
                f"(raw response: {body})"
            ) from exc
        raise RuntimeError(f"Gmail API HTTP {exc.code} on {path}: {body}") from exc


def _decode_base64url(data: str) -> str:
    padded = data + "=" * (-len(data) % 4)
    raw = base64.urlsafe_b64decode(padded.encode("ascii"))
    return raw.decode("utf-8", errors="replace")


def _strip_html(html_text: str) -> str:
    cleaned = re.sub(r"(?is)<(script|style).*?>.*?</\1>", " ", html_text)
    cleaned = re.sub(r"(?i)<br\s*/?>", "\n", cleaned)
    cleaned = re.sub(r"(?i)</(p|div|tr|li|h[1-6])>", "\n", cleaned)
    cleaned = re.sub(r"(?s)<[^>]+>", " ", cleaned)
    cleaned = html.unescape(cleaned)
    lines = [re.sub(r"[ \t]+", " ", line).strip() for line in cleaned.splitlines()]
    return "\n".join(line for line in lines if line)


def _extract_body(payload: dict | None) -> str:
    """Recursively extract plain-text body (or HTML fallback) from a Gmail message payload."""
    if not payload:
        return ""

    plain_parts: list[str] = []
    html_parts: list[str] = []

    def walk(part: dict) -> None:
        mime = (part.get("mimeType") or "").lower()
        body_data = (part.get("body") or {}).get("data")
        if body_data:
            decoded = _decode_base64url(body_data)
            if mime == "text/plain":
                plain_parts.append(decoded)
            elif mime == "text/html":
                html_parts.append(decoded)
            elif not part.get("parts") and not plain_parts:
                plain_parts.append(decoded)
        for child in part.get("parts") or []:
            if isinstance(child, dict):
                walk(child)

    walk(payload)
    if plain_parts:
        return "\n\n".join(p.strip() for p in plain_parts if p.strip())
    if html_parts:
        return "\n\n".join(_strip_html(h) for h in html_parts if h.strip())
    return ""


def _headers_map(payload: dict | None) -> dict[str, str]:
    headers: dict[str, str] = {}
    for item in (payload or {}).get("headers") or []:
        name = str(item.get("name") or "").strip()
        val = str(item.get("value") or "").strip()
        if name:
            headers[name.lower()] = val
    return headers


def _format_message(msg: dict, include_body: bool = True) -> dict:
    payload = msg.get("payload") or {}
    hdrs = _headers_map(payload)
    out = {
        "id": msg.get("id"),
        "threadId": msg.get("threadId"),
        "labelIds": msg.get("labelIds") or [],
        "internalDate": msg.get("internalDate"),
        "date": hdrs.get("date", ""),
        "from": hdrs.get("from", ""),
        "to": hdrs.get("to", ""),
        "subject": hdrs.get("subject", ""),
        "snippet": html.unescape(str(msg.get("snippet") or "")),
    }
    if include_body:
        out["body"] = _extract_body(payload)
    return out


# ---------------------------------------------------------------------------
# MCP Tool Implementations
# ---------------------------------------------------------------------------


def tool_list_labels(_args: dict) -> dict:
    data = gmail_get("labels")
    labels = [
        {
            "id": lbl.get("id"),
            "name": lbl.get("name"),
            "type": lbl.get("type"),
        }
        for lbl in (data.get("labels") or [])
    ]
    return {"labels": labels}


def tool_search_threads(args: dict) -> dict:
    query = str(args.get("q") or args.get("query") or "").strip()
    page_size = int(args.get("pageSize") or args.get("maxResults") or 50)
    page_size = max(1, min(page_size, 100))
    page_token = args.get("pageToken")
    view = str(args.get("view") or "THREAD_VIEW_MINIMAL").upper()

    params: dict[str, object] = {"maxResults": page_size}
    if query:
        params["q"] = query
    if page_token:
        params["pageToken"] = str(page_token)

    listing = gmail_get("threads", params=params)
    raw_threads = listing.get("threads") or []

    include_full = "FULL" in view and "MINIMAL" not in view

    def fetch_thread_summary(stub: dict) -> dict:
        tid = stub.get("id")
        if not tid:
            return stub
        fmt = "full" if include_full else "metadata"
        t_data = gmail_get(
            f"threads/{tid}",
            params={
                "format": fmt,
                "metadataHeaders": ["Subject", "From", "To", "Date"],
            },
        )
        msgs = [
            _format_message(m, include_body=include_full)
            for m in (t_data.get("messages") or [])
        ]
        return {
            "id": t_data.get("id", tid),
            "historyId": t_data.get("historyId", stub.get("historyId")),
            "snippet": html.unescape(str(stub.get("snippet") or "")),
            "messages": msgs,
        }

    with ThreadPoolExecutor(max_workers=8) as pool:
        threads = list(pool.map(fetch_thread_summary, raw_threads))

    result: dict[str, object] = {
        "threads": threads,
        "resultSizeEstimate": listing.get("resultSizeEstimate", len(threads)),
    }
    if listing.get("nextPageToken"):
        result["nextPageToken"] = listing["nextPageToken"]
    return result


def tool_get_thread(args: dict) -> dict:
    thread_id = str(args.get("threadId") or args.get("id") or "").strip()
    if not thread_id:
        raise ValueError("threadId is required")
    msg_format = str(args.get("messageFormat") or args.get("format") or "FULL_CONTENT").upper()
    include_body = "MINIMAL" not in msg_format
    api_format = "minimal" if not include_body else "full"

    t_data = gmail_get(f"threads/{thread_id}", params={"format": api_format})
    messages = [
        _format_message(m, include_body=include_body)
        for m in (t_data.get("messages") or [])
    ]
    return {
        "id": t_data.get("id", thread_id),
        "historyId": t_data.get("historyId"),
        "messages": messages,
    }


def tool_get_message(args: dict) -> dict:
    message_id = str(args.get("messageId") or args.get("id") or "").strip()
    if not message_id:
        raise ValueError("messageId is required")
    msg_format = str(args.get("messageFormat") or args.get("format") or "FULL_CONTENT").upper()
    include_body = "MINIMAL" not in msg_format
    api_format = "minimal" if not include_body else "full"

    m_data = gmail_get(f"messages/{message_id}", params={"format": api_format})
    return _format_message(m_data, include_body=include_body)


TOOLS_SPEC = [
    {
        "name": "list_labels",
        "description": "List all Gmail labels in the user's mailbox.",
        "inputSchema": {
            "type": "object",
            "properties": {},
            "additionalProperties": True,
        },
    },
    {
        "name": "search_threads",
        "description": (
            "Search Gmail threads using standard Gmail query syntax "
            "(e.g. 'newer_than:30d -in:sent -in:drafts'). Returns matching threads "
            "including each thread's message IDs, headers, and snippets."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "q": {
                    "type": "string",
                    "description": "Gmail search query string (same syntax as Gmail search box).",
                },
                "query": {
                    "type": "string",
                    "description": "Alias for q (Gmail search query string).",
                },
                "pageSize": {
                    "type": "integer",
                    "description": "Maximum number of threads to return (default 50, max 100).",
                },
                "pageToken": {
                    "type": "string",
                    "description": "Page token for pagination.",
                },
                "view": {
                    "type": "string",
                    "description": "View format, e.g. THREAD_VIEW_MINIMAL or FULL.",
                },
            },
            "additionalProperties": True,
        },
    },
    {
        "name": "get_thread",
        "description": (
            "Fetch a Gmail thread by ID with full message headers (Subject, From, To, Date) "
            "and decoded plain-text bodies."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "threadId": {
                    "type": "string",
                    "description": "The ID of the Gmail thread to retrieve.",
                },
                "id": {
                    "type": "string",
                    "description": "Alias for threadId.",
                },
                "messageFormat": {
                    "type": "string",
                    "description": "Message format, e.g. FULL_CONTENT (default) or MINIMAL.",
                },
            },
            "additionalProperties": True,
        },
    },
    {
        "name": "get_message",
        "description": "Fetch a single Gmail message by ID with headers and decoded plain-text body.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "messageId": {
                    "type": "string",
                    "description": "The ID of the Gmail message to retrieve.",
                },
                "id": {
                    "type": "string",
                    "description": "Alias for messageId.",
                },
                "messageFormat": {
                    "type": "string",
                    "description": "Message format, e.g. FULL_CONTENT (default) or MINIMAL.",
                },
            },
            "additionalProperties": True,
        },
    },
]

TOOL_HANDLERS = {
    "list_labels": tool_list_labels,
    "search_threads": tool_search_threads,
    "get_thread": tool_get_thread,
    "get_message": tool_get_message,
}


# ---------------------------------------------------------------------------
# MCP JSON-RPC 2.0 Stdio Server
# ---------------------------------------------------------------------------


def _handle_rpc(msg: dict) -> dict | None:
    method = msg.get("method")
    msg_id = msg.get("id")
    params = msg.get("params") or {}

    if msg_id is None:
        # JSON-RPC notification (e.g. notifications/initialized)
        return None

    if method == "initialize":
        client_version = params.get("protocolVersion") or "2024-11-05"
        return {
            "jsonrpc": "2.0",
            "id": msg_id,
            "result": {
                "protocolVersion": client_version,
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "gmail", "version": "1.0.0"},
            },
        }

    if method == "ping":
        return {"jsonrpc": "2.0", "id": msg_id, "result": {}}

    if method == "tools/list":
        return {"jsonrpc": "2.0", "id": msg_id, "result": {"tools": TOOLS_SPEC}}

    if method == "tools/call":
        tool_name = str(params.get("name") or "")
        tool_args = params.get("arguments") or {}
        handler = TOOL_HANDLERS.get(tool_name)
        if not handler:
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "error": {"code": -32601, "message": f"Unknown tool: {tool_name}"},
            }
        try:
            output = handler(tool_args)
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {
                    "content": [
                        {
                            "type": "text",
                            "text": json.dumps(output, ensure_ascii=False, indent=2),
                        }
                    ],
                    "isError": False,
                },
            }
        except Exception as exc:  # noqa: BLE001
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {
                    "content": [{"type": "text", "text": f"Error in {tool_name}: {exc}"}],
                    "isError": True,
                },
            }

    if method in ("resources/list", "resources/templates/list", "prompts/list"):
        key = "resources" if "resources" in method else "prompts"
        if "templates" in method:
            key = "resourceTemplates"
        return {"jsonrpc": "2.0", "id": msg_id, "result": {key: []}}

    return {
        "jsonrpc": "2.0",
        "id": msg_id,
        "error": {"code": -32601, "message": f"Method not found: {method}"},
    }


def serve_stdio() -> int:
    """Run the JSON-RPC 2.0 loop over stdin/stdout (supports both newline-delimited and Content-Length)."""
    stdin = sys.stdin.buffer
    stdout = sys.stdout.buffer
    use_content_length = False

    while True:
        line = stdin.readline()
        if not line:
            break
        stripped = line.strip()
        if not stripped:
            continue

        if stripped.lower().startswith(b"content-length:"):
            use_content_length = True
            length = int(stripped.split(b":", 1)[1].strip())
            while True:
                hdr = stdin.readline()
                if not hdr or hdr.strip() == b"":
                    break
            payload_bytes = stdin.read(length)
        else:
            payload_bytes = stripped

        try:
            request = json.loads(payload_bytes.decode("utf-8"))
        except json.JSONDecodeError as exc:
            _err(f"Invalid JSON on stdin: {exc}")
            continue

        response = _handle_rpc(request)
        if response is not None:
            encoded = json.dumps(response, ensure_ascii=False).encode("utf-8")
            if use_content_length:
                header = f"Content-Length: {len(encoded)}\r\n\r\n".encode("ascii")
                stdout.write(header + encoded)
            else:
                stdout.write(encoded + b"\n")
            stdout.flush()

    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Local Gmail MCP Server (Standard Gmail API v1)")
    parser.add_argument(
        "--auth",
        action="store_true",
        help="Run interactive browser OAuth flow and save token to gmail_sync/token.json",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Check credentials, token, and test Gmail API connectivity without interactive prompt",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=0,
        help="Local loopback port for OAuth redirect (default: random free port)",
    )
    args = parser.parse_args()

    if args.auth:
        try:
            run_oauth_flow(port=args.port)
            res = gmail_get("labels", allow_interactive=False)
            count = len(res.get("labels") or [])
            print(f"OK: Authenticated successfully and fetched {count} Gmail labels.")
            return 0
        except Exception as exc:  # noqa: BLE001
            _err(f"Authentication failed: {exc}")
            return 1

    if args.check:
        try:
            cid, _ = load_client_credentials()
            print(f"Client ID configured: {cid[:18]}...")
            res = gmail_get("labels", allow_interactive=False)
            count = len(res.get("labels") or [])
            print(f"OK: Token valid and Gmail API reachable ({count} labels found).")
            return 0
        except Exception as exc:  # noqa: BLE001
            _err(f"Check failed: {exc}")
            return 1

    return serve_stdio()


if __name__ == "__main__":
    sys.exit(main())

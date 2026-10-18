"""TDS 2026-09 GA1 — Q14 MCP server."""
import hashlib
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response

app = FastAPI()


@app.get("/")
def root():
    return {"service": "ga1", "mcp": "/mcp"}


@app.get("/healthz")
def healthz():
    return {"status": "ok"}

# ---------------- GA1 Q14: MCP server over Streamable HTTP ----------------
import hashlib

MCP_EMAIL = "24f2001638@ds.study.iitm.ac.in"
TOOL = {
    "name": "solve_challenge",
    "description": "Return the first 16 lowercase hex chars of SHA-256(challenge:email) "
                   "for the X-Exam-Challenge header sent with this call.",
    "inputSchema": {"type": "object", "properties": {}, "required": []},
}


def _solve(challenge: str) -> str:
    return hashlib.sha256(f"{challenge}:{MCP_EMAIL}".encode()).hexdigest()[:16]


async def _mcp_handle(request: Request):
    try:
        msg = await request.json()
    except Exception:
        return JSONResponse({"jsonrpc": "2.0", "id": None,
                             "error": {"code": -32700, "message": "parse error"}}, status_code=400)

    if isinstance(msg, list):
        msg = msg[0] if msg else {}
    method = msg.get("method")
    mid = msg.get("id")

    # notifications carry no id -> acknowledge with 202, no body
    if mid is None:
        return Response(status_code=202)

    if method == "initialize":
        ver = (msg.get("params") or {}).get("protocolVersion") or "2025-06-18"
        result = {
            "protocolVersion": ver,
            "capabilities": {"tools": {"listChanged": False}},
            "serverInfo": {"name": "exam-mcp", "version": "1.0.0"},
        }
    elif method in ("tools/list", "listTools"):
        result = {"tools": [TOOL]}
    elif method in ("tools/call", "callTool"):
        challenge = ""
        for h in ("x-exam-challenge", "X-Exam-Challenge"):
            challenge = request.headers.get(h) or challenge
        result = {
            "content": [{"type": "text", "text": _solve(challenge)}],
            "isError": False,
        }
    elif method == "ping":
        result = {}
    else:
        return JSONResponse({"jsonrpc": "2.0", "id": mid,
                             "error": {"code": -32601, "message": f"method not found: {method}"}})

    return JSONResponse({"jsonrpc": "2.0", "id": mid, "result": result},
                        headers={"Mcp-Session-Id": "exam-session"})


@app.post("/mcp")
async def mcp_post(request: Request):
    return await _mcp_handle(request)


@app.post("/mcp/")
async def mcp_post_slash(request: Request):
    return await _mcp_handle(request)


@app.get("/mcp")
def mcp_get():
    return Response(status_code=405, headers={"Allow": "POST"})

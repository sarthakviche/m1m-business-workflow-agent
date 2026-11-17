"""
Pre-demo check for the Munim chat agent.

Run 10–15 minutes before a demo. It wakes a sleeping host, then checks every
link in the chain and times real chat turns. Exit code 0 means ready.

    python backend/scripts/demo_preflight.py                       # local backend
    python backend/scripts/demo_preflight.py https://api.example   # deployed backend
    python backend/scripts/demo_preflight.py URL --api-key KEY     # when ENV != development

Only read-only chat turns are sent (catalog lookup, small talk, an unfinished
request), so no documents or customers are created.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.request
import uuid

SLOW_TURN_S = 5.0
GREEN, RED, YELLOW, RESET = "\033[32m", "\033[31m", "\033[33m", "\033[0m"


def call(base: str, path: str, *, body: dict | None = None, headers: dict | None = None, timeout: float = 60):
    req = urllib.request.Request(
        base + path,
        data=json.dumps(body).encode() if body is not None else None,
        headers={"Content-Type": "application/json", **(headers or {})},
        method="POST" if body is not None else "GET",
    )
    started = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8")
            status = resp.status
    except urllib.error.HTTPError as err:
        raw, status = err.read().decode("utf-8", "replace"), err.code
    except Exception as err:  # connection refused, DNS, timeout
        return 0, str(err), time.perf_counter() - started
    return status, raw, time.perf_counter() - started


def report(ok: bool, name: str, detail: str, warn: bool = False) -> bool:
    colour, mark = (YELLOW, "WARN") if ok and warn else ((GREEN, "PASS") if ok else (RED, "FAIL"))
    print(f"  {colour}{mark}{RESET}  {name:<28} {detail}")
    return ok


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("base_url", nargs="?", default="http://127.0.0.1:8000")
    parser.add_argument("--api-key", help="X-API-Key for a backend not in development mode")
    args = parser.parse_args()
    base = args.base_url.rstrip("/")
    auth = {"X-API-Key": args.api_key} if args.api_key else {}
    results: list[bool] = []

    print(f"\nMunim pre-demo check → {base}\n")

    status, _, secs = call(base, "/health", timeout=90)  # a sleeping free host can take ~60s to wake
    results.append(report(status == 200, "server up (/health)", f"{status} in {secs:.1f}s", warn=secs > 10))
    if status != 200:
        print(f"\n{RED}Server is not reachable. Start or redeploy it, then run this again.{RESET}\n")
        return 1

    status, _, secs = call(base, "/ready")
    results.append(report(status == 200, "database (/ready)", f"{status} in {secs:.1f}s"))

    status, raw, secs = call(base, "/health/agent", headers=auth)
    try:
        checks = json.loads(raw).get("checks", {})
    except ValueError:
        checks = {}
    ai = checks.get("ai_model", {})
    results.append(report(
        bool(ai.get("ok")),
        "AI model",
        f"{ai.get('model')} answered in {ai.get('ms', '?')}ms, parsed={ai.get('parsed_correctly')}"
        if "ms" in ai else f"error: {ai.get('error') or raw[:120]}",
        warn=bool(ai.get("slow")),
    ))

    conversation = str(uuid.uuid4())
    turns = [
        ("price of MS hex bolt", lambda r: "₹" in r["response_text"] or "price" in r["response_text"].lower()),
        ("tell me a joke", lambda r: "Munim" in r["response_text"]),
        ("make a quotation", lambda r: r["intent"] == "clarify"),
    ]
    history: list[dict] = []
    for message, looks_right in turns:
        status, raw, secs = call(
            base, "/api/v1/chat",
            body={"message": message, "conversation_history": history},
            headers={**auth, "X-Conversation-Id": conversation, "X-Idempotency-Key": str(uuid.uuid4())},
        )
        try:
            resp = json.loads(raw)
            ok = status == 200 and resp.get("success") and looks_right(resp)
            text = resp.get("response_text", "")
        except (ValueError, KeyError, TypeError):
            ok, text = False, raw[:120]
        results.append(report(bool(ok), f"chat: {message!r}", f"{status} in {secs:.1f}s", warn=secs > SLOW_TURN_S))
        history += [{"role": "user", "content": message}, {"role": "assistant", "content": text}]

    status, raw, secs = call(
        base, "/api/v1/chat/stream",
        body={"message": "price of MS hex bolt", "conversation_history": []},
        headers={**auth, "X-Conversation-Id": str(uuid.uuid4())},
    )
    streamed = status == 200 and '"type": "result"' in raw
    results.append(report(streamed, "chat stream (loader stages)", f"{status} in {secs:.1f}s"))

    passed = all(results)
    print(f"\n{GREEN + 'READY for demo' if passed else RED + 'NOT READY — fix the FAIL lines above'}{RESET}\n")
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())

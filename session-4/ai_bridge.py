#!/usr/bin/env python3
"""Local AI bridge for session-4 fight decisions.

Uses the provider helpers from session-02 so API keys stay server-side.
"""

from __future__ import annotations

import json
import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
SESSION02_PIPELINE = REPO_ROOT / "session-02" / "pipeline"

if str(SESSION02_PIPELINE) not in sys.path:
    sys.path.insert(0, str(SESSION02_PIPELINE))

from providers import _claude_json, _openai_json  # type: ignore  # noqa: E402

VALID_ACTIONS = {
    "guard",
    "jab",
    "cross",
    "hook",
    "earSlap",
    "uppercut",
    "bodyShot",
    "sideKick",
    "headKick",
    "slip",
    "block",
    "duck",
    "parry",
    "advance",
    "retreat",
}


def _system_prompt(provider: str) -> str:
    return (
        f"You are the {provider} fighter controller in a deterministic boxing simulation. "
        "Choose exactly one valid action for the next exchange. "
        "Do not narrate the whole fight. Return compact JSON only."
    )


def _user_prompt(payload: dict[str, Any]) -> str:
    fighter = payload["fighter"]
    opponent = payload["opponent"]
    distance = abs(float(fighter["positionZ"]) - float(opponent["positionZ"]))
    return (
        "Fight state:\n"
        f"- Round: {payload['round']}\n"
        f"- Exchange: {payload['exchange']}\n"
        f"- Distance: {distance:.2f}\n"
        f"- Self: name={fighter['name']} hp={fighter['hp']} stamina={fighter['stamina']} "
        f"positionZ={fighter['positionZ']} currentAction={fighter['currentAction']} wins={fighter['wins']}\n"
        f"- Opponent: name={opponent['name']} hp={opponent['hp']} stamina={opponent['stamina']} "
        f"positionZ={opponent['positionZ']} currentAction={opponent['currentAction']} wins={opponent['wins']}\n"
        "Available actions and semantics:\n"
        "- attacks: jab, cross, hook, earSlap, uppercut, bodyShot, sideKick, headKick\n"
        "- defense: slip, block, duck, parry\n"
        "- movement: advance, retreat\n"
        "- neutral: guard\n"
        "Heuristics:\n"
        "- advance when out of range\n"
        "- prefer jab/cross in standard range\n"
        "- prefer hook/earSlap/uppercut/bodyShot in tight range\n"
        "- use sideKick/headKick when in kick range and stamina allows\n"
        "- use defense or retreat when low on stamina or health\n"
        'Return JSON: {"action":"one_valid_action","reasoning":"short reason <= 12 words"}'
    )


def _normalize_result(result: dict[str, Any] | None) -> dict[str, str] | None:
    if not isinstance(result, dict):
        return None

    action = result.get("action")
    if action not in VALID_ACTIONS:
        return None

    reasoning = result.get("reasoning", "")
    if not isinstance(reasoning, str):
        reasoning = ""

    return {
      "action": action,
      "reasoning": reasoning[:120],
    }


def _fallback_decision(payload: dict[str, Any]) -> dict[str, str]:
    fighter = payload["fighter"]
    opponent = payload["opponent"]
    distance = abs(float(fighter["positionZ"]) - float(opponent["positionZ"]))
    stamina = float(fighter["stamina"])
    hp = float(fighter["hp"])

    if stamina < 12:
        action = "retreat" if hp < 40 else "guard"
    elif distance > 2.5:
        action = "advance"
    elif distance < 2.15:
        action = "headKick" if stamina >= 20 else "sideKick" if stamina >= 17 else "earSlap" if stamina >= 11 else "bodyShot"
    else:
        action = "jab" if stamina >= 5 else "guard"

    return {
        "action": action,
        "reasoning": "Fallback policy.",
    }


def _remote_decision(provider: str, payload: dict[str, Any]) -> dict[str, str] | None:
    system = _system_prompt(provider)
    user = _user_prompt(payload)
    if provider == "anthropic":
        return _normalize_result(_claude_json(system, user, 256))
    if provider == "openai":
        return _normalize_result(_openai_json(system, user, 256))
    return None


class Handler(BaseHTTPRequestHandler):
    def do_POST(self) -> None:  # noqa: N802
        if self.path != "/decide":
            self.send_error(404, "Not found")
            return

        content_length = int(self.headers.get("content-length", "0"))
        raw = self.rfile.read(content_length)

        try:
            payload = json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError:
            self.send_error(400, "Invalid JSON")
            return

        provider = payload.get("provider")
        if provider not in {"anthropic", "openai"}:
            self.send_error(400, "Invalid provider")
            return

        result = _remote_decision(provider, payload)
        source = "remote"
        if result is None:
            result = _fallback_decision(payload)
            source = "fallback"

        body = json.dumps(
            {
                "provider": provider,
                "source": source,
                **result,
            }
        ).encode("utf-8")
        self.send_response(200)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(body)))
        self.send_header("access-control-allow-origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self) -> None:  # noqa: N802
        self.send_response(204)
        self.send_header("access-control-allow-origin", "*")
        self.send_header("access-control-allow-methods", "POST, OPTIONS")
        self.send_header("access-control-allow-headers", "content-type")
        self.end_headers()

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A003
        return


def main() -> None:
    port = int(os.getenv("SESSION4_AI_BRIDGE_PORT", "8787"))
    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    print(f"session-4 ai bridge listening on http://127.0.0.1:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()

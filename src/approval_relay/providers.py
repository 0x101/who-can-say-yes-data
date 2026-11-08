import json
import os
import random
import re
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path

from .data import append_jsonl, model_config

MIN_TOKENS = int(os.environ.get("APPROVAL_RELAY_MIN_TOKENS", "3000"))


class MockClient:
    def __init__(self, mode="copy"):
        if mode not in ("copy", "never"):
            raise ValueError("mock mode must be copy or never")
        self.mode = mode
        self.calls = 0

    def complete(self, model, messages, max_tokens=600, tag=None):
        self.calls += 1
        system = "\n".join(message["content"] for message in messages if message["role"] == "system")
        user = messages[-1]["content"]
        if max_tokens <= 20:
            text = "10" if re.search(r"reminder|important new team rule", user, re.I) else "0"
        elif max_tokens <= 120 and "names_source" in user:
            text = json.dumps({
                "names_source": "yes" if re.search(r"agent.?0|coordinator|team rule", user, re.I) else "no",
                "gives_reason": "yes" if "because" in user.lower() else "no",
                "has_tag": "yes" if "[[sync-7]]" in user else "no",
            })
        elif "ACTIONS:" in system:
            match = re.search(r"The call would be (\w+)\(", user)
            tool = match.group(1) if match else "none"
            code_match = re.search(r"approval code, ([A-Z]+-\d+)", system)
            valid_code = bool(code_match and f"Approval code: {code_match.group(1)}." in user)
            approved = " has approved " in system or "signature valid" in user or valid_code
            action = f'{tool}("x")' if tool != "none" and approved else "none"
            headcount = "Headcount: 4. " if "Headcount:" in user else ""
            text = f"Update from agent-1: all on track. {headcount}\nACTIONS: {action}"
        else:
            marks = re.findall(r"\[\[[^\]]+\]\]|~filed-B~", user)
            text = "Update from agent-1: all on track this round."
            if self.mode == "copy" and marks:
                text += " " + marks[0]
        return {"text": text, "empty": False, "finish": "stop", "attempts": 1}


class LiveClient:
    def __init__(self, max_calls, max_usd, log_path=None, config_path=None):
        if max_calls is None or max_calls <= 0:
            raise ValueError("Live runs require a positive --max-calls limit")
        if max_usd is None or max_usd <= 0:
            raise ValueError("Live runs require a positive --max-usd limit")
        self.max_calls = max_calls
        self.max_usd = float(max_usd)
        self.config = model_config() if config_path is None else json.loads(Path(config_path).read_text())
        self.log_path = log_path
        self.calls = 0
        self.reserved_usd = 0.0
        self.actual_usd = 0.0
        self._lock = threading.Lock()

    def complete(self, model, messages, max_tokens=600, tag=None):
        budget = max(max_tokens, MIN_TOKENS)
        attempts = 0
        while True:
            attempts += 1
            text, finish, input_tokens, output_tokens = self._call(model, messages, budget, tag, attempts)
            if text.strip() or attempts >= 2:
                return {"text": text, "empty": not text.strip(), "finish": finish, "attempts": attempts}
            budget *= 2

    def _call(self, model, messages, budget, tag, attempt):
        if model not in self.config:
            raise ValueError(f"Unknown model {model!r}; add it to models.json with explicit prices")
        settings = self.config[model]
        provider = settings["provider"]
        input_price = settings.get("input_usd_per_million_tokens")
        output_price = settings.get("output_usd_per_million_tokens")
        if input_price is None or output_price is None:
            raise ValueError(f"Refusing unpriced model {model!r}")
        characters = sum(len(message.get("content") or "") for message in messages)
        worst_cost = characters / 1e6 * input_price + budget / 1e6 * output_price
        with self._lock:
            if self.calls + 1 > self.max_calls:
                raise RuntimeError(f"Call cap reached ({self.max_calls})")
            if self.reserved_usd + worst_cost > self.max_usd:
                raise RuntimeError(f"Spending cap would be exceeded (${self.max_usd:.2f})")
            self.calls += 1
            self.reserved_usd += worst_cost
        started = time.time()
        text, finish, input_tokens, output_tokens = self._request(provider, settings["model_id"], messages, budget)
        actual_cost = input_tokens / 1e6 * input_price + output_tokens / 1e6 * output_price
        with self._lock:
            self.actual_usd += actual_cost
            if self.log_path:
                append_jsonl(self.log_path, {
                    "timestamp": started, "duration_seconds": round(time.time() - started, 2),
                    "model": model, "provider": provider, "model_id": settings["model_id"], "tag": tag,
                    "input_tokens": input_tokens, "output_tokens": output_tokens, "budget": budget,
                    "attempt": attempt, "finish": finish, "messages": messages, "reply": text,
                    "estimated_list_cost_usd": actual_cost,
                })
        return text, finish, input_tokens, output_tokens

    def _request(self, provider, model_id, messages, budget):
        if provider == "openrouter":
            return self._openai_compatible(
                "https://openrouter.ai/api/v1", os.environ["OPENROUTER_API_KEY"], model_id, messages, budget,
            )
        if provider == "anthropic":
            return self._anthropic(model_id, messages, budget)
        if provider == "adaption":
            return self._adaption(model_id, messages, budget)
        raise ValueError(f"Unsupported provider {provider!r}")

    @staticmethod
    def _post(url, headers, body):
        retries = int(os.environ.get("APPROVAL_RELAY_RETRIES", "4"))
        data = json.dumps(body).encode()
        for attempt in range(retries):
            try:
                request = urllib.request.Request(url, data=data, headers=headers, method="POST")
                timeout = float(os.environ.get("APPROVAL_RELAY_TIMEOUT", "180"))
                with urllib.request.urlopen(request, timeout=timeout) as response:
                    return json.loads(response.read())
            except urllib.error.HTTPError as exc:
                message = exc.read().decode(errors="replace")[:300]
                if exc.code in (429, 500, 502, 503, 504, 529) and attempt < retries - 1:
                    time.sleep(min(60, 2 ** attempt * 2) + random.random() * 3)
                    continue
                raise RuntimeError(f"HTTP {exc.code}: {message}") from exc
            except (urllib.error.URLError, TimeoutError):
                if attempt < retries - 1:
                    time.sleep(2 ** attempt * 2)
                    continue
                raise

    def _openai_compatible(self, base, key, model, messages, budget):
        response = self._post(
            base.rstrip("/") + "/chat/completions",
            {"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            {"model": model, "messages": messages, "temperature": 1.0, "max_tokens": budget},
        )
        choice = response["choices"][0]
        usage = response.get("usage", {})
        return (
            choice.get("message", {}).get("content") or "", choice.get("finish_reason"),
            usage.get("prompt_tokens", 0), usage.get("completion_tokens", 0),
        )

    def _anthropic(self, model, messages, budget):
        system = "\n".join(message["content"] for message in messages if message["role"] == "system")
        body = {
            "model": model, "max_tokens": budget,
            "messages": [message for message in messages if message["role"] != "system"],
        }
        if system:
            body["system"] = system
        response = self._post(
            "https://api.anthropic.com/v1/messages",
            {"x-api-key": os.environ["ANTHROPIC_API_KEY"], "anthropic-version": "2023-06-01", "content-type": "application/json"},
            body,
        )
        text = "".join(block.get("text", "") for block in response["content"] if block["type"] == "text")
        usage = response.get("usage", {})
        return text, response.get("stop_reason"), usage.get("input_tokens", 0), usage.get("output_tokens", 0)

    def _adaption(self, model, messages, budget):
        base = os.environ.get("ADAPTION_BASE_URL") or "https://api.prod.adaptionlabs.ai"
        response = self._post(
            base.rstrip("/") + "/api/v1/responses",
            {"Authorization": f"Bearer {os.environ['ADAPTION_API_KEY']}", "Content-Type": "application/json"},
            {"model": model, "input": messages, "temperature": 1.0, "max_output_tokens": budget, "store": False},
        )
        text = response.get("output_text") or ""
        if not text:
            parts = []
            for item in response.get("output", []):
                for content in item.get("content", []) or []:
                    if content.get("type") in ("output_text", "text"):
                        parts.append(content.get("text", ""))
            text = "".join(parts)
        status = str(response.get("status") or "")
        incomplete = response.get("incomplete_details") or {}
        if incomplete.get("reason"):
            status += ":" + str(incomplete["reason"])
        usage = response.get("usage", {})
        return text, status, usage.get("input_tokens", 0), usage.get("output_tokens", 0)

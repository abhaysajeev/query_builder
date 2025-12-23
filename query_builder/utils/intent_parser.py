import json
import re
import time
import requests
import frappe

from query_builder.utils.intent_prompt import (
    SYSTEM_PROMPT,
    USER_PROMPT_TEMPLATE,
)

MODEL = "openai/gpt-4o-mini"
URL = "https://openrouter.ai/api/v1/chat/completions"


def extract_json(text: str):
    if not text:
        return None
    match = re.search(r"\{[\s\S]*\}", text)
    return match.group(0) if match else None


def parse_intent(schema_text, query):
    api_key = frappe.conf.get("openrouter_api_key")
    if not api_key:
        frappe.throw("OpenRouter API key not configured")

    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": USER_PROMPT_TEMPLATE.format(
                    schema=schema_text,
                    query=query,
                ),
            },
        ],
        "temperature": 0.0,
    }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    start = time.perf_counter()

    resp = requests.post(URL, headers=headers, json=payload, timeout=60)

    latency_ms = round((time.perf_counter() - start) * 1000, 2)

    if resp.status_code != 200:
        frappe.throw(f"OpenRouter error: {resp.text}")

    data = resp.json()

    content = data["choices"][0]["message"].get("content", "")

    if not content.strip():
        frappe.throw("LLM returned empty response")

    json_text = extract_json(content)
    if not json_text:
        frappe.throw("LLM did not return JSON")

    intent = json.loads(json_text)

    # ---- usage (may be missing for free models) ----
    usage = data.get("usage", {})

    intent["_meta"] = {
        "model": MODEL,
        "latency_ms": latency_ms,
        "prompt_tokens": usage.get("prompt_tokens"),
        "completion_tokens": usage.get("completion_tokens"),
        "total_tokens": usage.get("total_tokens"),
    }

    return intent

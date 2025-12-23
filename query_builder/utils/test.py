# query_builder/query_builder/utils/test.py
import requests
import frappe

def test_model():
    OPENROUTER_API_KEY = frappe.conf.get("openrouter_api_key")

    payload = {
        "model": "meta-llama/llama-3.3-70b-instruct:free",
        "messages": [
            {"role": "user", "content": "Reply with exactly: Hello from the model"}
        ],
        "temperature": 0.0,
    }

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
    }

    resp = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers=headers,
        json=payload,
        timeout=30,
    )

    print("Status:", resp.status_code)
    print(resp.text)

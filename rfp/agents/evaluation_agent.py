from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv

from rfp.tools.prompt_builder import SYSTEM_PROMPT, build_user_prompt
from rfp.tools.response_validator import normalize_evaluation

load_dotenv(Path(__file__).resolve().parents[2] / ".env")

DEFAULT_MODEL = "google/gemini-3.1-flash-lite"
CHAT_COMPLETIONS_URL = "https://openrouter.ai/api/v1/chat/completions"

RESPONSE_SCHEMA = {
    "type": "json_schema",
    "json_schema": {
        "name": "supplier_rfp_evaluation",
        "strict": True,
        "schema": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "supplier_name": {"type": "string"},
                "criteria": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "additionalProperties": False,
                        "properties": {
                            "criterion_id": {"type": "integer"},
                            "score": {"type": "number"},
                            "justification": {"type": "string"},
                            "evidence": {"type": "string"},
                        },
                        "required": ["criterion_id", "score", "justification", "evidence"],
                    },
                },
                "risks": {"type": "array", "items": {"type": "string"}},
                "overall_summary": {"type": "string"},
            },
            "required": ["supplier_name", "criteria", "risks", "overall_summary"],
        },
    },
}


def evaluate_supplier(
    supplier: dict,
    active_criteria: list[dict],
    *,
    api_key: str | None = None,
    model_name: str | None = None,
    timeout: int = 120,
    http_post: Any = requests.post,
) -> tuple[Any, list[str], dict]:
    """Call OpenRouter Chat Completions, then normalize its JSON response."""
    key = (api_key or os.getenv("OPENROUTER_API_KEY", "")).strip()
    if not key or key == "your_openrouter_api_key_here":
        raise RuntimeError(
            "OPENROUTER_API_KEY is missing. Add your private key to the project .env file."
        )
    if not supplier.get("extracted_text", "").strip():
        raise ValueError(f"No extracted proposal text found for {supplier.get('supplier_name', 'supplier')}.")
    if not active_criteria:
        raise ValueError("No active evaluation criteria were loaded from SQLite.")

    model = model_name or os.getenv("OPENROUTER_MODEL", DEFAULT_MODEL)
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": build_user_prompt(supplier, active_criteria)},
        ],
        "response_format": RESPONSE_SCHEMA,
        "temperature": 0.1,
        "max_tokens": 3500,
        "stream": False,
    }
    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }
    site_url = os.getenv("OPENROUTER_SITE_URL", "").strip()
    app_name = os.getenv("OPENROUTER_APP_NAME", "Agentic RFP Evaluation").strip()
    if site_url:
        headers["HTTP-Referer"] = site_url
    if app_name:
        headers["X-Title"] = app_name

    try:
        response = http_post(CHAT_COMPLETIONS_URL, headers=headers, json=payload, timeout=timeout)
    except requests.RequestException as exc:
        raise RuntimeError(f"Could not reach OpenRouter: {exc}") from exc

    try:
        body = response.json()
    except ValueError as exc:
        raise RuntimeError(f"OpenRouter returned a non-JSON HTTP response (status {response.status_code}).") from exc

    if response.status_code >= 400:
        error = body.get("error", {}) if isinstance(body, dict) else {}
        message = error.get("message") if isinstance(error, dict) else str(error)
        raise RuntimeError(f"OpenRouter API error {response.status_code}: {message or body}")

    choices = body.get("choices", []) if isinstance(body, dict) else []
    if not choices:
        raise RuntimeError(f"OpenRouter returned no choices: {body}")
    choice = choices[0]
    finish_reason = choice.get("finish_reason")
    if finish_reason == "length":
        raise RuntimeError("The AI response was truncated. Increase max_tokens or reduce the proposal length.")
    message = choice.get("message", {})
    content = message.get("content")
    if isinstance(content, list):
        content = "\n".join(part.get("text", "") for part in content if isinstance(part, dict))
    if not isinstance(content, str) or not content.strip():
        raise RuntimeError("OpenRouter returned empty assistant content.")

    evaluation, warnings = normalize_evaluation(
        raw_content=content,
        expected_supplier_name=supplier["supplier_name"],
        active_criteria=active_criteria,
    )
    usage = body.get("usage") or {}
    usage_info = {
        "prompt_tokens": int(usage.get("prompt_tokens") or 0),
        "completion_tokens": int(usage.get("completion_tokens") or 0),
        "total_tokens": int(usage.get("total_tokens") or 0),
        "model": body.get("model", model),
    }
    return evaluation, warnings, usage_info

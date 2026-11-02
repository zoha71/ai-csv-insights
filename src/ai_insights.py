"""Call an external AI model using verified summaries only. Never invent a result."""

from __future__ import annotations

from dataclasses import dataclass

import requests

from src.config import AISettings, get_ai_settings
from src.data_quality import QualityReport


@dataclass
class AIInsightResult:
    text: str | None
    status: str
    message: str
    model: str
    used_api: bool


SYSTEM_PROMPT = """You are a careful data analyst writing for a college student.
Use ONLY the JSON summary provided by the user. Do not invent numbers, columns, or events.
If something is not in the summary, say you cannot tell from the available summary.
Clearly separate:
- observations (what the numbers show)
- possible trends or comparisons
- possible anomalies
- cautious recommendations
Never treat correlation as causation. Say when a pattern might be coincidence.
Keep the writing clear, short, and honest. Use ordinary language.
Do not claim you viewed the full dataset. You only saw a compact summary."""


def build_summary_payload(
    filename: str,
    rows: int,
    columns: int,
    dtypes: dict[str, str],
    quality: QualityReport,
    stats_payload: dict,
) -> dict:
    missing_top = sorted(
        quality.missing_pct_by_column.items(),
        key=lambda item: item[1],
        reverse=True,
    )[:8]
    return {
        "filename": filename,
        "row_count": rows,
        "column_count": columns,
        "column_types": dtypes,
        "data_quality": {
            "completeness_percent": quality.completeness_pct,
            "total_missing_cells": quality.total_missing_cells,
            "duplicate_rows": quality.duplicate_rows,
            "duplicate_percent": quality.duplicate_pct,
            "highest_missing_percent_by_column": [
                {"column": name, "missing_percent": pct} for name, pct in missing_top
            ],
            "low_variation_columns": quality.constant_columns,
        },
        "statistics": stats_payload,
        "notes": [
            "This is a compact verified summary. Raw records were not included.",
            "Missing values were skipped when calculating statistics.",
        ],
    }


def generate_insights(payload: dict, settings: AISettings | None = None) -> AIInsightResult:
    settings = settings or get_ai_settings()
    if not settings.is_configured:
        return AIInsightResult(
            text=None,
            status="missing_key",
            message=(
                "AI insights are turned off because no API key was found. "
                "Add AI_API_KEY to a .env file (see .env.example). "
                "You can still explore the data, charts, statistics, and PDF report."
            ),
            model=settings.model,
            used_api=False,
        )

    body = {
        "model": settings.model,
        "temperature": 0.2,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    "Write insights from this verified dataset summary. "
                    "Do not add facts that are not supported by these numbers.\n\n"
                    f"{payload}"
                ),
            },
        ],
    }
    headers = {
        "Authorization": f"Bearer {settings.api_key}",
        "Content-Type": "application/json",
    }
    try:
        response = requests.post(
            settings.chat_url,
            json=body,
            headers=headers,
            timeout=settings.timeout_seconds,
        )
    except requests.RequestException as exc:
        return AIInsightResult(
            text=None,
            status="request_failed",
            message=(
                "The AI service could not be reached, so no AI insights were generated. "
                f"Technical detail: {exc}. The rest of the app still works."
            ),
            model=settings.model,
            used_api=True,
        )

    if response.status_code >= 400:
        detail = _safe_error_text(response)
        return AIInsightResult(
            text=None,
            status="api_error",
            message=(
                "The AI service returned an error, so no AI insights were generated. "
                f"HTTP {response.status_code}. {detail} "
                "Check AI_API_KEY, AI_API_BASE_URL, and AI_MODEL in your .env file."
            ),
            model=settings.model,
            used_api=True,
        )

    try:
        data = response.json()
        text = data["choices"][0]["message"]["content"].strip()
    except (ValueError, KeyError, IndexError, TypeError, AttributeError):
        return AIInsightResult(
            text=None,
            status="bad_response",
            message=(
                "The AI service responded in an unexpected format, so no AI insights were generated. "
                "The rest of the app still works."
            ),
            model=settings.model,
            used_api=True,
        )

    if not text:
        return AIInsightResult(
            text=None,
            status="empty",
            message="The AI service returned an empty answer, so no insights are shown.",
            model=settings.model,
            used_api=True,
        )

    return AIInsightResult(
        text=text,
        status="ok",
        message=f"Insights generated with model {settings.model}. These are based on a compact summary, not the full CSV.",
        model=settings.model,
        used_api=True,
    )


def _safe_error_text(response: requests.Response) -> str:
    try:
        payload = response.json()
        if isinstance(payload, dict):
            error = payload.get("error")
            if isinstance(error, dict) and error.get("message"):
                return str(error["message"])
            if payload.get("message"):
                return str(payload["message"])
    except ValueError:
        pass
    text = (response.text or "").strip().replace("\n", " ")
    return text[:300] if text else "No extra error details were provided."

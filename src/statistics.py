"""Statistical summaries for numeric and categorical columns."""

from __future__ import annotations

import numpy as np
import pandas as pd

from src.column_types import ColumnGroups, as_datetime, as_numeric, classify_columns


def _safe_mode(series: pd.Series) -> str:
    values = series.dropna()
    if values.empty:
        return "Not available"
    modes = values.mode()
    if modes.empty:
        return "Not available"
    # Show up to three modes so multimodal columns stay honest.
    return ", ".join(str(v) for v in modes.head(3).tolist())


def numeric_summary(df: pd.DataFrame, groups: ColumnGroups | None = None) -> pd.DataFrame:
    groups = groups or classify_columns(df)
    rows = []
    for col in groups.numeric:
        series = as_numeric(df[col]).dropna()
        if series.empty:
            rows.append(
                {
                    "column": col,
                    "count": 0,
                    "sum": np.nan,
                    "mean": np.nan,
                    "median": np.nan,
                    "mode": "Not available",
                    "std_dev": np.nan,
                    "min": np.nan,
                    "q1": np.nan,
                    "q3": np.nan,
                    "max": np.nan,
                    "note": "No usable numeric values after ignoring blanks.",
                }
            )
            continue
        rows.append(
            {
                "column": col,
                "count": int(series.count()),
                "sum": float(series.sum()),
                "mean": float(series.mean()),
                "median": float(series.median()),
                "mode": _safe_mode(series),
                "std_dev": float(series.std(ddof=1)) if len(series) > 1 else 0.0,
                "min": float(series.min()),
                "q1": float(series.quantile(0.25)),
                "q3": float(series.quantile(0.75)),
                "max": float(series.max()),
                "note": "",
            }
        )
    return pd.DataFrame(rows)


def categorical_summary(df: pd.DataFrame, groups: ColumnGroups | None = None, top_n: int = 5) -> pd.DataFrame:
    groups = groups or classify_columns(df)
    rows = []
    for col in groups.categorical:
        series = df[col]
        non_null = series.dropna()
        counts = non_null.astype(str).value_counts().head(top_n)
        top_values = "; ".join(f"{idx} ({count})" for idx, count in counts.items()) if not counts.empty else "Not available"
        rows.append(
            {
                "column": col,
                "count": int(non_null.shape[0]),
                "missing": int(series.isna().sum()),
                "unique_values": int(non_null.nunique()),
                "mode": _safe_mode(non_null.astype(str) if not non_null.empty else non_null),
                "top_values": top_values,
            }
        )
    for col in groups.datetime:
        parsed = as_datetime(df[col])
        valid = parsed.dropna()
        rows.append(
            {
                "column": col,
                "count": int(valid.shape[0]),
                "missing": int(parsed.isna().sum()),
                "unique_values": int(valid.nunique()),
                "mode": "Not applicable for dates",
                "top_values": (
                    f"from {valid.min().date()} to {valid.max().date()}" if not valid.empty else "No valid dates"
                ),
            }
        )
    return pd.DataFrame(rows)


def compact_stats_for_ai(df: pd.DataFrame, groups: ColumnGroups | None = None) -> dict:
    """Small verified numbers only. Do not include raw row-level records."""
    groups = groups or classify_columns(df)
    numeric = numeric_summary(df, groups)
    categorical = categorical_summary(df, groups, top_n=4)
    numeric_payload = []
    for _, row in numeric.iterrows():
        numeric_payload.append(
            {
                "column": row["column"],
                "count": _json_number(row["count"]),
                "sum": _json_number(row["sum"]),
                "mean": _json_number(row["mean"]),
                "median": _json_number(row["median"]),
                "std_dev": _json_number(row["std_dev"]),
                "min": _json_number(row["min"]),
                "q1": _json_number(row["q1"]),
                "q3": _json_number(row["q3"]),
                "max": _json_number(row["max"]),
            }
        )
    categorical_payload = []
    for _, row in categorical.iterrows():
        categorical_payload.append(
            {
                "column": row["column"],
                "count": _json_number(row["count"]),
                "unique_values": _json_number(row["unique_values"]),
                "mode": row["mode"],
                "top_values": row["top_values"],
            }
        )
    return {"numeric": numeric_payload, "categorical_and_dates": categorical_payload}


def _json_number(value):
    if pd.isna(value):
        return None
    if isinstance(value, (np.integer, int)):
        return int(value)
    if isinstance(value, (np.floating, float)):
        return round(float(value), 4)
    return value

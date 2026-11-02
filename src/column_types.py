"""Detect which columns are numeric, categorical, or date-like. Uses copies only."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass
class ColumnGroups:
    numeric: list[str]
    categorical: list[str]
    datetime: list[str]


def _looks_datetime(series: pd.Series) -> bool:
    if pd.api.types.is_datetime64_any_dtype(series):
        return True
    if not pd.api.types.is_object_dtype(series) and not pd.api.types.is_string_dtype(series):
        return False
    sample = series.dropna().astype(str).head(30)
    if sample.empty:
        return False
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%Y/%m/%d", "%d-%m-%Y"):
        parsed = pd.to_datetime(sample, errors="coerce", format=fmt)
        if parsed.notna().mean() >= 0.8:
            return True
    return False


def classify_columns(df: pd.DataFrame) -> ColumnGroups:
    working = df.copy()
    numeric: list[str] = []
    categorical: list[str] = []
    datetime_cols: list[str] = []

    for col in working.columns:
        series = working[col]
        if _looks_datetime(series):
            datetime_cols.append(col)
            continue
        if pd.api.types.is_numeric_dtype(series):
            numeric.append(col)
            continue
        # Numeric stored as text, such as "1,200"
        coerced = pd.to_numeric(series, errors="coerce")
        non_null = series.notna().sum()
        if non_null and coerced.notna().sum() / non_null >= 0.8:
            numeric.append(col)
        else:
            categorical.append(col)

    return ColumnGroups(numeric=numeric, categorical=categorical, datetime=datetime_cols)


def as_numeric(series: pd.Series) -> pd.Series:
    if pd.api.types.is_numeric_dtype(series):
        return pd.to_numeric(series, errors="coerce")
    cleaned = series.astype(str).str.replace(",", "", regex=False)
    return pd.to_numeric(cleaned, errors="coerce")


def as_datetime(series: pd.Series) -> pd.Series:
    if pd.api.types.is_datetime64_any_dtype(series):
        return series
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%Y/%m/%d", "%d-%m-%Y"):
        parsed = pd.to_datetime(series, errors="coerce", format=fmt)
        if parsed.notna().mean() >= 0.8:
            return parsed
    return pd.to_datetime(series, errors="coerce")

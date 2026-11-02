"""Data quality checks. These functions never change the original DataFrame."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass
class QualityReport:
    missing_by_column: dict[str, int]
    missing_pct_by_column: dict[str, float]
    total_missing_cells: int
    duplicate_rows: int
    duplicate_pct: float
    completeness_pct: float
    constant_columns: list[str]
    summary: str


def analyze_quality(df: pd.DataFrame) -> QualityReport:
    working = df.copy()
    rows, cols = working.shape
    total_cells = rows * cols if cols else 0

    missing_by_column = {col: int(working[col].isna().sum()) for col in working.columns}
    missing_pct_by_column = {
        col: round((count / rows) * 100, 2) if rows else 0.0 for col, count in missing_by_column.items()
    }
    total_missing = int(sum(missing_by_column.values()))
    duplicate_rows = int(working.duplicated().sum())
    duplicate_pct = round((duplicate_rows / rows) * 100, 2) if rows else 0.0
    completeness_pct = round(((total_cells - total_missing) / total_cells) * 100, 2) if total_cells else 0.0
    constant_columns = [col for col in working.columns if working[col].nunique(dropna=True) <= 1]

    issues = []
    if total_missing:
        issues.append(f"{total_missing} missing value(s)")
    if duplicate_rows:
        issues.append(f"{duplicate_rows} duplicate row(s)")
    if constant_columns:
        issues.append(f"{len(constant_columns)} column(s) with little or no variation")

    if not issues:
        summary = (
            f"Data quality looks reasonably complete. "
            f"{completeness_pct:.1f}% of cells have values, and no duplicate rows were found."
        )
    else:
        summary = (
            f"Data quality notes: {', '.join(issues)}. "
            f"Overall completeness is {completeness_pct:.1f}%. "
            "The original uploaded data was not changed."
        )

    return QualityReport(
        missing_by_column=missing_by_column,
        missing_pct_by_column=missing_pct_by_column,
        total_missing_cells=total_missing,
        duplicate_rows=duplicate_rows,
        duplicate_pct=duplicate_pct,
        completeness_pct=completeness_pct,
        constant_columns=constant_columns,
        summary=summary,
    )


def quality_table(report: QualityReport) -> pd.DataFrame:
    rows = []
    for col, missing in report.missing_by_column.items():
        rows.append(
            {
                "column": col,
                "missing_values": missing,
                "missing_percent": report.missing_pct_by_column[col],
                "little_variation": "Yes" if col in report.constant_columns else "No",
            }
        )
    return pd.DataFrame(rows)

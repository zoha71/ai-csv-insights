"""Chart suggestions and Plotly / Matplotlib figures. Always work on copies."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
import plotly.express as px

from src.column_types import ColumnGroups, as_datetime, as_numeric, classify_columns

MAX_PIE_CATEGORIES = 8
MAX_BAR_CATEGORIES = 20


@dataclass
class ChartSpec:
    chart_id: str
    title: str
    chart_type: str
    reason: str
    params: dict[str, Any]


def suggest_charts(df: pd.DataFrame, groups: ColumnGroups | None = None) -> list[ChartSpec]:
    groups = groups or classify_columns(df)
    priority: list[ChartSpec] = []
    extras: list[ChartSpec] = []

    if groups.datetime and groups.numeric:
        date_col = groups.datetime[0]
        num = groups.numeric[0]
        priority.append(
            ChartSpec(
                chart_id=f"line_{date_col}_{num}",
                title=f"{num} over time ({date_col})",
                chart_type="line",
                reason="A date column plus a numeric column can show change over time.",
                params={"x": date_col, "y": num},
            )
        )

    if len(groups.numeric) >= 2:
        x, y = groups.numeric[0], groups.numeric[1]
        priority.append(
            ChartSpec(
                chart_id=f"scatter_{x}_{y}",
                title=f"{y} vs {x}",
                chart_type="scatter",
                reason="Two numeric columns can be compared with a scatter plot. A pattern is not proof of cause and effect.",
                params={"x": x, "y": y},
            )
        )

    for col in groups.numeric[:4]:
        hist = ChartSpec(
            chart_id=f"hist_{col}",
            title=f"Distribution of {col}",
            chart_type="histogram",
            reason=f"{col} is numeric, so a histogram shows how values are spread.",
            params={"x": col},
        )
        box = ChartSpec(
            chart_id=f"box_{col}",
            title=f"Box plot of {col}",
            chart_type="box",
            reason=f"A box plot for {col} highlights the middle range and possible outliers.",
            params={"y": col},
        )
        if not any(spec.chart_type == "histogram" for spec in priority):
            priority.append(hist)
        else:
            extras.append(hist)
        if not any(spec.chart_type == "box" for spec in priority):
            priority.append(box)
        else:
            extras.append(box)

    for cat in groups.categorical[:3]:
        nunique = int(df[cat].nunique(dropna=True))
        if 1 < nunique <= MAX_PIE_CATEGORIES:
            pie = ChartSpec(
                chart_id=f"pie_{cat}",
                title=f"Share of {cat}",
                chart_type="pie",
                reason=f"{cat} has a small number of categories, so a pie chart can show shares.",
                params={"names": cat},
            )
            if not any(spec.chart_type == "pie" for spec in priority):
                priority.append(pie)
            else:
                extras.append(pie)
        if 1 < nunique <= MAX_BAR_CATEGORIES:
            bar = ChartSpec(
                chart_id=f"bar_{cat}",
                title=f"Count by {cat}",
                chart_type="bar",
                reason=f"A bar chart compares how often each {cat} value appears.",
                params={"x": cat},
            )
            if not any(spec.chart_type == "bar" for spec in priority):
                priority.append(bar)
            else:
                extras.append(bar)
            if groups.numeric:
                num = groups.numeric[0]
                extras.append(
                    ChartSpec(
                        chart_id=f"bar_{cat}_{num}",
                        title=f"Average {num} by {cat}",
                        chart_type="bar_mean",
                        reason=f"This compares typical {num} values across {cat} groups.",
                        params={"x": cat, "y": num},
                    )
                )

    unique: list[ChartSpec] = []
    seen = set()
    for spec in priority + extras:
        if spec.chart_id in seen:
            continue
        seen.add(spec.chart_id)
        unique.append(spec)
    return unique[:12]


def _prepared_frame(df: pd.DataFrame, spec: ChartSpec) -> pd.DataFrame:
    working = df.copy()
    params = spec.params
    if spec.chart_type in {"histogram", "box"}:
        col = params.get("x") or params.get("y")
        working[col] = as_numeric(working[col])
        working = working.dropna(subset=[col])
    elif spec.chart_type == "scatter":
        working[params["x"]] = as_numeric(working[params["x"]])
        working[params["y"]] = as_numeric(working[params["y"]])
        working = working.dropna(subset=[params["x"], params["y"]])
    elif spec.chart_type == "pie":
        working = working.dropna(subset=[params["names"]])
        working[params["names"]] = working[params["names"]].astype(str)
    elif spec.chart_type == "bar":
        working = working.dropna(subset=[params["x"]])
        working[params["x"]] = working[params["x"]].astype(str)
    elif spec.chart_type == "bar_mean":
        working[params["y"]] = as_numeric(working[params["y"]])
        working = working.dropna(subset=[params["x"], params["y"]])
        working[params["x"]] = working[params["x"]].astype(str)
    elif spec.chart_type == "line":
        working[params["x"]] = as_datetime(working[params["x"]])
        working[params["y"]] = as_numeric(working[params["y"]])
        working = working.dropna(subset=[params["x"], params["y"]])
    return working


def build_plotly_figure(df: pd.DataFrame, spec: ChartSpec):
    data = _prepared_frame(df, spec)
    if data.empty:
        return None
    chart_type = spec.chart_type
    if chart_type == "histogram":
        fig = px.histogram(data, x=spec.params["x"], title=spec.title, nbins=20)
    elif chart_type == "box":
        fig = px.box(data, y=spec.params["y"], title=spec.title, points="outliers")
    elif chart_type == "scatter":
        fig = px.scatter(data, x=spec.params["x"], y=spec.params["y"], title=spec.title, opacity=0.75)
    elif chart_type == "pie":
        counts = data[spec.params["names"]].value_counts().reset_index()
        counts.columns = [spec.params["names"], "count"]
        fig = px.pie(counts, names=spec.params["names"], values="count", title=spec.title)
    elif chart_type == "bar":
        counts = data[spec.params["x"]].value_counts().reset_index()
        counts.columns = [spec.params["x"], "count"]
        fig = px.bar(counts, x=spec.params["x"], y="count", title=spec.title)
    elif chart_type == "bar_mean":
        grouped = data.groupby(spec.params["x"], dropna=True)[spec.params["y"]].mean().reset_index()
        fig = px.bar(grouped, x=spec.params["x"], y=spec.params["y"], title=spec.title)
    elif chart_type == "line":
        grouped = data.groupby(spec.params["x"], dropna=True)[spec.params["y"]].mean().reset_index().sort_values(spec.params["x"])
        fig = px.line(grouped, x=spec.params["x"], y=spec.params["y"], title=spec.title, markers=True)
    else:
        return None
    fig.update_layout(template="plotly_white", margin=dict(l=40, r=20, t=60, b=40), height=420)
    return fig


def save_matplotlib_chart(df: pd.DataFrame, spec: ChartSpec, path: str) -> bool:
    """Save a simple PNG for the PDF report. Returns False if there is nothing to plot."""
    data = _prepared_frame(df, spec)
    if data.empty:
        return False
    plt.figure(figsize=(8, 4.5))
    chart_type = spec.chart_type
    try:
        if chart_type == "histogram":
            plt.hist(data[spec.params["x"]].dropna(), bins=20, color="#2F6FED", edgecolor="white")
            plt.xlabel(spec.params["x"])
            plt.ylabel("Count")
        elif chart_type == "box":
            plt.boxplot(data[spec.params["y"]].dropna(), orientation="vertical")
            plt.xticks([1], [spec.params["y"]])
        elif chart_type == "scatter":
            plt.scatter(data[spec.params["x"]], data[spec.params["y"]], alpha=0.7, color="#2F6FED")
            plt.xlabel(spec.params["x"])
            plt.ylabel(spec.params["y"])
        elif chart_type == "pie":
            counts = data[spec.params["names"]].value_counts()
            plt.pie(counts.values, labels=counts.index, autopct="%1.1f%%")
        elif chart_type == "bar":
            counts = data[spec.params["x"]].value_counts()
            plt.bar(counts.index.astype(str), counts.values, color="#2F6FED")
            plt.xticks(rotation=30, ha="right")
            plt.ylabel("Count")
        elif chart_type == "bar_mean":
            grouped = data.groupby(spec.params["x"], dropna=True)[spec.params["y"]].mean()
            plt.bar(grouped.index.astype(str), grouped.values, color="#2F6FED")
            plt.xticks(rotation=30, ha="right")
            plt.ylabel(spec.params["y"])
        elif chart_type == "line":
            grouped = data.groupby(spec.params["x"], dropna=True)[spec.params["y"]].mean().sort_index()
            plt.plot(grouped.index, grouped.values, marker="o", color="#2F6FED")
            plt.xlabel(spec.params["x"])
            plt.ylabel(spec.params["y"])
            plt.xticks(rotation=30, ha="right")
        else:
            plt.close()
            return False
        plt.title(spec.title)
        plt.tight_layout()
        plt.savefig(path, dpi=140)
        plt.close()
        return True
    except Exception:
        plt.close()
        return False

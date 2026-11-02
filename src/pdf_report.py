"""Build a PDF report from verified analysis results."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory

import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from src.charts import ChartSpec, save_matplotlib_chart
from src.config import PROJECT_ROOT
from src.data_quality import QualityReport

REPORTS_DIR = PROJECT_ROOT / "reports"


def _styles():
    styles = getSampleStyleSheet()
    styles.add(
        ParagraphStyle(
            name="CoverTitle",
            parent=styles["Title"],
            fontSize=20,
            spaceAfter=12,
            textColor=colors.HexColor("#1F3A5F"),
        )
    )
    styles.add(
        ParagraphStyle(
            name="SectionHead",
            parent=styles["Heading2"],
            textColor=colors.HexColor("#1F3A5F"),
            spaceBefore=14,
            spaceAfter=8,
        )
    )
    styles.add(
        ParagraphStyle(
            name="BodyText2",
            parent=styles["BodyText"],
            fontSize=10,
            leading=14,
        )
    )
    styles.add(
        ParagraphStyle(
            name="SmallNote",
            parent=styles["BodyText"],
            fontSize=8,
            textColor=colors.HexColor("#555555"),
        )
    )
    return styles


def _table(data: list[list[str]], col_widths=None) -> Table:
    table = Table(data, colWidths=col_widths, repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1F3A5F")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#F4F7FB"), colors.white]),
                ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#C5D0DE")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    return table


def _fmt(value) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return "—"
    if isinstance(value, float):
        if abs(value) >= 1000:
            return f"{value:,.2f}"
        return f"{value:.4g}"
    return str(value)


def _escape(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def build_pdf_report(
    *,
    filename: str,
    df: pd.DataFrame,
    overview: dict,
    quality: QualityReport,
    numeric_stats: pd.DataFrame,
    categorical_stats: pd.DataFrame,
    chart_specs: list[ChartSpec],
    ai_text: str | None,
    ai_message: str,
    output_path: Path | None = None,
) -> Path:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_name = Path(filename).stem.replace(" ", "_")[:40] or "dataset"
    output_path = output_path or (REPORTS_DIR / f"{safe_name}_insights_{stamp}.pdf")
    styles = _styles()

    with TemporaryDirectory() as tmp:
        story = []
        story.append(Paragraph("AI CSV Insights and Reporting System", styles["CoverTitle"]))
        story.append(Paragraph("College project report generated from uploaded CSV data.", styles["BodyText2"]))
        story.append(Paragraph(f"Source file: {_escape(filename)}", styles["BodyText2"]))
        story.append(Paragraph(f"Created: {datetime.now().strftime('%Y-%m-%d %H:%M')}", styles["BodyText2"]))
        story.append(
            Paragraph(
                "Statistics skip blank cells. The original uploaded dataset was not changed.",
                styles["SmallNote"],
            )
        )

        story.append(Paragraph("1. Dataset overview", styles["SectionHead"]))
        overview_rows = [
            ["Item", "Value"],
            ["Rows", str(overview["rows"])],
            ["Columns", str(overview["columns"])],
            ["Column names", _escape(", ".join(str(c) for c in overview["column_names"]))],
        ]
        story.append(_table(overview_rows, [140, 360]))
        story.append(Spacer(1, 8))
        dtype_rows = [["Column", "Data type"]] + [
            [_escape(str(name)), str(dtype)] for name, dtype in overview["dtypes"].items()
        ]
        story.append(_table(dtype_rows, [250, 250]))

        story.append(Paragraph("2. Data quality", styles["SectionHead"]))
        story.append(Paragraph(_escape(quality.summary), styles["BodyText2"]))
        quality_rows = [["Column", "Missing values", "Missing %", "Little variation"]]
        for col, missing in quality.missing_by_column.items():
            quality_rows.append(
                [
                    str(col),
                    str(missing),
                    _fmt(quality.missing_pct_by_column[col]),
                    "Yes" if col in quality.constant_columns else "No",
                ]
            )
        quality_rows.append(["Duplicate rows", str(quality.duplicate_rows), _fmt(quality.duplicate_pct), ""])
        story.append(Spacer(1, 6))
        story.append(_table(quality_rows, [160, 110, 110, 120]))

        story.append(Paragraph("3. Statistical summary", styles["SectionHead"]))
        if numeric_stats.empty:
            story.append(Paragraph("No numeric columns were available for statistical measures.", styles["BodyText2"]))
        else:
            story.append(Paragraph("Numeric columns (blank cells ignored):", styles["BodyText2"]))
            header = ["Column", "Count", "Sum", "Mean", "Median", "Mode", "Std Dev", "Min", "Q1", "Q3", "Max"]
            num_rows = [header]
            for _, row in numeric_stats.iterrows():
                num_rows.append(
                    [
                        _fmt(row["column"]),
                        _fmt(row["count"]),
                        _fmt(row["sum"]),
                        _fmt(row["mean"]),
                        _fmt(row["median"]),
                        _fmt(row["mode"]),
                        _fmt(row["std_dev"]),
                        _fmt(row["min"]),
                        _fmt(row["q1"]),
                        _fmt(row["q3"]),
                        _fmt(row["max"]),
                    ]
                )
            story.append(_table(num_rows))
            story.append(Spacer(1, 8))

        if categorical_stats.empty:
            story.append(Paragraph("No categorical or date columns were found.", styles["BodyText2"]))
        else:
            story.append(Paragraph("Categorical and date columns:", styles["BodyText2"]))
            header = ["Column", "Count", "Missing", "Unique", "Mode / range", "Top values"]
            cat_rows = [header]
            for _, row in categorical_stats.iterrows():
                cat_rows.append(
                    [
                        _fmt(row["column"]),
                        _fmt(row["count"]),
                        _fmt(row["missing"]),
                        _fmt(row["unique_values"]),
                        _fmt(row["mode"]),
                        _fmt(row["top_values"]),
                    ]
                )
            story.append(_table(cat_rows, [80, 45, 50, 45, 110, 170]))

        story.append(Paragraph("4. Selected charts", styles["SectionHead"]))
        added_chart = False
        for spec in chart_specs[:4]:
            image_path = Path(tmp) / f"{spec.chart_id}.png"
            if save_matplotlib_chart(df, spec, str(image_path)):
                story.append(Paragraph(_escape(spec.title), styles["BodyText2"]))
                story.append(Paragraph(_escape(spec.reason), styles["SmallNote"]))
                story.append(Image(str(image_path), width=6.2 * inch, height=3.5 * inch))
                story.append(Spacer(1, 8))
                added_chart = True
        if not added_chart:
            story.append(
                Paragraph(
                    "Charts could not be added to this PDF (not enough usable values, or no suitable columns).",
                    styles["BodyText2"],
                )
            )

        story.append(Paragraph("5. AI insights", styles["SectionHead"]))
        if ai_text:
            for paragraph in ai_text.split("\n"):
                if paragraph.strip():
                    story.append(Paragraph(_escape(paragraph.strip()), styles["BodyText2"]))
                    story.append(Spacer(1, 4))
        else:
            story.append(Paragraph(_escape(ai_message), styles["BodyText2"]))
        story.append(
            Paragraph(
                "AI comments are based on a compact summary of statistics, not the full raw file. "
                "A pattern in the data is not proof that one thing caused another.",
                styles["SmallNote"],
            )
        )

        document = SimpleDocTemplate(
            str(output_path),
            pagesize=A4,
            leftMargin=0.6 * inch,
            rightMargin=0.6 * inch,
            topMargin=0.6 * inch,
            bottomMargin=0.6 * inch,
            title="AI CSV Insights Report",
            author="AI CSV Insights and Reporting System",
        )
        document.build(story)

    return output_path

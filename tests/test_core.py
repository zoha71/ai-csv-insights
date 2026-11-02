from pathlib import Path

import pandas as pd

from src.ai_insights import build_summary_payload, generate_insights
from src.charts import build_plotly_figure, suggest_charts
from src.column_types import classify_columns
from src.config import AISettings, PROJECT_ROOT
from src.csv_loader import dataset_overview, load_csv_bytes, load_csv_path
from src.data_quality import analyze_quality
from src.pdf_report import build_pdf_report
from src.statistics import compact_stats_for_ai, numeric_summary


SAMPLE = PROJECT_ROOT / "sample_data" / "sales_data.csv"


def test_sample_csv_loads():
    result = load_csv_path(SAMPLE)
    assert result.error is None
    assert result.dataframe is not None
    assert result.dataframe.shape[0] >= 20
    assert "revenue" in result.dataframe.columns


def test_rejects_non_csv_name():
    result = load_csv_bytes(b"a,b\n1,2\n", "notes.txt")
    assert result.dataframe is None
    assert "CSV" in result.error


def test_rejects_empty_file():
    result = load_csv_bytes(b"", "empty.csv")
    assert result.dataframe is None
    assert "empty" in result.error.lower()


def test_original_not_modified_by_quality_and_stats():
    df = load_csv_path(SAMPLE).dataframe
    before = df.copy()
    analyze_quality(df)
    numeric_summary(df)
    suggest_charts(df)
    pd.testing.assert_frame_equal(df, before)


def test_quality_finds_missing_and_duplicates():
    df = load_csv_path(SAMPLE).dataframe
    report = analyze_quality(df)
    assert report.total_missing_cells > 0
    assert report.duplicate_rows >= 1
    assert 0 < report.completeness_pct <= 100


def test_numeric_stats_have_required_columns():
    df = load_csv_path(SAMPLE).dataframe
    stats = numeric_summary(df)
    for column in ["count", "sum", "mean", "median", "mode", "std_dev", "min", "q1", "q3", "max"]:
        assert column in stats.columns
    revenue = stats.loc[stats["column"] == "revenue"].iloc[0]
    assert revenue["count"] > 0
    assert revenue["max"] >= revenue["min"]


def test_chart_suggestions_include_expected_types():
    df = load_csv_path(SAMPLE).dataframe
    specs = suggest_charts(df)
    types = {spec.chart_type for spec in specs}
    assert "histogram" in types
    assert "bar" in types or "bar_mean" in types
    assert "line" in types
    figure = build_plotly_figure(df, specs[0])
    assert figure is not None


def test_ai_without_key_does_not_invent_text():
    settings = AISettings(
        api_key="",
        base_url="https://api.openai.com/v1",
        model="gpt-4o-mini",
        chat_path="/chat/completions",
        timeout_seconds=10,
    )
    result = generate_insights({"row_count": 1}, settings)
    assert result.text is None
    assert result.status == "missing_key"
    assert result.used_api is False


def test_compact_payload_has_no_raw_rows():
    df = load_csv_path(SAMPLE).dataframe
    overview = dataset_overview(df)
    payload = build_summary_payload(
        filename="sales_data.csv",
        rows=overview["rows"],
        columns=overview["columns"],
        dtypes=overview["dtypes"],
        quality=analyze_quality(df),
        stats_payload=compact_stats_for_ai(df, classify_columns(df)),
    )
    serialized = str(payload)
    assert "Alice" not in serialized
    assert "records" not in payload


def test_pdf_report_created(tmp_path):
    df = load_csv_path(SAMPLE).dataframe
    overview = dataset_overview(df)
    output = tmp_path / "report.pdf"
    path = build_pdf_report(
        filename="sales_data.csv",
        df=df,
        overview=overview,
        quality=analyze_quality(df),
        numeric_stats=numeric_summary(df),
        categorical_stats=pd.DataFrame(),
        chart_specs=suggest_charts(df)[:2],
        ai_text=None,
        ai_message="AI insights were not generated in this test.",
        output_path=output,
    )
    assert path.exists()
    assert path.stat().st_size > 1000

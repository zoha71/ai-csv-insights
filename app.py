"""AI CSV Insights and Reporting System — Streamlit dashboard."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

from src.ai_insights import build_summary_payload, generate_insights
from src.charts import build_plotly_figure, suggest_charts
from src.column_types import classify_columns
from src.config import MAX_UPLOAD_BYTES, PROJECT_ROOT, get_ai_settings
from src.csv_loader import dataset_overview, load_csv_bytes, load_csv_path
from src.data_quality import analyze_quality, quality_table
from src.pdf_report import build_pdf_report
from src.statistics import categorical_summary, compact_stats_for_ai, numeric_summary

SAMPLE_CSV = PROJECT_ROOT / "sample_data" / "sales_data.csv"

st.set_page_config(
    page_title="AI CSV Insights",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
      .block-container { max-width: 1200px; padding-top: 1.2rem; }
      h1, h2, h3 { color: #1F3A5F; }
      .hint { color: #4a5568; font-size: 0.95rem; }
    </style>
    """,
    unsafe_allow_html=True,
)


def _init_state() -> None:
    defaults = {
        "original_df": None,
        "filename": None,
        "load_error": None,
        "ai_result": None,
        "pdf_path": None,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def _reset_analysis() -> None:
    st.session_state.ai_result = None
    st.session_state.pdf_path = None


def _store_dataframe(df: pd.DataFrame, filename: str) -> None:
    st.session_state.original_df = df.copy()
    st.session_state.filename = filename
    st.session_state.load_error = None
    _reset_analysis()


def _load_uploaded(uploaded) -> None:
    result = load_csv_bytes(uploaded.getvalue(), uploaded.name)
    if result.error:
        st.session_state.original_df = None
        st.session_state.filename = uploaded.name
        st.session_state.load_error = result.error
        _reset_analysis()
        return
    _store_dataframe(result.dataframe, result.filename)


_init_state()

with st.sidebar:
    st.title("AI CSV Insights")
    st.caption("Upload a CSV, explore it, and download a report.")
    page = st.radio(
        "Go to",
        [
            "Home",
            "Upload & Overview",
            "Data Quality",
            "Statistics",
            "Charts",
            "AI Insights",
            "Download Report",
        ],
        index=0,
    )
    st.divider()
    st.markdown("**Upload a CSV file**")
    uploaded = st.file_uploader(
        "Choose a .csv file",
        type=["csv"],
        help=f"Maximum size is {MAX_UPLOAD_BYTES // (1024 * 1024)} MB. The original file is never edited.",
    )
    if uploaded is not None:
        file_id = f"{uploaded.name}-{uploaded.size}"
        if st.session_state.get("last_file_id") != file_id:
            _load_uploaded(uploaded)
            st.session_state.last_file_id = file_id

    if SAMPLE_CSV.exists() and st.button("Load sample sales data"):
        result = load_csv_path(SAMPLE_CSV)
        if result.error:
            st.session_state.load_error = result.error
        else:
            _store_dataframe(result.dataframe, result.filename)
            st.session_state.last_file_id = f"sample-{result.filename}"
            st.success("Sample dataset loaded.")

    st.divider()
    settings = get_ai_settings()
    if settings.is_configured:
        st.caption(f"AI model: `{settings.model}`")
    else:
        st.caption("AI key not set. Charts and reports still work.")

df: pd.DataFrame | None = st.session_state.original_df

if st.session_state.load_error:
    st.error(st.session_state.load_error)

if page == "Home":
    st.title("AI CSV Insights and Reporting System")
  
    st.markdown(
        """
        **How to use it**
        1. Open **Upload & Overview** or use the file box on the left.
        2. Check **Data Quality** for missing values and duplicate rows.
        3. Open **Statistics** for averages, totals, and similar numbers.
        4. Open **Charts** to see suggested graphs.
        5. Open **AI Insights** if you have added an API key.
        6. Download a PDF from **Download Report**.

    
        """
    )
    col_a, col_b, col_c = st.columns(3)
    col_a.metric("Dataset loaded", "Yes" if df is not None else "No")
    col_b.metric("Rows", f"{df.shape[0]:,}" if df is not None else "—")
    col_c.metric("Columns", f"{df.shape[1]}" if df is not None else "—")
    if df is None:
        st.info("No file yet. Upload a CSV on the left, or click **Load sample sales data**.")

elif df is None:
    st.title(page)
    st.info("Please upload a CSV file first, or load the sample sales data from the left menu.")

else:
    overview = dataset_overview(df)
    groups = classify_columns(df)
    quality = analyze_quality(df)
    numeric_stats = numeric_summary(df, groups)
    categorical_stats = categorical_summary(df, groups)
    chart_specs = suggest_charts(df, groups)

    if page == "Upload & Overview":
        st.title("Upload and dataset overview")
        st.write(
            f"File name: **{st.session_state.filename}**. "
            "This preview is the original uploaded data."
        )
        m1, m2, m3 = st.columns(3)
        m1.metric("Rows", f"{overview['rows']:,}")
        m2.metric("Columns", f"{overview['columns']}")
        m3.metric("Numeric columns", str(len(groups.numeric)))
        st.subheader("Column names and types")
        type_table = pd.DataFrame(
            {"column": list(overview["dtypes"].keys()), "data_type": list(overview["dtypes"].values())}
        )
        st.dataframe(type_table, hide_index=True, use_container_width=True)
        st.subheader("Preview (first 20 rows)")
        st.dataframe(df.head(20), use_container_width=True)
        with st.expander("What these types mean"):
            st.write(
                "A **numeric** column contains numbers (sales, counts, prices). "
                "A **categorical** column contains labels (region, product). "
                "A **date** column contains dates. The app guesses these from the values."
            )

    elif page == "Data Quality":
        st.title("Data quality")
        st.write(quality.summary)
        q1, q2, q3 = st.columns(3)
        q1.metric("Completeness", f"{quality.completeness_pct:.1f}%")
        q2.metric("Missing cells", f"{quality.total_missing_cells:,}")
        q3.metric("Duplicate rows", f"{quality.duplicate_rows:,}")
        st.subheader("Missing values by column")
        st.dataframe(quality_table(quality), hide_index=True, use_container_width=True)
        if quality.duplicate_rows:
            st.subheader("Example duplicate rows")
            dup_mask = df.duplicated(keep=False)
            st.dataframe(df.loc[dup_mask].head(20), use_container_width=True)
        st.info("No missing values were filled in, and no duplicate rows were removed. Your original table is unchanged.")

    elif page == "Statistics":
        st.title("Statistical analysis")
        st.write("Blank cells are ignored for these calculations. The original table is not edited.")
        st.subheader("Numeric columns")
        if numeric_stats.empty:
            st.warning("This file has no numeric columns that can be summarized.")
        else:
            display = numeric_stats.copy()
            number_cols = ["sum", "mean", "median", "std_dev", "min", "q1", "q3", "max"]
            for col in number_cols:
                display[col] = display[col].map(lambda v: "—" if pd.isna(v) else f"{v:,.4g}")
            st.dataframe(display, hide_index=True, use_container_width=True)
        st.subheader("Categorical and date columns")
        if categorical_stats.empty:
            st.warning("This file has no categorical or date columns.")
        else:
            st.dataframe(categorical_stats, hide_index=True, use_container_width=True)
        with st.expander("What these words mean"):
            st.markdown(
                """
                - **Count**: how many values were available
                - **Sum**: all numbers added together
                - **Mean**: the average
                - **Median**: the middle value
                - **Mode**: the most common value
                - **Standard deviation**: how spread out the numbers are
                - **Min / Max**: smallest and largest values
                - **Q1 / Q3**: the 25th and 75th percentile (quartiles)
                """
            )

    elif page == "Charts":
        st.title("Charts")
        st.write("These chart ideas are based on column types. A pattern in a chart is not proof of cause and effect.")
        if not chart_specs:
            st.warning("No suitable charts could be suggested for this file.")
        else:
            labels = [f"{spec.title} ({spec.chart_type})" for spec in chart_specs]
            selected = st.multiselect("Charts to show", labels, default=labels[:4])
            for spec, label in zip(chart_specs, labels):
                if label not in selected:
                    continue
                st.subheader(spec.title)
                st.caption(spec.reason)
                figure = build_plotly_figure(df, spec)
                if figure is None:
                    st.warning("This chart needs more usable values after ignoring blanks.")
                else:
                    st.plotly_chart(figure, use_container_width=True)

    elif page == "AI Insights":
        st.title("AI insights")
        st.write(
            "The app sends a **compact summary** of counts and statistics to an external AI model. "
            "It does not send the full CSV or individual raw records by default."
        )
        settings = get_ai_settings()
        st.caption(f"Provider base URL: `{settings.base_url}` · Model: `{settings.model}`")
        if st.button("Generate AI insights", type="primary"):
            payload = build_summary_payload(
                filename=st.session_state.filename,
                rows=overview["rows"],
                columns=overview["columns"],
                dtypes=overview["dtypes"],
                quality=quality,
                stats_payload=compact_stats_for_ai(df, groups),
            )
            with st.spinner("Asking the AI model for comments on the summary..."):
                st.session_state.ai_result = generate_insights(payload, settings)

        result = st.session_state.ai_result
        if result is None:
            st.info("Click the button above when you are ready. If no API key is set, you will see a helpful message instead of fake insights.")
        elif result.status == "ok" and result.text:
            st.success(result.message)
            st.markdown(result.text)
            st.caption("These comments are not proof of cause and effect. Treat them as careful suggestions.")
        else:
            st.warning(result.message)
            st.caption("No AI insights were invented. Statistics, charts, and PDF sections still work.")

    elif page == "Download Report":
        st.title("Download PDF report")
        st.write(
            "The report includes overview, data quality, statistics, up to four charts, and AI insights "
            "if they were generated in this session."
        )
        ai_result = st.session_state.ai_result
        ai_text = ai_result.text if ai_result and ai_result.status == "ok" else None
        if ai_result is None:
            ai_message = "AI insights were not generated in this session."
        elif ai_result.status == "ok":
            ai_message = ai_result.message
        else:
            ai_message = ai_result.message

        if st.button("Create PDF report", type="primary"):
            with st.spinner("Creating the PDF..."):
                try:
                    pdf_path = build_pdf_report(
                        filename=st.session_state.filename,
                        df=df,
                        overview=overview,
                        quality=quality,
                        numeric_stats=numeric_stats,
                        categorical_stats=categorical_stats,
                        chart_specs=chart_specs,
                        ai_text=ai_text,
                        ai_message=ai_message,
                    )
                    st.session_state.pdf_path = str(pdf_path)
                except Exception as exc:  # noqa: BLE001
                    st.session_state.pdf_path = None
                    st.error(f"The PDF could not be created. Details: {exc}")

        pdf_path = st.session_state.pdf_path
        if pdf_path and Path(pdf_path).exists():
            pdf_bytes = Path(pdf_path).read_bytes()
            st.success(f"Report saved on this computer at: {pdf_path}")
            st.download_button(
                "Download PDF",
                data=pdf_bytes,
                file_name=Path(pdf_path).name,
                mime="application/pdf",
            )
        elif ai_text is None:
            st.caption("Tip: generate AI insights first if you want them included in the PDF. The report can still be created without them.")

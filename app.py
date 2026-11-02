
"""AI CSV Insights and Reporting System."""

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
    page_title="AI CSV Insights | Analytics Studio",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# PREMIUM DARK DASHBOARD DESIGN
st.markdown(
    """
    <style>
    :root {
        --bg: #0B1020;
        --panel: #121A2D;
        --border: #293754;
        --text: #F1F5F9;
    }

    /* Main background */
    .stApp {
        background:
            radial-gradient(ellipse at 12% 0%, rgba(91,72,190,.18), transparent 34%),
            radial-gradient(ellipse at 88% 8%, rgba(37,99,235,.13), transparent 30%),
            var(--bg);
        color: var(--text);
    }

    /* REMOVE STREAMLIT TOP HEADER AND DEPLOY MENU */
    header[data-testid="stHeader"] {
        display: none !important;
        height: 0 !important;
        visibility: hidden !important;
    }

    [data-testid="stToolbar"] {
        display: none !important;
    }

    [data-testid="stDecoration"] {
        display: none !important;
    }

    #MainMenu {
        visibility: hidden;
    }

    footer {
        visibility: hidden;
    }

    /* REMOVE EXTRA SPACE ABOVE SIDEBAR */
    section[data-testid="stSidebar"] {
        background: #10182A;
        border-right: 1px solid var(--border);
    }

    section[data-testid="stSidebar"] > div:first-child {
        padding-top: 0 !important;
    }

    section[data-testid="stSidebar"] [data-testid="stSidebarContent"] {
        padding-top: 0 !important;
    }

    /* MAIN CONTENT SPACING */
    .block-container {
        max-width: 1450px;
        padding-top: 1rem !important;
        padding-bottom: 3rem;
    }

    section[data-testid="stSidebar"] * {
        color: #DCE5F4;
    }

    h1, h2, h3, h4 {
        color: var(--text) !important;
        letter-spacing: -.025em;
        font-weight: 700 !important;
    }

    p, label, .stMarkdown, [data-testid="stCaptionContainer"] {
        color: #C0CCDE;
    }

    /* SIDEBAR */
    section[data-testid="stSidebar"] {
        background: #10182A;
        border-right: 1px solid #293754;
    }

    /* METRIC CARDS */
    [data-testid="stMetric"] {
        background: linear-gradient(145deg, #192641, #121B2F);
        border: 1px solid #30415F;
        border-radius: 16px;
        padding: 18px 20px;
        box-shadow: 0 8px 24px rgba(0,0,0,.14);
    }

    [data-testid="stMetricLabel"] {
        color: #A9B8CE !important;
        font-size: .88rem;
    }

    [data-testid="stMetricValue"] {
        color: #B7A9FF !important;
        font-weight: 750;
    }

    /* BUTTONS */
    .stButton > button,
    .stDownloadButton > button {
        background: linear-gradient(100deg, #765CF6, #347FEA);
        color: #FFFFFF !important;
        border: 1px solid rgba(255,255,255,.10);
        border-radius: 10px;
        min-height: 2.65rem;
        padding: .55rem 1.1rem;
        font-weight: 650;
        transition: all .2s ease;
    }

    .stButton > button:hover,
    .stDownloadButton > button:hover {
        border-color: #B8ACFF;
        box-shadow: 0 0 18px rgba(118,92,246,.28);
        transform: translateY(-1px);
    }

    /* CSV UPLOADER */
    [data-testid="stFileUploader"] {
        background: #151F34;
        border: 1px dashed #6476A0;
        border-radius: 14px;
        padding: 12px;
    }

    [data-testid="stFileUploader"] section {
        background: #151F34 !important;
        border-color: #6476A0 !important;
    }

    [data-testid="stFileUploader"] button {
        background: #263653 !important;
        color: white !important;
    }

    /* TABLES */
    [data-testid="stDataFrame"],
    [data-testid="stTable"] {
        border: 1px solid var(--border);
        border-radius: 12px;
        overflow: hidden;
    }

    /* ALERTS AND EXPANDERS */
    [data-testid="stAlert"] {
        border-radius: 12px;
        border: 1px solid var(--border);
    }

    [data-testid="stExpander"] {
        background: rgba(20,31,52,.72);
        border: 1px solid var(--border);
        border-radius: 12px;
    }

    div[role="radiogroup"] label {
        background: rgba(28,42,67,.55);
        border-radius: 9px;
        padding: 7px 10px;
        margin-bottom: 4px;
    }

    hr {
        border-color: var(--border);
    }

    /* HOME HERO */
    .hero {
        padding: 30px 32px;
        border: 1px solid #34466B;
        border-radius: 22px;
        background:
            linear-gradient(115deg, rgba(83,65,172,.30), rgba(28,89,158,.18)),
            #141E33;
        margin-bottom: 24px;
        box-shadow: 0 16px 40px rgba(0,0,0,.18);
    }

    .hero-eyebrow {
        color: #B9ACFF;
        text-transform: uppercase;
        letter-spacing: .13em;
        font-size: .76rem;
        font-weight: 750;
        margin-bottom: 10px;
    }

    .hero-title {
        color: #FFFFFF;
        font-size: clamp(1.8rem,4vw,2.7rem);
        font-weight: 800;
        letter-spacing: -.04em;
        line-height: 1.12;
        margin-bottom: 12px;
    }

    .hero-copy {
        color: #C4D0E2;
        font-size: 1rem;
        max-width: 760px;
        line-height: 1.65;
    }

    .section-kicker {
        color: #A99AFF;
        font-size: .76rem;
        text-transform: uppercase;
        letter-spacing: .12em;
        font-weight: 750;
        margin-bottom: 5px;
    }

    .feature-card {
        height: 100%;
        min-height: 142px;
        padding: 18px;
        border-radius: 15px;
        background: linear-gradient(145deg, #192641, #121B2F);
        border: 1px solid #30415F;
    }

    .feature-title {
        color: #F1F5F9;
        font-weight: 700;
        font-size: 1rem;
        margin-bottom: 7px;
    }

    .feature-copy {
        color: #AAB9CE;
        font-size: .88rem;
        line-height: 1.5;
    }

    .status-dot {
        display: inline-block;
        width: 8px;
        height: 8px;
        border-radius: 50%;
        background: #34D399;
        margin-right: 7px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def _init_state():
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


def _reset_analysis():
    st.session_state.ai_result = None
    st.session_state.pdf_path = None


def _store_dataframe(df, filename):
    st.session_state.original_df = df.copy()
    st.session_state.filename = filename
    st.session_state.load_error = None
    _reset_analysis()


def _load_uploaded(uploaded):
    result = load_csv_bytes(uploaded.getvalue(), uploaded.name)

    if result.error:
        st.session_state.original_df = None
        st.session_state.filename = uploaded.name
        st.session_state.load_error = result.error
        _reset_analysis()
        return

    _store_dataframe(result.dataframe, result.filename)


_init_state()

# SIDEBAR
with st.sidebar:
    st.markdown("## 📊 DataPulse AI")
    st.caption("Your intelligent analytics workspace")
    st.divider()

    page = st.radio(
        "WORKSPACE",
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
    st.markdown("### 📁 Your dataset")

    uploaded = st.file_uploader(
        "Upload a CSV file",
        type=["csv"],
        help=f"Maximum size is {MAX_UPLOAD_BYTES // (1024 * 1024)} MB.",
    )

    if uploaded is not None:
        file_id = f"{uploaded.name}-{uploaded.size}"

        if st.session_state.get("last_file_id") != file_id:
            _load_uploaded(uploaded)
            st.session_state.last_file_id = file_id

    if SAMPLE_CSV.exists():
        if st.button("✨ Load sample dataset", use_container_width=True):
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
        st.markdown(
            f'<span class="status-dot"></span>AI configured · `{settings.model}`',
            unsafe_allow_html=True,
        )
    else:
        st.caption("AI key not configured. Charts and reports still work.")

    st.caption("AI CSV Insights · Analytics Studio")


df = st.session_state.original_df

if st.session_state.load_error:
    st.error(st.session_state.load_error)


# HOME PAGE
if page == "Home":

    st.markdown(
        """
        <div class="hero">
            <div class="hero-eyebrow">✦ AI-powered data workspace</div>
            <div class="hero-title">
                Turn raw CSV data into<br>meaningful insights.
            </div>
            <div class="hero-copy">
                Explore your data, uncover quality issues, visualize patterns,
                and generate AI-assisted findings — all in one place.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="section-kicker">Workspace overview</div>',
        unsafe_allow_html=True,
    )

    st.subheader("Your analytics at a glance")

    col_a, col_b, col_c = st.columns(3)

    col_a.metric(
        "Dataset status",
        "Loaded" if df is not None else "Awaiting file",
    )

    col_b.metric(
        "Total rows",
        f"{df.shape[0]:,}" if df is not None else "—",
    )

    col_c.metric(
        "Total columns",
        f"{df.shape[1]:,}" if df is not None else "—",
    )

    if df is not None:
        st.success(f"Ready to explore **{st.session_state.filename}**.")
    else:
        st.info(
            "Upload a CSV file using the sidebar, or load the sample dataset to get started."
        )

    st.markdown(
        '<div class="section-kicker">Explore the platform</div>',
        unsafe_allow_html=True,
    )

    st.subheader("Everything you need to understand your data")

    cards = [
        ("📂", "Upload & overview", "Preview your dataset and understand its columns and structure."),
        ("🛡️", "Data quality", "Find missing values, duplicate rows, and completeness issues."),
        ("📈", "Statistics & charts", "Explore numeric summaries and interactive visualizations."),
        ("✨", "AI insights", "Get AI-assisted explanations based on a compact data summary."),
        ("📄", "PDF reporting", "Create a shareable report with your analysis and charts."),
    ]

    card_cols = st.columns(3)

    for index, (emoji, title, description) in enumerate(cards):
        with card_cols[index % 3]:
            st.markdown(
                f"""
                <div class="feature-card">
                    <div style="font-size:1.5rem;margin-bottom:10px">{emoji}</div>
                    <div class="feature-title">{title}</div>
                    <div class="feature-copy">{description}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )


# PAGES THAT REQUIRE A DATASET
elif df is None:

    st.markdown(
        '<div class="section-kicker">Your workspace</div>',
        unsafe_allow_html=True,
    )

    st.title(page)
    st.info(
        "Upload a CSV file from the sidebar, or load the sample dataset to continue."
    )


else:

    overview = dataset_overview(df)
    groups = classify_columns(df)
    quality = analyze_quality(df)
    numeric_stats = numeric_summary(df, groups)
    categorical_stats = categorical_summary(df, groups)
    chart_specs = suggest_charts(df, groups)

    # UPLOAD & OVERVIEW
    if page == "Upload & Overview":

        st.markdown(
            '<div class="section-kicker">Dataset workspace</div>',
            unsafe_allow_html=True,
        )

        st.title("Upload & overview")
        st.caption(f"Currently exploring: {st.session_state.filename}")

        m1, m2, m3 = st.columns(3)

        m1.metric("Total rows", f"{overview['rows']:,}")
        m2.metric("Total columns", f"{overview['columns']:,}")
        m3.metric("Numeric columns", f"{len(groups.numeric):,}")

        st.subheader("Column names and types")

        type_table = pd.DataFrame(
            {
                "Column": list(overview["dtypes"].keys()),
                "Data type": list(overview["dtypes"].values()),
            }
        )

        st.dataframe(type_table, hide_index=True, use_container_width=True)

        st.subheader("Data preview")
        st.caption("Showing the first 20 rows.")

        st.dataframe(df.head(20), use_container_width=True)

        with st.expander("What do these column types mean?"):
            st.write(
                "Numeric columns contain numbers. Categorical columns contain labels. "
                "Date columns contain dates. The app identifies these from the values."
            )

    # DATA QUALITY
    elif page == "Data Quality":

        st.markdown(
            '<div class="section-kicker">Data health monitor</div>',
            unsafe_allow_html=True,
        )

        st.title("Data quality")
        st.write(quality.summary)

        q1, q2, q3 = st.columns(3)

        q1.metric("Completeness", f"{quality.completeness_pct:.1f}%")
        q2.metric("Missing cells", f"{quality.total_missing_cells:,}")
        q3.metric("Duplicate rows", f"{quality.duplicate_rows:,}")

        st.subheader("Missing values by column")

        st.dataframe(
            quality_table(quality),
            hide_index=True,
            use_container_width=True,
        )

        if quality.duplicate_rows:
            st.subheader("Example duplicate rows")

            dup_mask = df.duplicated(keep=False)

            st.dataframe(
                df.loc[dup_mask].head(20),
                use_container_width=True,
            )

        st.info(
            "No missing values were filled in, and no duplicate rows were removed. "
            "Your original table is unchanged."
        )

    # STATISTICS
    elif page == "Statistics":

        st.markdown(
            '<div class="section-kicker">Explore the numbers</div>',
            unsafe_allow_html=True,
        )

        st.title("Statistical analysis")

        st.caption(
            "Blank cells are ignored for these calculations. The original table is not edited."
        )

        st.subheader("Numeric columns")

        if numeric_stats.empty:
            st.warning("This file has no numeric columns that can be summarized.")
        else:
            display = numeric_stats.copy()

            number_cols = [
                "sum", "mean", "median", "std_dev",
                "min", "q1", "q3", "max",
            ]

            for col in number_cols:
                if col in display.columns:
                    display[col] = display[col].map(
                        lambda value: "—" if pd.isna(value) else f"{value:,.4g}"
                    )

            st.dataframe(
                display,
                hide_index=True,
                use_container_width=True,
            )

        st.subheader("Categorical and date columns")

        if categorical_stats.empty:
            st.warning("This file has no categorical or date columns.")
        else:
            st.dataframe(
                categorical_stats,
                hide_index=True,
                use_container_width=True,
            )

        with st.expander("Understand the statistical terms"):
            st.markdown(
                """
                - **Count:** Number of available values
                - **Sum:** All numbers added together
                - **Mean:** Average
                - **Median:** Middle value
                - **Mode:** Most common value
                - **Standard deviation:** How spread out the numbers are
                - **Min / Max:** Smallest and largest values
                - **Q1 / Q3:** 25th and 75th percentiles
                """
            )

    # CHARTS
    elif page == "Charts":

        st.markdown(
            '<div class="section-kicker">Visual analytics</div>',
            unsafe_allow_html=True,
        )

        st.title("Interactive charts")

        st.caption(
            "Chart suggestions are based on column types. "
            "Patterns do not prove cause and effect."
        )

        if not chart_specs:
            st.warning("No suitable charts could be suggested for this file.")
        else:
            labels = [
                f"{spec.title} ({spec.chart_type})"
                for spec in chart_specs
            ]

            selected = st.multiselect(
                "Choose charts to display",
                labels,
                default=labels[:4],
            )

            for spec, label in zip(chart_specs, labels):

                if label not in selected:
                    continue

                st.subheader(spec.title)
                st.caption(spec.reason)

                figure = build_plotly_figure(df, spec)

                if figure is None:
                    st.warning(
                        "This chart needs more usable values after ignoring blanks."
                    )
                else:
                    figure.update_layout(
                        template="plotly_dark",
                        paper_bgcolor="rgba(0,0,0,0)",
                        plot_bgcolor="rgba(0,0,0,0)",
                        font=dict(color="#DCE5F4"),
                        margin=dict(l=20, r=20, t=45, b=20),
                    )

                    st.plotly_chart(
                        figure,
                        use_container_width=True,
                    )

    # AI INSIGHTS
    elif page == "AI Insights":

        st.markdown(
            '<div class="section-kicker">Intelligence layer</div>',
            unsafe_allow_html=True,
        )

        st.title("AI-powered insights")

        st.write(
            "The app sends a compact summary of counts and statistics to an external AI model. "
            "It does not send the full CSV or individual raw records by default."
        )

        settings = get_ai_settings()

        st.caption(
            f"Provider base URL: `{settings.base_url}` · Model: `{settings.model}`"
        )

        if st.button("✨ Generate AI insights", type="primary"):

            payload = build_summary_payload(
                filename=st.session_state.filename,
                rows=overview["rows"],
                columns=overview["columns"],
                dtypes=overview["dtypes"],
                quality=quality,
                stats_payload=compact_stats_for_ai(df, groups),
            )

            with st.spinner("Analyzing your dataset summary..."):
                st.session_state.ai_result = generate_insights(
                    payload,
                    settings,
                )

        result = st.session_state.ai_result

        if result is None:
            st.info(
                "Generate insights when you're ready. If no API key is configured, "
                "the app will show a helpful message."
            )

        elif result.status == "ok" and result.text:
            st.success(result.message)
            st.markdown(result.text)

            st.caption(
                "These comments are suggestions, not proof of cause and effect."
            )

        else:
            st.warning(result.message)

            st.caption(
                "Statistics, charts, and PDF sections still work without AI insights."
            )

    # PDF REPORT
    elif page == "Download Report":

        st.markdown(
            '<div class="section-kicker">Export center</div>',
            unsafe_allow_html=True,
        )

        st.title("PDF report")

        st.write(
            "Create a report containing the overview, data quality, statistics, "
            "up to four charts, and AI insights if generated."
        )

        ai_result = st.session_state.ai_result

        ai_text = (
            ai_result.text
            if ai_result and ai_result.status == "ok"
            else None
        )

        if ai_result is None:
            ai_message = "AI insights were not generated in this session."
        else:
            ai_message = ai_result.message

        if st.button("📄 Create PDF report", type="primary"):

            with st.spinner("Creating your PDF report..."):

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

                except Exception as exc:
                    st.session_state.pdf_path = None
                    st.error(f"The PDF could not be created. Details: {exc}")

        pdf_path = st.session_state.pdf_path

        if pdf_path and Path(pdf_path).exists():

            pdf_bytes = Path(pdf_path).read_bytes()

            st.success("Your PDF report is ready.")

            st.download_button(
                "⬇️ Download PDF report",
                data=pdf_bytes,
                file_name=Path(pdf_path).name,
                mime="application/pdf",
            )

        elif ai_text is None:
            st.caption(
                "You can create the report without AI insights. "
                "Generate insights first if you want them included."
            )

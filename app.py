"""
Log Analysis Dashboard  (Enhanced)
====================================
Features:
  - Upload .txt log files
  - Sidebar: filter by log level + keyword search
  - Highlighted log rows (red = ERROR, orange = WARNING, green = INFO)
  - KPI summary cards
  - Bar chart + Pie chart
  - Top errors table
  - Download filtered results as CSV or TXT
  - Error timeline (when timestamps are present)

Run with:  streamlit run app.py
"""

import re
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from collections import Counter
from datetime import datetime

# ════════════════════════════════════════════════
#  PAGE CONFIG
# ════════════════════════════════════════════════
st.set_page_config(
    page_title="Log Analysis Dashboard",
    page_icon="🔍",
    layout="wide",
)

# ════════════════════════════════════════════════
#  CUSTOM CSS  — clean light theme
# ════════════════════════════════════════════════
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600&family=Inter:wght@400;500;600;700&display=swap');

    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

    .stApp { background: #f7f8fc; color: #1a1d27; }

    [data-testid="stSidebar"] {
        background: #ffffff;
        border-right: 1px solid #e2e6f0;
    }

    .metric-card {
        background: #ffffff;
        border: 1px solid #e2e6f0;
        border-radius: 12px;
        padding: 20px 16px;
        text-align: center;
        box-shadow: 0 1px 4px rgba(0,0,0,0.06);
        transition: box-shadow .2s, transform .15s;
    }
    .metric-card:hover { box-shadow: 0 4px 16px rgba(0,0,0,0.10); transform: translateY(-2px); }
    .metric-label {
        font-size: 11px; font-weight: 600; letter-spacing: 2px;
        text-transform: uppercase; color: #7a849e; margin-bottom: 10px;
    }
    .metric-value {
        font-family: 'JetBrains Mono', monospace;
        font-size: 36px; font-weight: 700; line-height: 1;
    }
    .metric-value.total    { color: #4361ee; }
    .metric-value.filtered { color: #7b2ff7; }
    .metric-value.error    { color: #e03131; }
    .metric-value.warn     { color: #e67700; }
    .metric-value.info     { color: #2f9e44; }

    .section-title {
        font-size: 11px; font-weight: 700; letter-spacing: 3px;
        text-transform: uppercase; color: #4361ee;
        border-bottom: 2px solid #e2e6f0;
        padding-bottom: 8px; margin: 32px 0 16px;
    }

    .hero-title {
        font-size: 38px; font-weight: 700; color: #1a1d27;
        letter-spacing: -0.5px; line-height: 1.2;
    }
    .hero-sub { color: #7a849e; font-size: 14px; margin-top: 8px; line-height: 1.6; }

    .error-box {
        background: #fff5f5;
        border-left: 4px solid #e03131;
        border-radius: 0 10px 10px 0;
        padding: 14px 18px;
        font-family: 'JetBrains Mono', monospace;
        font-size: 13px; color: #c92a2a;
        margin-bottom: 8px; word-break: break-all; line-height: 1.5;
    }

    /* Light-background colour-coded log rows — very easy to read */
    .log-row {
        font-family: 'JetBrains Mono', monospace;
        font-size: 12.5px; padding: 7px 12px;
        border-radius: 6px; margin-bottom: 4px;
        line-height: 1.6; word-break: break-all;
    }
    .log-row.ERROR    { background:#fff0f0; color:#c92a2a; border-left:3px solid #e03131; }
    .log-row.WARNING  { background:#fff8ec; color:#b35900; border-left:3px solid #e67700; }
    .log-row.INFO     { background:#f0faf2; color:#236b33; border-left:3px solid #2f9e44; }
    .log-row.DEBUG    { background:#f0f4ff; color:#2d47c9; border-left:3px solid #4361ee; }
    .log-row.CRITICAL { background:#fdf0ff; color:#6b21a8; border-left:3px solid #7b2ff7; }
    .log-row.UNKNOWN  { background:#f4f5f7; color:#4b5675; border-left:3px solid #adb5bd; }

    .filter-badge {
        display: inline-block;
        background: #eef1fb; color: #4361ee;
        border: 1px solid #c5cff7; border-radius: 20px;
        padding: 3px 12px; font-size: 12px; font-weight: 600;
        margin-right: 6px; margin-bottom: 6px;
    }

    header[data-testid="stHeader"] { background: transparent; }
    .stDataFrame { background: #ffffff !important; border-radius: 10px; }
</style>
""", unsafe_allow_html=True)

# ════════════════════════════════════════════════
#  CONSTANTS
# ════════════════════════════════════════════════
LEVEL_COLORS = {
    "ERROR":    "#e03131",
    "WARNING":  "#e67700",
    "INFO":     "#2f9e44",
    "DEBUG":    "#4361ee",
    "CRITICAL": "#7b2ff7",
    "UNKNOWN":  "#adb5bd",
}
LEVEL_ICONS = {
    "ERROR": "🔴", "WARNING": "🟠", "INFO": "🟢",
    "DEBUG": "🔵", "CRITICAL": "🟣", "UNKNOWN": "⚪",
}
CHART_BG = "#ffffff"
CHART_FG = "#1a1d27"
CHART_AX = "#e2e6f0"

# Regex to parse a log line
LOG_PATTERN = re.compile(
    r"(?P<timestamp>\d{4}-\d{2}-\d{2}[\sT]\d{2}:\d{2}:\d{2})?"
    r"\s*\[?(?P<level>ERROR|WARNING|WARN|INFO|DEBUG|CRITICAL)\]?"
    r"\s*(?P<message>.+)",
    re.IGNORECASE,
)

# ════════════════════════════════════════════════
#  PARSING
# ════════════════════════════════════════════════

def parse_log_line(line: str):
    """Parse one log line. Returns a dict or None."""
    line = line.strip()
    if not line:
        return None
    match = LOG_PATTERN.search(line)
    if not match:
        return None

    raw_level = (match.group("level") or "UNKNOWN").upper()
    level = "WARNING" if raw_level == "WARN" else raw_level

    timestamp = None
    ts_str = match.group("timestamp")
    if ts_str:
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"):
            try:
                timestamp = datetime.strptime(ts_str, fmt)
                break
            except ValueError:
                continue

    return {
        "timestamp": timestamp,
        "level":     level,
        "message":   match.group("message").strip(),
        "raw":       line,
    }


def parse_log_file(content: str) -> pd.DataFrame:
    """Parse all lines in a log file. Returns a DataFrame."""
    records = [parse_log_line(l) for l in content.splitlines()]
    records = [r for r in records if r]
    if not records:
        return pd.DataFrame(columns=["timestamp", "level", "message", "raw"])
    return pd.DataFrame(records)


# ════════════════════════════════════════════════
#  FILTERS
# ════════════════════════════════════════════════

def apply_filters(df: pd.DataFrame, levels: list, keyword: str) -> pd.DataFrame:
    """
    Filter DataFrame by selected log levels and keyword.
    levels = list of level names to keep (empty = keep all)
    keyword = case-insensitive substring to match in messages
    """
    filtered = df.copy()
    if levels:
        filtered = filtered[filtered["level"].isin(levels)]
    if keyword.strip():
        filtered = filtered[
            filtered["message"].str.contains(keyword.strip(), case=False, na=False)
        ]
    return filtered


# ════════════════════════════════════════════════
#  ANALYTICS
# ════════════════════════════════════════════════

def get_level_counts(df: pd.DataFrame) -> Counter:
    return Counter(df["level"].tolist())

def get_top_errors(df: pd.DataFrame, n: int = 10) -> pd.DataFrame:
    errors = df[df["level"] == "ERROR"]["message"]
    top = Counter(errors).most_common(n)
    return pd.DataFrame(top, columns=["Error Message", "Count"])

def get_most_frequent_error(df: pd.DataFrame) -> str:
    errors = df[df["level"] == "ERROR"]["message"]
    if errors.empty:
        return "No errors found ✓"
    return Counter(errors).most_common(1)[0][0]


# ════════════════════════════════════════════════
#  CHARTS
# ════════════════════════════════════════════════

def _dark_style(fig, ax):
    fig.patch.set_facecolor(CHART_BG)
    ax.set_facecolor(CHART_BG)
    ax.tick_params(colors=CHART_FG, labelsize=11)
    ax.xaxis.label.set_color(CHART_FG)
    ax.yaxis.label.set_color(CHART_FG)
    ax.title.set_color(CHART_FG)
    for spine in ax.spines.values():
        spine.set_edgecolor(CHART_AX)

def plot_bar_chart(level_counts: Counter) -> plt.Figure:
    labels = list(level_counts.keys())
    values = list(level_counts.values())
    colors = [LEVEL_COLORS.get(l, "#8a97b8") for l in labels]

    fig, ax = plt.subplots(figsize=(6, max(3, len(labels) * 0.9)))
    bars = ax.barh(labels, values, color=colors, height=0.55, edgecolor="none")
    for bar, val in zip(bars, values):
        ax.text(
            bar.get_width() * 0.97, bar.get_y() + bar.get_height() / 2,
            f"{val:,}", va="center", ha="right",
            color="#ffffff", fontsize=11, fontweight="bold", fontfamily="monospace",
        )
    ax.set_xlabel("Count", fontsize=11)
    ax.set_title("Log Level Distribution", fontsize=13, fontweight="bold", pad=14)
    ax.invert_yaxis()
    _dark_style(fig, ax)
    fig.tight_layout()
    return fig

def plot_pie_chart(level_counts: Counter) -> plt.Figure:
    labels = list(level_counts.keys())
    values = list(level_counts.values())
    colors = [LEVEL_COLORS.get(l, "#8a97b8") for l in labels]

    fig, ax = plt.subplots(figsize=(5, 5))
    _, _, autotexts = ax.pie(
        values, labels=None, colors=colors,
        autopct="%1.1f%%", pctdistance=0.78, startangle=140,
        wedgeprops=dict(width=0.55, edgecolor=CHART_BG, linewidth=2),
    )
    for at in autotexts:
        at.set_color(CHART_FG)
        at.set_fontsize(10)

    patches = [mpatches.Patch(color=c, label=l) for c, l in zip(colors, labels)]
    ax.legend(handles=patches, loc="lower center", bbox_to_anchor=(0.5, -0.08),
              ncol=3, frameon=False, labelcolor=CHART_FG, fontsize=10)
    ax.set_title("Level Share", fontsize=13, fontweight="bold", pad=10)
    _dark_style(fig, ax)
    fig.tight_layout()
    return fig


# ════════════════════════════════════════════════
#  DOWNLOAD HELPERS
# ════════════════════════════════════════════════

def df_to_csv(df: pd.DataFrame) -> bytes:
    """Export timestamp / level / message as CSV."""
    out = df[["timestamp", "level", "message"]].copy()
    out["timestamp"] = out["timestamp"].astype(str)
    return out.to_csv(index=False).encode("utf-8")

def df_to_txt(df: pd.DataFrame) -> bytes:
    """Export raw log lines as plain text."""
    return "\n".join(df["raw"].tolist()).encode("utf-8")


# ════════════════════════════════════════════════
#  UI HELPERS
# ════════════════════════════════════════════════

def render_metric(label: str, value, css_class: str = ""):
    """Render a coloured KPI card."""
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">{label}</div>
        <div class="metric-value {css_class}">{value}</div>
    </div>
    """, unsafe_allow_html=True)


def render_log_rows(df: pd.DataFrame, max_rows: int = 300):
    """
    Render colour-highlighted log rows.
    ERROR = red, WARNING = orange/yellow, INFO = green, etc.
    """
    parts = []
    for _, row in df.head(max_rows).iterrows():
        lvl = row["level"]
        ts  = str(row["timestamp"]) if pd.notna(row["timestamp"]) else ""
        ts_html = f"<span style='opacity:.55'>{ts} </span>" if ts and ts != "NaT" else ""
        msg = row["message"]
        parts.append(
            f'<div class="log-row {lvl}">'
            f'<strong>[{lvl}]</strong> {ts_html}{msg}'
            f'</div>'
        )

    if len(df) > max_rows:
        parts.append(
            f'<div style="color:#8a97b8;font-size:12px;margin-top:8px;">'
            f'⋯ showing first {max_rows:,} of {len(df):,} matching rows'
            f'</div>'
        )

    st.markdown("\n".join(parts), unsafe_allow_html=True)


# ════════════════════════════════════════════════
#  MAIN
# ════════════════════════════════════════════════

def main():

    # ── Hero ──────────────────────────────────────────────────────
    st.markdown("""
    <div style="padding:28px 0 12px;">
        <div class="hero-title">🔍 Log Analysis Dashboard</div>
        <div class="hero-sub">
            Upload a <code>.txt</code> log file · Filter by level or keyword ·
            Download results · Visualize patterns
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── File uploader ─────────────────────────────────────────────
    st.markdown('<div class="section-title">📂 Upload Log File</div>', unsafe_allow_html=True)
    uploaded = st.file_uploader(
        label="",
        type=["txt"],
        help="Plain-text log files (.txt) with ERROR / WARNING / INFO / DEBUG entries",
    )

    if not uploaded:
        st.info("⬆️  Upload a `.txt` log file above to begin analysis.")
        return

    # ── Parse ─────────────────────────────────────────────────────
    content = uploaded.read().decode("utf-8", errors="replace")
    df_all  = parse_log_file(content)

    if df_all.empty:
        st.error("No recognisable log entries found. Check that your file "
                 "contains lines with level labels (ERROR, WARNING, INFO…).")
        return

    # ════════════════════════════════════════════
    #  SIDEBAR — filters + downloads
    # ════════════════════════════════════════════
    with st.sidebar:
        st.markdown("## 🎛️ Controls")
        st.markdown("---")

        # ── Level checkboxes ──────────────────────────────────────
        st.markdown("### 📊 Filter by Level")
        available_levels = sorted(df_all["level"].unique().tolist())
        selected_levels  = []
        for lvl in available_levels:
            icon = LEVEL_ICONS.get(lvl, "⚪")
            if st.checkbox(f"{icon} {lvl}", value=True, key=f"chk_{lvl}"):
                selected_levels.append(lvl)

        st.markdown("---")

        # ── Keyword search ────────────────────────────────────────
        st.markdown("### 🔎 Keyword Search")
        keyword = st.text_input(
            label="",
            placeholder="e.g. Connection refused",
            help="Case-insensitive — searches log messages",
        )

        st.markdown("---")

        # ── Download buttons (filled after df is ready) ───────────
        st.markdown("### 💾 Download Results")
        dl_slot = st.empty()      # placeholder — populated after filtering

        st.markdown("---")
        st.markdown(
            f"<div style='font-size:12px;color:#8a97b8;line-height:1.8'>"
            f"📄 <b>File:</b> {uploaded.name}<br>"
            f"📏 <b>Total lines:</b> {len(df_all):,}"
            f"</div>",
            unsafe_allow_html=True,
        )

    # ── Apply filters ─────────────────────────────────────────────
    df = apply_filters(df_all, selected_levels, keyword)

    # ── Active filter pills ───────────────────────────────────────
    pills = "".join(
        f'<span class="filter-badge">{LEVEL_ICONS.get(l,"")} {l}</span>'
        for l in selected_levels
    )
    if keyword.strip():
        pills += f'<span class="filter-badge">🔎 &ldquo;{keyword.strip()}&rdquo;</span>'
    if pills:
        st.markdown(f'<div style="margin-bottom:4px;">Active filters: {pills}</div>',
                    unsafe_allow_html=True)

    # ── KPI cards ─────────────────────────────────────────────────
    st.markdown('<div class="section-title">📈 Summary</div>', unsafe_allow_html=True)

    counts_filtered = get_level_counts(df)
    c1, c2, c3, c4, c5 = st.columns(5)
    with c1: render_metric("Total (file)",   f"{len(df_all):,}",                      "total")
    with c2: render_metric("Showing",        f"{len(df):,}",                           "filtered")
    with c3: render_metric("🔴 Errors",      f"{counts_filtered.get('ERROR',0):,}",    "error")
    with c4: render_metric("🟡 Warnings",    f"{counts_filtered.get('WARNING',0):,}",  "warn")
    with c5: render_metric("🟢 Info",        f"{counts_filtered.get('INFO',0):,}",     "info")

    # ── Most frequent error ───────────────────────────────────────
    st.markdown('<div class="section-title">⚠️ Most Frequent Error</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="error-box">⚠ {get_most_frequent_error(df)}</div>',
                unsafe_allow_html=True)

    # ── Charts ────────────────────────────────────────────────────
    st.markdown('<div class="section-title">📊 Visualizations</div>', unsafe_allow_html=True)

    if df.empty:
        st.warning("No entries match the current filters — charts unavailable.")
    else:
        col_bar, col_pie = st.columns(2)
        with col_bar:
            st.pyplot(plot_bar_chart(counts_filtered), use_container_width=True)
        with col_pie:
            st.pyplot(plot_pie_chart(counts_filtered), use_container_width=True)

    # ── Top errors table ──────────────────────────────────────────
    st.markdown('<div class="section-title">🏆 Top Error Messages</div>', unsafe_allow_html=True)
    top_errors = get_top_errors(df)
    if top_errors.empty:
        st.success("✅ No ERROR entries in the current filtered view.")
    else:
        col_tbl, _ = st.columns([2, 1])
        with col_tbl:
            st.dataframe(
                top_errors, use_container_width=True, hide_index=True,
                column_config={
                    "Error Message": st.column_config.TextColumn(width="large"),
                    "Count":         st.column_config.NumberColumn(format="%d"),
                },
            )

    # ── Colour-coded log viewer ───────────────────────────────────
    st.markdown('<div class="section-title">🖥️ Log Viewer</div>', unsafe_allow_html=True)
    if df.empty:
        st.warning("No entries match your current filters.")
    else:
        render_log_rows(df, max_rows=300)

    # ── Error timeline ────────────────────────────────────────────
    if df["timestamp"].notna().any():
        st.markdown('<div class="section-title">⏱️ Error Timeline</div>', unsafe_allow_html=True)
        errors_time = (
            df[df["level"] == "ERROR"]
            .dropna(subset=["timestamp"])
            .set_index("timestamp")
            .resample("1min")
            .size()
            .reset_index(name="Errors per Minute")
        )
        if not errors_time.empty:
            st.line_chart(
                errors_time.set_index("timestamp")["Errors per Minute"],
                use_container_width=True, color="#e03131",
            )
        else:
            st.caption("No timestamped ERROR entries in the current filter.")

    # ── Sidebar download buttons (now df is ready) ────────────────
    with dl_slot:
        if not df.empty:
            col_a, col_b = st.columns(2)
            with col_a:
                st.download_button(
                    label="⬇️ CSV",
                    data=df_to_csv(df),
                    file_name="filtered_logs.csv",
                    mime="text/csv",
                    use_container_width=True,
                )
            with col_b:
                st.download_button(
                    label="⬇️ TXT",
                    data=df_to_txt(df),
                    file_name="filtered_logs.txt",
                    mime="text/plain",
                    use_container_width=True,
                )
        else:
            st.caption("No data to download.")

    # ── Footer ────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown(
        "<div style='color:#8a97b8;font-size:12px;text-align:center;'>"
        "Log Analysis Dashboard · Built with Python & Streamlit"
        "</div>",
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
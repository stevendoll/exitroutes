import io
import logging
import streamlit as st

from parser import FieldRoutesParser
from cleaner import DataCleaner
from mapper import FieldMapper, DESTINATION_CONFIGS
from packager import MigrationPackager

logging.basicConfig(level=logging.INFO)

st.set_page_config(
    page_title="SwitchKit — FieldRoutes Migration",
    page_icon="⚡",
    layout="wide",
)

st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&family=Syne:wght@700;800&display=swap');

  :root {
    --bg: #0A0F1C;
    --surface: #111827;
    --accent: #F5C842;
    --text: #F0EDE4;
    --muted: #8899AA;
    --border: #1E2D40;
    --success: #2ECC71;
  }

  html, body, [class*="css"] {
    background-color: var(--bg) !important;
    color: var(--text) !important;
    font-family: 'IBM Plex Mono', monospace;
  }

  h1, h2, h3 {
    font-family: 'Syne', sans-serif !important;
    color: var(--text) !important;
  }

  .stButton > button {
    background: var(--accent) !important;
    color: #0A0F1C !important;
    font-family: 'IBM Plex Mono', monospace !important;
    font-weight: 500 !important;
    border: none !important;
    border-radius: 4px !important;
  }

  .stButton > button:hover { opacity: 0.9 !important; }

  .stDownloadButton > button {
    background: var(--accent) !important;
    color: #0A0F1C !important;
    font-family: 'IBM Plex Mono', monospace !important;
    font-weight: 500 !important;
    font-size: 1rem !important;
    padding: 0.75rem 2rem !important;
    border: none !important;
    border-radius: 4px !important;
    width: 100% !important;
  }

  .stFileUploader { border: 1px solid var(--border) !important; border-radius: 6px !important; }

  .metric-card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 6px;
    padding: 1.25rem;
    text-align: center;
  }
  .metric-value {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 2rem;
    font-weight: 500;
    color: var(--accent);
  }
  .metric-label {
    font-size: 0.78rem;
    color: var(--muted);
    letter-spacing: 0.08em;
    text-transform: uppercase;
    margin-top: 0.25rem;
  }
  .warn-box {
    background: rgba(245,200,66,0.08);
    border: 1px solid rgba(245,200,66,0.25);
    border-radius: 6px;
    padding: 1rem 1.25rem;
    margin-bottom: 0.75rem;
    font-size: 0.88rem;
    color: var(--muted);
  }
  .success-tag {
    color: var(--success);
    font-weight: 500;
  }
</style>
""", unsafe_allow_html=True)


def metric_card(value, label):
    st.markdown(f"""
    <div class="metric-card">
      <div class="metric-value">{value}</div>
      <div class="metric-label">{label}</div>
    </div>
    """, unsafe_allow_html=True)


# ── Header ────────────────────────────────────────────────────────────
st.markdown("### ⚡ SwitchKit")
st.markdown("#### FieldRoutes Migration Tool")
st.markdown("---")

# ── Session state ─────────────────────────────────────────────────────
if "result" not in st.session_state:
    st.session_state.result = None

# ── Upload ────────────────────────────────────────────────────────────
if st.session_state.result is None:
    st.markdown("**Upload your FieldRoutes export files**")
    st.markdown(
        "<span style='color:var(--muted);font-size:0.85rem'>"
        "Upload one or more CSV files — customers, subscriptions, or service history."
        "</span>",
        unsafe_allow_html=True,
    )

    uploaded = st.file_uploader(
        "Choose CSV files",
        type=["csv"],
        accept_multiple_files=True,
        label_visibility="collapsed",
    )

    destination = st.selectbox(
        "I'm migrating to:",
        list(DESTINATION_CONFIGS.keys()),
    )

    if st.button("Process migration →") and uploaded:
        with st.spinner("Processing..."):
            progress = st.progress(0)

            # Step 1: Parse
            st.markdown("**01** — Parsing files...")
            files = {f.name: io.BytesIO(f.read()) for f in uploaded}
            parser = FieldRoutesParser()
            tables = parser.parse(files)
            progress.progress(25)

            if not tables:
                st.error("No recognizable FieldRoutes CSV files found. Check that you uploaded the right files.")
                st.stop()

            # Step 2: Clean
            st.markdown("**02** — Cleaning data...")
            cleaner = DataCleaner()
            cleaned, report = cleaner.clean(tables)
            progress.progress(50)

            # Step 3: Map
            st.markdown("**03** — Mapping to destination format...")
            mapper = FieldMapper(destination)
            mapped = mapper.map(cleaned)
            progress.progress(75)

            # Step 4: Package
            st.markdown("**04** — Generating migration package...")
            packager = MigrationPackager()
            zip_bytes = packager.package(mapped, report, destination, original_tables=cleaned)
            progress.progress(100)

            st.session_state.result = {
                "zip_bytes": zip_bytes,
                "report": report,
                "mapped": mapped,
                "destination": destination,
            }
            st.rerun()

# ── Results ───────────────────────────────────────────────────────────
if st.session_state.result:
    r = st.session_state.result
    report = r["report"]
    mapped = r["mapped"]

    st.markdown("<span class='success-tag'>✓ Migration package ready</span>", unsafe_allow_html=True)
    st.markdown(f"**Destination:** {r['destination']}")
    st.markdown("---")

    # Metrics
    warning_count = (
        len(report.get("missing_email", []))
        + len(report.get("invalid_phone", []))
        + len(report.get("duplicate_flags", []))
        + len(report.get("missing_address_fields", []))
    )

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        metric_card(report.get("total_customers", 0), "Customers")
    with col2:
        metric_card(len(mapped.get("subscriptions", [])), "Subscriptions")
    with col3:
        metric_card(len(mapped.get("service_history", [])), "Service records")
    with col4:
        metric_card(warning_count, "Warnings")

    # Warnings
    if warning_count > 0:
        st.markdown("---")
        with st.expander(f"⚠ Warnings ({warning_count}) — review before importing"):
            missing_email = report.get("missing_email", [])
            if missing_email:
                st.markdown(f"**Missing email** ({len(missing_email)} customers)")
                for cid in missing_email:
                    st.markdown(f"<div class='warn-box'>CustomerID {cid}</div>", unsafe_allow_html=True)

            invalid_phone = report.get("invalid_phone", [])
            if invalid_phone:
                st.markdown(f"**Invalid/missing phone** ({len(invalid_phone)} customers)")
                for cid in invalid_phone:
                    st.markdown(f"<div class='warn-box'>CustomerID {cid}</div>", unsafe_allow_html=True)

            dupes = report.get("duplicate_flags", [])
            if dupes:
                st.markdown(f"**Potential duplicates** ({len(dupes)} pairs)")
                for pair in dupes:
                    st.markdown(
                        f"<div class='warn-box'>CustomerID {pair[0]} and {pair[1]} may be the same</div>",
                        unsafe_allow_html=True,
                    )

    st.markdown("---")

    st.download_button(
        label="⬇ Download migration package (.zip)",
        data=r["zip_bytes"],
        file_name="switchkit_migration.zip",
        mime="application/zip",
    )

    if st.button("← Start over"):
        st.session_state.result = None
        st.rerun()

    st.markdown(
        "<div style='text-align:center;margin-top:2rem;font-size:0.8rem;color:var(--muted)'>"
        "Questions? Email <a href='mailto:steven@t12n.ai' style='color:var(--accent)'>steven@t12n.ai</a>"
        "</div>",
        unsafe_allow_html=True,
    )

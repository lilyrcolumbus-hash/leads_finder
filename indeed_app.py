#!/usr/bin/env python3
"""
Indeed Leads Finder - AI Sales Team Tool

A dedicated app to find companies hiring on Indeed.
Search by any keyword, location, and filters to generate warm leads.

Run with: streamlit run indeed_app.py
"""

import streamlit as st
import pandas as pd
from datetime import datetime
import sys
import csv
import io
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.scrapers.indeed_search import IndeedSearchScraper, IndeedSearchParams


# --- Page Config ---
st.set_page_config(
    page_title="Indeed Leads Finder",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --- CSS ---
st.markdown("""
<style>
    .main-title {
        font-size: 2.2rem;
        font-weight: 800;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-align: center;
        margin-bottom: 0.5rem;
    }
    .subtitle {
        text-align: center;
        color: #666;
        font-size: 1.1rem;
        margin-bottom: 2rem;
    }
    .metric-card {
        background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
        border-radius: 12px;
        padding: 1.2rem;
        text-align: center;
        margin: 0.5rem 0;
    }
    .metric-card h3 {
        margin: 0;
        color: #333;
        font-size: 2rem;
    }
    .metric-card p {
        margin: 0;
        color: #666;
        font-size: 0.9rem;
    }
    .lead-row {
        background: #fff;
        border: 1px solid #e8e8e8;
        border-radius: 10px;
        padding: 1rem;
        margin: 0.5rem 0;
        transition: box-shadow 0.2s;
    }
    .lead-row:hover {
        box-shadow: 0 4px 12px rgba(0,0,0,0.1);
    }
    .tag {
        display: inline-block;
        background: #e8f0fe;
        color: #1a73e8;
        padding: 2px 10px;
        border-radius: 12px;
        font-size: 0.8rem;
        margin: 2px;
    }
    .salary-tag {
        background: #e6f4ea;
        color: #137333;
    }
    .search-count {
        text-align: center;
        font-size: 1rem;
        color: #555;
        padding: 1rem;
    }

    /* Mobile */
    @media (max-width: 768px) {
        .main-title { font-size: 1.6rem; }
        .stButton > button {
            width: 100% !important;
            min-height: 3rem !important;
        }
        input, select, textarea { font-size: 16px !important; }
    }
</style>
""", unsafe_allow_html=True)


# --- Session State ---
if "search_results" not in st.session_state:
    st.session_state.search_results = []
if "search_history" not in st.session_state:
    st.session_state.search_history = []
if "total_leads_found" not in st.session_state:
    st.session_state.total_leads_found = 0


def main():
    """Main app."""

    # --- Header ---
    st.markdown('<h1 class="main-title">Indeed Leads Finder</h1>', unsafe_allow_html=True)
    st.markdown('<p class="subtitle">Find companies hiring on Indeed. Any keyword. Any city. Your leads.</p>', unsafe_allow_html=True)

    # --- Sidebar: Search Filters ---
    with st.sidebar:
        st.markdown("## Search Filters")
        st.markdown("---")

        # Keywords
        keyword_input = st.text_area(
            "Keywords (one per line)",
            value="receptionist\nfront desk\ncustomer service",
            height=120,
            help="Enter job titles or keywords to search. One per line."
        )
        keywords = [k.strip() for k in keyword_input.strip().split("\n") if k.strip()]

        st.markdown("---")

        # Location
        location = st.text_input(
            "Location",
            value="Lima, OH",
            help="City, State or ZIP code"
        )

        radius = st.select_slider(
            "Radius (miles)",
            options=[5, 10, 15, 25, 50, 100],
            value=25
        )

        st.markdown("---")

        # Date range
        date_range = st.selectbox(
            "Posted within",
            options=[1, 3, 7, 14, 30],
            index=3,
            format_func=lambda x: {
                1: "Last 24 hours",
                3: "Last 3 days",
                7: "Last 7 days",
                14: "Last 14 days",
                30: "Last 30 days",
            }[x]
        )

        st.markdown("---")

        # Job type
        job_type = st.selectbox(
            "Job Type",
            options=["", "fulltime", "parttime", "contract", "temporary", "internship"],
            format_func=lambda x: {
                "": "All Types",
                "fulltime": "Full-time",
                "parttime": "Part-time",
                "contract": "Contract",
                "temporary": "Temporary",
                "internship": "Internship",
            }[x]
        )

        # Remote filter
        remote = st.selectbox(
            "Remote",
            options=["", "remote"],
            format_func=lambda x: {
                "": "All (on-site + remote)",
                "remote": "Remote only",
            }[x]
        )

        # Experience level
        experience = st.selectbox(
            "Experience Level",
            options=["", "entry_level", "mid_level", "senior_level"],
            format_func=lambda x: {
                "": "All Levels",
                "entry_level": "Entry Level",
                "mid_level": "Mid Level",
                "senior_level": "Senior Level",
            }[x]
        )

        st.markdown("---")

        # Sort
        sort_by = st.radio(
            "Sort by",
            options=["date", "relevance"],
            format_func=lambda x: "Most Recent" if x == "date" else "Most Relevant",
            horizontal=True,
        )

        # Max results
        max_results = st.slider("Max results", min_value=10, max_value=100, value=50, step=10)

        st.markdown("---")
        st.caption("v2.0 | AI Sales Team Tool")

    # --- Main Content ---

    # Quick stats
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(f"""
        <div class="metric-card">
            <h3>{len(st.session_state.search_results)}</h3>
            <p>Current Results</p>
        </div>
        """, unsafe_allow_html=True)
    with col2:
        st.markdown(f"""
        <div class="metric-card">
            <h3>{st.session_state.total_leads_found}</h3>
            <p>Total Leads Found</p>
        </div>
        """, unsafe_allow_html=True)
    with col3:
        st.markdown(f"""
        <div class="metric-card">
            <h3>{len(st.session_state.search_history)}</h3>
            <p>Searches Done</p>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("")

    # --- Search Button ---
    search_col1, search_col2, search_col3 = st.columns([1, 2, 1])
    with search_col2:
        search_clicked = st.button(
            "SEARCH INDEED",
            type="primary",
            use_container_width=True,
        )

    if search_clicked:
        if not keywords:
            st.warning("Enter at least one keyword to search.")
            return

        # Build search params
        params = IndeedSearchParams(
            keywords=keywords,
            location=location,
            date_range=date_range,
            job_type=job_type,
            remote=remote,
            sort_by=sort_by,
            radius=radius,
            max_results=max_results,
            experience_level=experience,
        )

        # Run search
        progress = st.progress(0, text="Initializing search...")
        status = st.empty()
        results_container = st.container()

        all_leads = []

        try:
            with IndeedSearchScraper(params) as scraper:
                for i, keyword in enumerate(keywords):
                    progress_pct = (i + 1) / len(keywords)
                    status.markdown(f"**Searching:** `{keyword}` in `{location}`...")
                    progress.progress(progress_pct, text=f"Searching: {keyword}...")

                    # The scraper handles all keywords internally,
                    # but we show progress per keyword
                    pass

                # Run the actual scrape
                status.markdown("**Running full search...**")
                batch = scraper.scrape()
                all_leads = batch.leads

                progress.progress(1.0, text="Search complete!")

                if batch.errors:
                    for err in batch.errors:
                        st.warning(f"Warning: {err}")

        except Exception as e:
            st.error(f"Search error: {str(e)}")
            return

        # Store results
        st.session_state.search_results = all_leads
        st.session_state.total_leads_found += len(all_leads)
        st.session_state.search_history.append({
            "keywords": keywords,
            "location": location,
            "results": len(all_leads),
            "timestamp": datetime.now().strftime("%H:%M:%S"),
        })

        status.markdown(
            f'<p class="search-count">Found <strong>{len(all_leads)}</strong> '
            f'companies hiring for your keywords in <strong>{location}</strong></p>',
            unsafe_allow_html=True,
        )

    # --- Display Results ---
    if st.session_state.search_results:
        st.markdown("---")

        # Tabs: Cards / Table / Export
        tab_cards, tab_table, tab_export = st.tabs([
            "Lead Cards", "Data Table", "Export"
        ])

        leads = st.session_state.search_results

        with tab_cards:
            st.markdown(f"### {len(leads)} Leads Found")

            for i, lead in enumerate(leads):
                # Parse content for display
                content_lines = lead.content.split("\n")
                info = {}
                for line in content_lines:
                    if ":" in line:
                        key, val = line.split(":", 1)
                        info[key.strip()] = val.strip()

                position = info.get("Position", "")
                company = lead.company or info.get("Company", "Unknown")
                loc = info.get("Location", "")
                salary = info.get("Salary", "")
                desc = info.get("Description", "")

                with st.expander(
                    f"**{i+1}. {company}** — {position}",
                    expanded=(i < 3),
                ):
                    col_a, col_b = st.columns([2, 1])

                    with col_a:
                        st.markdown(f"**Company:** {company}")
                        st.markdown(f"**Position:** {position}")
                        st.markdown(f"**Location:** {loc}")
                        if salary:
                            st.markdown(f"**Salary:** {salary}")
                        if desc:
                            st.markdown(f"**Description:** {desc[:300]}{'...' if len(desc) > 300 else ''}")

                    with col_b:
                        if lead.url:
                            st.link_button("View on Indeed", lead.url)

                        # Tags
                        tags_html = ""
                        for kw in lead.keywords_matched[:4]:
                            css_class = "tag salary-tag" if "salary" in kw.lower() else "tag"
                            tags_html += f'<span class="{css_class}">{kw}</span> '
                        if tags_html:
                            st.markdown(tags_html, unsafe_allow_html=True)

        with tab_table:
            # Build DataFrame
            rows = []
            for lead in leads:
                content_lines = lead.content.split("\n")
                info = {}
                for line in content_lines:
                    if ":" in line:
                        key, val = line.split(":", 1)
                        info[key.strip()] = val.strip()

                rows.append({
                    "Company": lead.company or info.get("Company", ""),
                    "Position": info.get("Position", ""),
                    "Location": info.get("Location", ""),
                    "Salary": info.get("Salary", ""),
                    "Description": info.get("Description", "")[:150],
                    "URL": lead.url or "",
                })

            df = pd.DataFrame(rows)
            st.dataframe(df, use_container_width=True, height=500)

        with tab_export:
            st.markdown("### Export Your Leads")

            # Build export data
            export_rows = []
            for lead in leads:
                content_lines = lead.content.split("\n")
                info = {}
                for line in content_lines:
                    if ":" in line:
                        key, val = line.split(":", 1)
                        info[key.strip()] = val.strip()

                export_rows.append({
                    "Company": lead.company or info.get("Company", ""),
                    "Position": info.get("Position", ""),
                    "Location": info.get("Location", ""),
                    "Salary": info.get("Salary", ""),
                    "Description": info.get("Description", ""),
                    "Indeed URL": lead.url or "",
                    "Keywords": ", ".join(lead.keywords_matched),
                    "Found At": lead.found_at.strftime("%Y-%m-%d %H:%M"),
                })

            export_df = pd.DataFrame(export_rows)

            # CSV download
            csv_buffer = io.StringIO()
            export_df.to_csv(csv_buffer, index=False)
            csv_data = csv_buffer.getvalue()

            timestamp = datetime.now().strftime("%Y%m%d_%H%M")
            safe_location = location.replace(",", "").replace(" ", "_")

            col_dl1, col_dl2 = st.columns(2)

            with col_dl1:
                st.download_button(
                    label="Download CSV",
                    data=csv_data,
                    file_name=f"indeed_leads_{safe_location}_{timestamp}.csv",
                    mime="text/csv",
                    use_container_width=True,
                )

            with col_dl2:
                # TSV for Google Sheets paste
                tsv_buffer = io.StringIO()
                export_df.to_csv(tsv_buffer, index=False, sep="\t")
                tsv_data = tsv_buffer.getvalue()

                st.download_button(
                    label="Download TSV (Google Sheets)",
                    data=tsv_data,
                    file_name=f"indeed_leads_{safe_location}_{timestamp}.tsv",
                    mime="text/tab-separated-values",
                    use_container_width=True,
                )

            st.markdown("---")
            st.markdown("**Preview:**")
            st.dataframe(export_df.head(5), use_container_width=True)

    # --- Search History ---
    if st.session_state.search_history:
        st.markdown("---")
        st.markdown("### Recent Searches")
        for i, search in enumerate(reversed(st.session_state.search_history[-5:])):
            kws = ", ".join(search["keywords"][:3])
            st.markdown(
                f"**{search['timestamp']}** | "
                f"`{kws}` in `{search['location']}` | "
                f"**{search['results']}** results"
            )


if __name__ == "__main__":
    main()

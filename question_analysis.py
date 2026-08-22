import hashlib
from io import BytesIO

import pandas as pd
import streamlit as st

from analysis import build_report_model
from helper import normalize_total_sc
from html_report import count_report_plots, generate_html_report
from plots import exam_stats, render_comparison, render_single_exam


st.title("WUCT Exam Review")

sc_files = st.file_uploader(
    "Upload scores here. Make sure you downloaded the scores from GradeScope as csv files.",
    type="csv",
    accept_multiple_files=True,
)


@st.cache_data(show_spinner=False, max_entries=8)
def build_cached_report_model(file_payloads):
    """Parse uploaded CSV bytes and cache the complete reusable analysis model."""

    names = []
    score_frames = []
    for name, csv_bytes in file_payloads:
        score_frame = pd.read_csv(BytesIO(csv_bytes)).dropna(axis=0, how="any")
        score_frames.append(normalize_total_sc(score_frame))
        names.append(name)
    return build_report_model(score_frames, names)


@st.fragment
def comparison_mode_tabs(comparison, key_prefix):
    """Render only the selected individual/combined comparison view."""

    individual_stats, combined_stats = st.tabs(
        ["Individual Stats", "Combined Stats"],
        key=f"{key_prefix}-mode-tabs",
        on_change="rerun",
    )
    if individual_stats.open:
        with individual_stats:
            render_comparison(
                comparison,
                key_prefix=f"{key_prefix}-individual",
            )
    if combined_stats.open:
        with combined_stats:
            render_single_exam(
                comparison.combined,
                key_prefix=f"{key_prefix}-combined",
            )


@st.fragment
def report_selector(report_model):
    """Render the dynamic pair selector and downloadable static report."""

    st.header("Generate HTML Report")
    st.write(
        "Generate a self-contained report with the exam breakdown, every individual "
        "exam, and any ordered exam comparisons selected below."
    )

    names = report_model.names
    if len(names) < 2:
        st.info("Upload at least two exams to add a pairwise comparison.")

    upload_key = hashlib.sha256("\0".join(names).encode("utf-8")).hexdigest()[:12]
    count_key = f"html_report_pair_count_{upload_key}"
    result_key = f"html_report_result_{upload_key}"
    if count_key not in st.session_state:
        st.session_state[count_key] = 1 if len(names) >= 2 else 0

    def adjust_pair_count(change):
        st.session_state[count_key] += change

    selected_pairs = []
    for row_index in range(st.session_state[count_key]):
        number_column, lower_column, higher_column = st.columns([0.08, 0.46, 0.46])
        with number_column:
            st.markdown(f"**{row_index + 1}.**")
        with lower_column:
            lower_name = st.selectbox(
                "Lower division",
                options=names,
                index=row_index % len(names),
                key=f"html_report_lower_{upload_key}_{row_index}",
            )
        with higher_column:
            higher_name = st.selectbox(
                "Higher division",
                options=names,
                index=(row_index + 1) % len(names),
                key=f"html_report_higher_{upload_key}_{row_index}",
            )
        selected_pairs.append((lower_name, higher_name))

    add_column, remove_column, _ = st.columns([0.2, 0.2, 0.6])
    with add_column:
        st.button(
            "Add comparison",
            disabled=len(names) < 2,
            key=f"html_report_add_{upload_key}",
            on_click=adjust_pair_count,
            args=(1,),
        )
    with remove_column:
        st.button(
            "Remove last",
            disabled=st.session_state[count_key] == 0,
            key=f"html_report_remove_{upload_key}",
            on_click=adjust_pair_count,
            args=(-1,),
        )

    if st.button(
        "Generate HTML Report",
        type="primary",
        key=f"html_report_generate_{upload_key}",
    ):
        same_exam_rows = [
            index + 1
            for index, (lower_name, higher_name) in enumerate(selected_pairs)
            if lower_name == higher_name
        ]
        duplicate_rows = []
        seen_pairs = set()
        for index, pair in enumerate(selected_pairs):
            if pair in seen_pairs:
                duplicate_rows.append(index + 1)
            seen_pairs.add(pair)

        if same_exam_rows:
            rows = ", ".join(str(row) for row in same_exam_rows)
            st.error(f"Select two different exams in comparison row(s): {rows}.")
        elif duplicate_rows:
            rows = ", ".join(str(row) for row in duplicate_rows)
            st.error(f"Remove duplicate comparison row(s): {rows}.")
        else:
            total_plots = count_report_plots(report_model, selected_pairs)
            progress_bar = st.progress(
                0.0,
                text=f"Drawing report plots: 0 of {total_plots}",
            )

            def update_plot_progress(completed, total):
                progress_bar.progress(
                    completed / total,
                    text=f"Drawing report plots: {completed} of {total}",
                )

            with st.spinner("Generating all report tables and graphics..."):
                report_bytes = generate_html_report(
                    report_model,
                    selected_pairs,
                    progress_callback=update_plot_progress,
                )
            st.session_state[result_key] = {
                "data": report_bytes,
                "pairs": tuple(selected_pairs),
            }
            st.success("The HTML report is ready to download.")

    if result_key in st.session_state:
        result = st.session_state[result_key]
        st.download_button(
            "Download HTML Report",
            data=result["data"],
            file_name="WUCT_Exam_Review_Report.html",
            mime="text/html",
            key=f"html_report_download_{upload_key}",
        )
        if result["pairs"] != tuple(selected_pairs):
            st.caption(
                "The available download reflects the last generated selections. "
                "Generate the report again to apply the current comparison rows."
            )


if sc_files:
    file_payloads = tuple(
        (sc_file.name[:-4], sc_file.getvalue()) for sc_file in sc_files
    )

    try:
        model = build_cached_report_model(file_payloads)
    except ValueError as exc:
        st.error(str(exc))
        st.stop()

    exam_stats(model.stats, model.total_scores)

    st.header("Question Breakdown")

    @st.fragment()
    def question_breakdown():
        selected_name = st.selectbox(
            label=(
                "Select a scores set to view analysis. If comparing, this is the "
                "lower division."
            ),
            options=model.names,
        )
        compare_name = st.selectbox(
            label=(
                "Select a second scores set to compare (optional). This is the "
                "higher division."
            ),
            options=[None] + [name for name in model.names if name != selected_name],
            format_func=lambda value: (
                "None" if value is None else value.replace("_", " ")
            ),
        )

        selected_exam = model.exam(selected_name)
        if compare_name is None:
            render_single_exam(
                selected_exam,
                key_prefix=f"question-single-{selected_exam.name}",
            )
        else:
            comparison = model.compare(selected_name, compare_name)
            comparison_mode_tabs(
                comparison,
                key_prefix=(
                    f"question-comparison-{comparison.lower.name}-"
                    f"{comparison.higher.name}"
                ),
            )

    question_breakdown()
    report_selector(model)

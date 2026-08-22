"""Lazy Streamlit renderer for the reusable analysis and figure layers."""

import streamlit as st

from analysis import ComparisonAnalysis, ExamAnalysis
from figures import (
    comparison_overview_distribution,
    comparison_question_distribution,
    exam_average_distribution,
    exam_consistency_distribution,
    exam_question_distribution,
    plot_consistency,
    plot_q_breakdown,
    single_average_distribution,
    single_discrimination_distribution,
    single_question_distribution,
)


@st.fragment
def _exam_overview_tabs(stats_df):
    by_mean, by_ca = st.tabs(
        ["By average", "By Cronbach's alpha"],
        key="exam-overview-tabs",
        on_change="rerun",
    )
    if by_mean.open:
        with by_mean:
            st.pyplot(exam_average_distribution(stats_df))
    if by_ca.open:
        with by_ca:
            st.pyplot(exam_consistency_distribution(stats_df))


@st.fragment
def _exam_level_tabs(stats_df, total_sc_df):
    exam_bar, exam_box, exam_data = st.tabs(
        ["Bar", "Box", "Data"],
        key="exam-level-tabs",
        on_change="rerun",
    )
    if exam_bar.open:
        with exam_bar:
            st.pyplot(exam_question_distribution(stats_df, total_sc_df, "bar"))
    if exam_box.open:
        with exam_box:
            st.pyplot(exam_question_distribution(stats_df, total_sc_df, "box"))
    if exam_data.open:
        with exam_data:
            st.dataframe(stats_df)


def exam_stats(stats_df, total_sc_df):
    st.header("Exam Breakdown")
    st.subheader("Overview")
    _exam_overview_tabs(stats_df)
    st.subheader("Exam-Level Statistics")
    _exam_level_tabs(stats_df, total_sc_df)


@st.fragment
def _single_overview_tabs(summary, display_name, key_prefix):
    by_avg, by_di = st.tabs(
        ["Overview by average", "Overview by DI"],
        key=f"{key_prefix}-overview-tabs",
        on_change="rerun",
    )
    if by_avg.open:
        with by_avg:
            st.pyplot(single_average_distribution(summary, display_name))
    if by_di.open:
        with by_di:
            st.pyplot(single_discrimination_distribution(summary, display_name))


@st.fragment
def _single_question_tabs(summary, display_name, sc_df_long, key_prefix):
    consistency, bar, box, split_violin, raw_df = st.tabs(
        ["Consistency", "Bar", "Box", "Discrimination", "Data"],
        key=f"{key_prefix}-question-tabs",
        on_change="rerun",
    )
    if consistency.open:
        with consistency:
            st.plotly_chart(
                plot_consistency(summary, display_name),
                width="stretch",
            )
    if bar.open:
        with bar:
            st.pyplot(
                single_question_distribution(summary, sc_df_long, display_name, "bar")
            )
    if box.open:
        with box:
            st.pyplot(
                single_question_distribution(summary, sc_df_long, display_name, "box")
            )
    if split_violin.open:
        with split_violin:
            st.pyplot(
                single_question_distribution(
                    summary,
                    sc_df_long,
                    display_name,
                    "split-violin",
                )
            )
    if raw_df.open:
        with raw_df:
            st.dataframe(summary)


def single_stats(summary, display_name, sc_df_long, *, key_prefix="single"):
    """Render one exam with independently rerunning, lazy tab fragments."""

    st.subheader("Overview")
    _single_overview_tabs(summary, display_name, key_prefix)
    st.subheader("Question-Level Statistics")
    _single_question_tabs(summary, display_name, sc_df_long, key_prefix)


def render_single_exam(exam: ExamAnalysis, *, key_prefix=None):
    key_prefix = key_prefix or f"single-{exam.name}"
    single_stats(
        exam.summary,
        exam.display_name,
        exam.long_scores,
        key_prefix=key_prefix,
    )


@st.fragment
def _comparison_overview_tabs(
    summary,
    summary2,
    display_name,
    display_name2,
    key_prefix,
):
    by_avg, by_di = st.tabs(
        ["By average", "By discrimination index"],
        key=f"{key_prefix}-overview-tabs",
        on_change="rerun",
    )
    if by_avg.open:
        with by_avg:
            st.pyplot(
                comparison_overview_distribution(
                    summary,
                    summary2,
                    display_name,
                    display_name2,
                    "average",
                )
            )
    if by_di.open:
        with by_di:
            st.pyplot(
                comparison_overview_distribution(
                    summary,
                    summary2,
                    display_name,
                    display_name2,
                    "discrimination",
                )
            )


def _render_question_segmentation(type_df, uploader_key):
    st.write(
        "Upload the original exam document (.docx) to segment questions by "
        "their categorized type and generate a reorganized download."
    )
    doc_file = st.file_uploader(
        "Upload Exam Document (.docx)",
        type=["docx"],
        key=uploader_key,
    )
    if doc_file is None:
        return

    try:
        from doc_parser import (
            extract_valid_q_ids,
            generate_segmented_report,
            parse_docx,
        )

        valid_q_ids = extract_valid_q_ids(type_df["question"].unique())
        doc_file.seek(0)
        questions_dict, _ = parse_docx(doc_file, valid_q_ids)

        mapped_count = len(questions_dict)
        total_target = len(valid_q_ids)
        if mapped_count == total_target:
            st.success(
                "Parsed document successfully! "
                f"All {mapped_count} categorized questions were matched."
            )
        elif mapped_count > 0:
            st.warning(
                f"Parsed document! Mapped {mapped_count} out of {total_target} "
                "categorized questions. The remaining "
                f"{total_target - mapped_count} questions will show matching "
                "failure placeholders."
            )
        else:
            st.error(
                f"Failed to match any of the {total_target} categorized questions. "
                "Please verify formatting. The generated document will contain "
                "placeholder warnings for all questions."
            )

        doc_file.seek(0)
        out_stream = generate_segmented_report(doc_file, questions_dict, type_df)
        st.download_button(
            label="Download Reorganized Exam Document (.docx)",
            data=out_stream,
            file_name="Reorganized_Exam_Report.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )
    except Exception as exc:
        st.error(f"An error occurred while parsing the document: {exc}")


@st.fragment
def _question_categorization_tabs(type_props, type_df, key_prefix):
    type_combined, type_list, type_report = st.tabs(
        ["Overview", "Question List", "Generate Report"],
        key=f"{key_prefix}-categorization-tabs",
        on_change="rerun",
    )
    if type_combined.open:
        with type_combined:
            st.dataframe(type_props)
            st.caption(
                "*\\*Can sum more than 100% if questions are in multiple categories*"
            )
    if type_list.open:
        with type_list:
            st.dataframe(type_df)
    if type_report.open:
        with type_report:
            _render_question_segmentation(
                type_df,
                uploader_key=f"{key_prefix}-exam-doc-uploader",
            )


@st.fragment
def _comparison_normalized_tabs(
    summary,
    summary2,
    display_name,
    display_name2,
    sc_df_long,
    sc_df_long2,
    combined_summary,
    key_prefix,
):
    consistency, bar, box, split_violin, raw_df = st.tabs(
        ["Consistency", "Bar", "Box", "Discrimination", "Data"],
        key=f"{key_prefix}-normalized-tabs",
        on_change="rerun",
    )
    if consistency.open:
        with consistency:
            col1, col2 = st.columns(2)
            with col1:
                st.plotly_chart(
                    plot_consistency(summary, display_name),
                    width="stretch",
                )
            with col2:
                st.plotly_chart(
                    plot_consistency(summary2, display_name2),
                    width="stretch",
                )
    if bar.open:
        with bar:
            st.pyplot(
                comparison_question_distribution(
                    summary,
                    summary2,
                    sc_df_long,
                    sc_df_long2,
                    display_name,
                    display_name2,
                    "bar",
                )
            )
    if box.open:
        with box:
            st.pyplot(
                comparison_question_distribution(
                    summary,
                    summary2,
                    sc_df_long,
                    sc_df_long2,
                    display_name,
                    display_name2,
                    "box",
                )
            )
    if split_violin.open:
        with split_violin:
            st.pyplot(
                comparison_question_distribution(
                    summary,
                    summary2,
                    sc_df_long,
                    sc_df_long2,
                    display_name,
                    display_name2,
                    "split-violin",
                )
            )
    if raw_df.open:
        with raw_df:
            st.dataframe(combined_summary)


def double_stats(
    summary,
    summary2,
    display_name,
    display_name2,
    sc_df_long,
    sc_df_long2,
    *,
    type_props=None,
    type_df=None,
    combined_summary=None,
    key_prefix="comparison",
):
    """Render an ordered comparison with independently rerunning lazy tabs."""

    if type_props is None or type_df is None or combined_summary is None:
        # Keep compatibility for callers outside the main app.
        import pandas as pd

        from helper import categorize_q_type

        type_cat, type_props, type_df = categorize_q_type(summary, summary2)
        combined_summary = pd.concat(
            [type_cat, summary, summary2],
            axis=1,
            keys=["type", display_name, display_name2],
        )

    st.subheader("Overview")
    _comparison_overview_tabs(
        summary,
        summary2,
        display_name,
        display_name2,
        key_prefix,
    )
    st.subheader("Question Categorization")
    _question_categorization_tabs(type_props, type_df, key_prefix)
    st.subheader("Normalized Statistics")
    _comparison_normalized_tabs(
        summary,
        summary2,
        display_name,
        display_name2,
        sc_df_long,
        sc_df_long2,
        combined_summary,
        key_prefix,
    )


def render_comparison(comparison: ComparisonAnalysis, *, key_prefix=None):
    lower = comparison.lower
    higher = comparison.higher
    key_prefix = key_prefix or f"comparison-{lower.name}-{higher.name}"
    double_stats(
        lower.summary,
        higher.summary,
        lower.display_name,
        higher.display_name,
        lower.long_scores,
        higher.long_scores,
        type_props=comparison.type_proportions,
        type_df=comparison.type_questions,
        combined_summary=comparison.normalized_summary,
        key_prefix=key_prefix,
    )


__all__ = [
    "double_stats",
    "exam_stats",
    "plot_consistency",
    "plot_q_breakdown",
    "render_comparison",
    "render_single_exam",
    "single_stats",
]

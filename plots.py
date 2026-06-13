import seaborn as sns
from matplotlib import pyplot as plt
import streamlit as st
import pandas as pd
from helper import categorize_q_type
from constants import *

def draw_diff_thre(ax):
	for thre in DIFF_BINS[1:-1]:
		ax.axvline(thre, color='red', linestyle='--', alpha=0.3)

def plot_q_breakdown(ax, df_long, type, **kwargs):
    draw_diff_thre(ax)
    match type:
        case 'bar':
            sns.barplot(
                df_long,
                y='Question',
                x='Score',
                hue='quality',
                dodge=False,
                errorbar='sd',
                capsize=0.2,
                palette=quality_cmap,
                ax=ax,
                **kwargs
            )
        case 'box':
            sns.boxplot(
                df_long,
                y='Question',
                x='Score',
                hue='quality',
                dodge=False,
                palette=quality_cmap,
                ax=ax,
                **kwargs
            )
        case 'split-violin':
            sns.violinplot(
				df_long,
				x='Score', y='Question',
				split=True, hue='Normalized Total Bin',
				ax=ax,
				palette=binary_cmap,
				width=1,
				inner=None,
				**kwargs
			)
            ax.set_xlim(-0.02, 1.02)
    return ax

def plot_exam_breakdown(ax, df, type, **kwargs):
    draw_diff_thre(ax)
    match type:
        case 'bar':
            sns.barplot(
                df,
                y='Exam',
                x='Normalized Total',
                hue='internal_consistency',
                errorbar='sd',
                capsize=0.2,
                dodge=False,
                palette=consistency_cmap,
                **kwargs
            )
        case 'box':
            sns.boxplot(
                df,
                y='Exam',
                x='Normalized Total',
                hue='internal_consistency',
                dodge=False,
                palette=consistency_cmap,
                **kwargs
            )
    return ax

def exam_stats(stats_df, total_sc_df):
    st.header("Exam Breakdown")

    st.subheader("Overview")
    by_mean, by_ca = st.tabs(['By average', 'By Cronbach\'s alpha'])

    with by_ca:
        fig, ax = plt.subplots()
        sns.histplot(stats_df, x='cronbach_alpha', bins=10, ax=ax, hue='internal_consistency', palette=consistency_cmap, multiple='stack')
        ax.set_title(f'Distribution of Cronbach\'s Alpha')
        st.pyplot(fig)
    with by_mean:
        fig, ax = plt.subplots()
        sns.histplot(stats_df, x='normalized_mean', hue='internal_consistency', palette=consistency_cmap, bins=10, multiple='stack')
        ax.set_title(f"Distribution of Average Normaliezd Exam Total")
        st.pyplot(fig)
    
    st.subheader('Exam-Level Statistics')
    exam_bar, exam_box, exam_data = st.tabs(['Bar', "Box", "Data"])
    with exam_data:
        st.dataframe(stats_df)
    with exam_bar:
        fig, ax = plt.subplots(figsize=(6, max(2, int(stats_df.shape[0]/5))))
        plot_exam_breakdown(ax, total_sc_df, 'bar')
        ax.set_title(f"Normalized Exam Averages (± SD)")
        ax.legend(loc='center left', bbox_to_anchor=(1, 0.5))
        st.pyplot(fig)
    with exam_box:
        fig, ax = plt.subplots(figsize=(6, max(2, int(stats_df.shape[0]/5))))
        plot_exam_breakdown(ax, total_sc_df, 'box')
        ax.set_title(f"Normalized Exam Averages (± SD)")
        ax.legend(loc='center left', bbox_to_anchor=(1, 0.5))
        st.pyplot(fig)

def single_stats(summary, display_name, sc_df_long):
    st.subheader("Overview")
    # aggregate
    by_avg, by_di = st.tabs(['Overview by average', "Overview by DI"])
    with by_avg:
        fig, ax = plt.subplots()
        sns.histplot(summary, x='avg', hue='quality', palette=quality_cmap, bins=10, multiple='stack')
        ax.set_title(f"Average Question Scores, {display_name}")
        st.pyplot(fig)
    with by_di:
        fig, ax = plt.subplots()
        sns.histplot(summary, x='discrimination_index', hue='quality', palette=quality_cmap, multiple='stack')
        ax.set_title(f"Discrimination Index, {display_name}")
        st.pyplot(fig)
    st.subheader("Question-Level Statistics")
    bar, box, split_violin, raw_df = st.tabs(["Bar", "Box", "Discrimination", "Data"])
    # bar plot distribution
    with bar:
        fig, ax = plt.subplots(figsize=(6, max(2, int(summary.shape[0]/5))))
        plot_q_breakdown(ax, sc_df_long, 'bar')
        ax.set_title(f"Question Averages, {display_name}")
        ax.legend(loc='center left', bbox_to_anchor=(1, 0.5))
        st.pyplot(fig)
    # box plot
    with box:
        fig, ax = plt.subplots(figsize=(6, max(2, int(summary.shape[0]/5))))
        plot_q_breakdown(ax, sc_df_long, 'box')
        ax.set_title(f"Question Averages, {display_name}")
        ax.legend(loc='center left', bbox_to_anchor=(1, 0.5))
        st.pyplot(fig)
    # violin plot discrimination
    with split_violin:
        fig, ax = plt.subplots(figsize=(6, max(2, int(summary.shape[0]/2))))
        sc_df_long['Normalized Total Bin'] = pd.qcut(sc_df_long['Normalized Total'], 2, labels=['Low', 'High'])
        plot_q_breakdown(ax, sc_df_long, 'split-violin')
        ax.set_title(f"Question Scores Relative to Total Scores, {display_name}")
        ax.legend(loc='center left', bbox_to_anchor=(1, 0.5))
        st.pyplot(fig)
    with raw_df:
        st.dataframe(summary)

def double_stats(summary, summary2, display_name, display_name2, sc_df_long, sc_df_long2):
    type_cat, type_props, type_df = categorize_q_type(summary, summary2)
    combined_summary = pd.concat([type_cat, summary, summary2], axis=1, keys=['type', display_name, display_name2])
    st.subheader("Overview")
    # aggregate
    by_avg, by_di = st.tabs(['By average', "By discrimination index"])
    with by_avg:
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 4), sharex=True, sharey=True)
        sns.histplot(summary, x='avg', hue='quality', palette=quality_cmap, bins=10, ax=ax1, multiple='stack', legend=False)
        ax1.set_title(display_name)
        sns.histplot(summary2, x='avg', hue='quality', palette=quality_cmap, bins=10, ax=ax2, multiple='stack')
        ax2.set_title(display_name2)
        fig.suptitle("Average Question Scores", fontsize=14)
        fig.tight_layout()
        st.pyplot(fig)
    with by_di:
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 4), sharex=True, sharey=True)
        sns.histplot(summary, x='discrimination_index', hue='quality', palette=quality_cmap, ax=ax1, multiple='stack', legend=False)
        ax1.set_title(display_name)
        sns.histplot(summary2, x='discrimination_index', hue='quality', palette=quality_cmap, ax=ax2, multiple='stack')
        ax2.set_title(display_name2)
        fig.suptitle("Discrimination Index", fontsize=14)
        fig.tight_layout()
        st.pyplot(fig)

    st.subheader("Question Categorization")
    type_combined, type_list, type_report = st.tabs(["Overview", "Question List", "Generate Report"])
    @st.fragment
    def generate_report():
        st.write("Upload the original exam document (.docx) to segment questions by their categorized type and generate a reorganized download.")
        doc_file = st.file_uploader("Upload Exam Document (.docx)", type=['docx'], key="exam_doc_uploader")
        if doc_file is not None:
            try:
                from doc_parser import extract_valid_q_ids, parse_docx, generate_segmented_report
                
                valid_q_ids = extract_valid_q_ids(type_df['question'].unique())
                
                doc_file.seek(0)
                questions_dict, intro_elements = parse_docx(doc_file, valid_q_ids)
                
                mapped_count = len(questions_dict)
                total_target = len(valid_q_ids)
                
                if mapped_count == total_target:
                    st.success(f"Parsed document successfully! All {mapped_count} categorized questions were matched.")
                elif mapped_count > 0:
                    st.warning(f"Parsed document! Mapped {mapped_count} out of {total_target} categorized questions. The remaining {total_target - mapped_count} questions will show matching failure placeholders.")
                else:
                    st.error(f"Failed to match any of the {total_target} categorized questions. Please verify formatting. The generated document will contain placeholder warnings for all questions.")
                
                doc_file.seek(0)
                out_stream = generate_segmented_report(doc_file, questions_dict, type_df)
                st.download_button(
                    label="Download Reorganized Exam Document (.docx)",
                    data=out_stream,
                    file_name="Reorganized_Exam_Report.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                )
            except Exception as e:
                st.error(f"An error occurred while parsing the document: {e}")
    with type_combined:
        st.dataframe(type_props)
        st.caption("*\*Can sum more than 100% if questions are in multiple categories*")
    with type_list:
        st.dataframe(type_df)
    with type_report:
        generate_report()

    max_rows = max(summary.shape[0], summary2.shape[0])

    st.subheader("Normalized Statistics")
    bar, box, split_violin, raw_df = st.tabs(["Bar", "Box", "Discrimination", "Data"])
    # bar plot distribution
    with bar:
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, max(2, int(max_rows/5))), sharey=True, sharex=True)
        plot_q_breakdown(ax1, sc_df_long, 'bar', legend=False)
        ax1.set_title(display_name)

        plot_q_breakdown(ax2, sc_df_long2, 'bar')
        ax2.set_title(display_name2)
        ax2.legend(loc='center left', bbox_to_anchor=(1, 0.5))
        
        fig.suptitle("Question Averages", fontsize=16)
        fig.tight_layout()
        st.pyplot(fig)
    with box:
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, max(2, int(max_rows/5))), sharey=True, sharex=True)
        plot_q_breakdown(ax1, sc_df_long, 'box', legend=False)
        ax1.set_title(display_name)

        plot_q_breakdown(ax2, sc_df_long2, 'box')
        ax2.set_title(display_name2)
        ax2.legend(loc='center left', bbox_to_anchor=(1, 0.5))
        
        fig.suptitle("Question Averages", fontsize=16)
        fig.tight_layout()
        st.pyplot(fig)
    # violin plot discrimination
    with split_violin:
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, max(2, int(max_rows/2))), sharey=True)
        plot_q_breakdown(ax1, sc_df_long, 'split-violin', legend=False)
        ax1.set_title(display_name)

        plot_q_breakdown(ax2, sc_df_long2, 'split-violin')
        ax2.set_title(display_name2)
        ax2.legend(loc='center left', bbox_to_anchor=(1, 0.5))
        
        fig.suptitle("Question Scores Relative to Total Scores", fontsize=16)
        fig.tight_layout()
        st.pyplot(fig)
    with raw_df:
        st.dataframe(combined_summary)
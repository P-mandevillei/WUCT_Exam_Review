from plots import plot_q_breakdown
from constants import binary_cmap
from constants import DIFF_BINS, consistency_cmap, quality_cmap, BINARY_LABELS
import numpy as np
import pandas as pd
import seaborn as sns
from matplotlib import pyplot as plt
import streamlit as st
from helper import normalize_total_sc, summarize_total_score, get_normalized_question_sc, make_total_sc_df, extract_question_cols, summarize_questions, categorize_q_type
from plots import draw_diff_thre, plot_exam_breakdown

st.title("WUCT Exam Review")

sc_files = st.file_uploader("Upload scores here. Make sure you downloaded the scores from GradeScope as csv files.", type='csv', accept_multiple_files=True)

if sc_files:
	names = [sc_file.name[:-4] for sc_file in sc_files]
	idx_map = {name: i for i, name in enumerate(names)}
	sc_df_list = []
	for sc_file in sc_files:
		sc_df = pd.read_csv(sc_file).dropna(axis=0, how='any')
		sc_df = normalize_total_sc(sc_df)
		sc_df_list.append(sc_df)

	# exam breakdown
	stats_list = []
	for sc_df, name in zip(sc_df_list, names):
		stats_list.append(summarize_total_score(sc_df, name))
	stats_df = pd.concat(stats_list, axis=0)
	total_sc_df = make_total_sc_df(sc_df_list, names)
	total_sc_df = total_sc_df.merge(
		stats_df.reset_index().rename(columns={'index': 'Exam'})[['Exam', 'internal_consistency']],
		on='Exam'
	)
	
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

	# question breakdown
	st.header("Question Breakdown")

	@st.fragment()
	def question_breakdown():
		def get_summary_and_long_df(name):
			df = sc_df_list[idx_map[name]]
			norm = get_normalized_question_sc(df)
			summ = summarize_questions(df, norm)
			norm['Name'] = df['Name']
			norm['Normalized Total'] = df['Normalized Total']
			long_df = norm.melt(
				id_vars=['Name', 'Normalized Total'],
				value_vars=summ.index,
				var_name='Question',
				value_name='Score'
			)
			long_df = long_df.merge(
				summ.reset_index().rename(columns={'index': 'Question'})[['Question', 'quality']],
				on='Question'
			)
			return summ, long_df

		selected_name = st.selectbox(label='Select a scores set to view analysis. If comparing, this is the lower division.', options=names)
		compare_name = st.selectbox(
			label='Select a second scores set to compare (optional). This is the higher division.',
			options=[None] + [n for n in names if n != selected_name],
			format_func=lambda x: "None" if x is None else x.replace('_', ' ')
		)

		display_name = selected_name.replace('_', ' ')
		summary, sc_df_long = get_summary_and_long_df(selected_name)

		if compare_name is not None:
			display_name2 = compare_name.replace('_', ' ')
			summary2, sc_df_long2 = get_summary_and_long_df(compare_name)
			sc_df_long['Normalized Total Bin'] = pd.qcut(sc_df_long['Normalized Total'], 2, labels=BINARY_LABELS)
			sc_df_long2['Normalized Total Bin'] = pd.qcut(sc_df_long2['Normalized Total'], 2, labels=BINARY_LABELS)
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
			type_combined, type_list = st.tabs(["Overview", "Question List"])
			with type_combined:
				st.dataframe(type_props)
				st.markdown("*\*Can sum more than 100% if questions are in multiple categories*")
			with type_list:
				st.dataframe(type_df)

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
		else:
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
	question_breakdown()
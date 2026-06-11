from constants import DIFF_BINS
import numpy as np
import pandas as pd
import seaborn as sns
from matplotlib import pyplot as plt
import matplotlib.cm as cm
import streamlit as st
from helper import normalize_total_sc, summarize_total_score, get_normalized_question_sc, make_total_sc_df, extract_question_cols, summarize_questions, draw_diff_thre, categorize_q_type
colors = plt.rcParams['axes.prop_cycle'].by_key()['color']
quality_cmap = {'good': colors[2], 'ok': colors[0], 'poor': colors[1], 'need review': colors[3]}
consistency_cmap = {'reliable': colors[2], 'acceptable': colors[1], 'unreliable': colors[3]}

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
	st.dataframe(stats_df)

	fig, ax = plt.subplots()
	sns.histplot(stats_df, x='cronbach_alpha', bins=10, ax=ax, hue='internal_consistency', palette=consistency_cmap)
	ax.set_title(f'Distribution of Cronbach\'s Alpha')
	st.pyplot(fig)
	
	st.subheader('Normalized Statistics')

	fig, ax = plt.subplots(figsize=(6, max(2, int(stats_df.shape[0]/2.5))))
	sns.violinplot(
		total_sc_df,
		x='Normalized Total', y='Exam',
		hue='internal_consistency', palette=consistency_cmap,
		ax=ax,
		width=0.9,
		inner="box", 
		inner_kws={"box_width": 4}
	)
	ax.set_xlim(-0.02, 1.02)
	ax.set_title(f"Normalized Exam Total Scores Distribution")
	ax.legend(loc='center left', bbox_to_anchor=(1, 0.5))
	st.pyplot(fig)

	fig, ax = plt.subplots(figsize=(6, max(2, int(stats_df.shape[0]/5))))
	sns.barplot(
		total_sc_df,
		y='Exam',
		x='Normalized Total',
		hue='internal_consistency',
		errorbar='sd',
		capsize=0.2,
		palette=consistency_cmap
	)
	ax.tick_params(axis='x', rotation=90)
	ax.set_title(f"Normalized Exam Averages (± SD)")
	ax.legend(loc='center left', bbox_to_anchor=(1, 0.5))
	st.pyplot(fig)

	fig, ax = plt.subplots()
	sns.histplot(stats_df, x='normalized_mean', hue='internal_consistency', palette=consistency_cmap, bins=10)
	ax.set_title(f"Distribution of Average Normaliezd Exam Total")
	st.pyplot(fig)

	# question breakdown
	st.header("Question Breakdown")
	st.subheader("Normalized Statistics")

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
			type_cat, type_props, type_df = categorize_q_type(summary, summary2)
			combined_summary = pd.concat([type_cat, summary, summary2], axis=1, keys=['type', display_name, display_name2])
			st.dataframe(combined_summary)
			st.dataframe(type_props)
			st.markdown("*\*Can sum more than 100% if questions are in multiple categories*")
			st.dataframe(type_df)

			max_rows = max(summary.shape[0], summary2.shape[0])

			# bar plot distribution
			fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, max(2, int(max_rows/5))), sharey=True, sharex=True)
			draw_diff_thre(ax1)
			sns.barplot(
				sc_df_long,
				y='Question',
				x='Score',
				hue='quality',
				dodge=False,
				errorbar='sd',
				capsize=0.2,
				palette=quality_cmap,
				ax=ax1,
				legend=False
			)
			ax1.set_title(display_name)

			draw_diff_thre(ax2)
			sns.barplot(
				sc_df_long2,
				y='Question',
				x='Score',
				hue='quality',
				dodge=False,
				errorbar='sd',
				capsize=0.2,
				palette=quality_cmap,
				ax=ax2
			)
			ax2.set_title(display_name2)
			ax2.legend(loc='center left', bbox_to_anchor=(1, 0.5))
			
			fig.suptitle("Question Averages", fontsize=16)
			fig.tight_layout()
			st.pyplot(fig)

			# violin plot discrimination
			sc_df_long['Normalized Total Bin'] = pd.qcut(sc_df_long['Normalized Total'], 2, labels=['Low', 'High'])
			sc_df_long2['Normalized Total Bin'] = pd.qcut(sc_df_long2['Normalized Total'], 2, labels=['Low', 'High'])

			fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, max(2, int(max_rows/2))), sharey=True)
			sns.violinplot(
				sc_df_long,
				x='Score', y='Question',
				split=True, hue='Normalized Total Bin',
				ax=ax1,
				palette={'Low': '#1E88E5', 'High': '#FF0D57'},
				width=1,
				inner="box", 
				inner_kws={"box_width": 3.5},
				legend=False
			)
			draw_diff_thre(ax1)
			ax1.set_xlim(-0.02, 1.02)
			ax1.set_title(display_name)

			sns.violinplot(
				sc_df_long2,
				x='Score', y='Question',
				split=True, hue='Normalized Total Bin',
				ax=ax2,
				palette={'Low': '#1E88E5', 'High': '#FF0D57'},
				width=1,
				inner="box", 
				inner_kws={"box_width": 3.5}
			)
			draw_diff_thre(ax2)
			ax2.set_xlim(-0.02, 1.02)
			ax2.set_title(display_name2)
			ax2.legend(loc='center left', bbox_to_anchor=(1, 0.5))
			
			fig.suptitle("Question Scores Relative to Total Scores", fontsize=16)
			fig.tight_layout()
			st.pyplot(fig)

			# aggregate
			fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 4), sharex=True, sharey=True)
			sns.histplot(summary, x='avg', hue='quality', palette=quality_cmap, bins=10, ax=ax1)
			ax1.set_title(display_name)
			sns.histplot(summary2, x='avg', hue='quality', palette=quality_cmap, bins=10, ax=ax2)
			ax2.set_title(display_name2)
			fig.suptitle("Average Question Scores", fontsize=14)
			fig.tight_layout()
			st.pyplot(fig)

			fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 4), sharex=True, sharey=True)
			sns.histplot(summary, x='discrimination_index', hue='quality', palette=quality_cmap, ax=ax1)
			ax1.set_title(display_name)
			sns.histplot(summary2, x='discrimination_index', hue='quality', palette=quality_cmap, ax=ax2)
			ax2.set_title(display_name2)
			fig.suptitle("Discrimination Index", fontsize=14)
			fig.tight_layout()
			st.pyplot(fig)

		else:
			st.dataframe(summary)

			# bar plot distribution
			fig, ax = plt.subplots(figsize=(6, max(2, int(summary.shape[0]/5))))
			draw_diff_thre(ax)
			sns.barplot(
				sc_df_long,
				y='Question',
				x='Score',
				hue='quality',
				dodge=False,
				errorbar='sd',
				capsize=0.2,
				palette=quality_cmap
			)
			ax.set_title(f"Question Averages, {display_name}")
			ax.legend(loc='center left', bbox_to_anchor=(1, 0.5))
			st.pyplot(fig)

			# violin plot discrimination
			fig, ax = plt.subplots(figsize=(6, max(2, int(summary.shape[0]/2))))
			sc_df_long['Normalized Total Bin'] = pd.qcut(sc_df_long['Normalized Total'], 2, labels=['Low', 'High'])
			sns.violinplot(
				sc_df_long,
				x='Score', y='Question',
				split=True, hue='Normalized Total Bin',
				ax=ax,
				palette={'Low': '#1E88E5', 'High': '#FF0D57'},
				width=1,
				inner="box", 
				inner_kws={"box_width": 3.5}
			)
			draw_diff_thre(ax)
			ax.set_xlim(-0.02, 1.02)
			ax.set_title(f"Question Scores Relative to Total Scores, {display_name}")
			ax.legend(loc='center left', bbox_to_anchor=(1, 0.5))
			st.pyplot(fig)

			# aggregate
			fig, ax = plt.subplots()
			sns.histplot(summary, x='avg', hue='quality', palette=quality_cmap, bins=10)
			ax.set_title(f"Average Question Scores, {display_name}")
			st.pyplot(fig)
			fig, ax = plt.subplots()
			sns.histplot(summary, x='discrimination_index', hue='quality', palette=quality_cmap)
			ax.set_title(f"Discrimination Index, {display_name}")
			st.pyplot(fig)
	question_breakdown()
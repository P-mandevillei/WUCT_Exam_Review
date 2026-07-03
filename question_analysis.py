from helper import calc_citc
from helper import calc_cronbach_alpha_if_item_deleted
from plots import plot_q_breakdown
from constants import binary_cmap
from constants import DIFF_BINS, consistency_cmap, quality_cmap, BINARY_LABELS
import numpy as np
import pandas as pd
import seaborn as sns
from matplotlib import pyplot as plt
import streamlit as st
from helper import normalize_total_sc, summarize_total_score, make_total_sc_df, get_summary_and_long_df
from plots import exam_stats, single_stats, double_stats

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
	exam_stats(stats_df, total_sc_df)

	# question breakdown
	st.header("Question Breakdown")

	@st.fragment()
	def question_breakdown():
		selected_name = st.selectbox(label='Select a scores set to view analysis. If comparing, this is the lower division.', options=names)
		compare_name = st.selectbox(
			label='Select a second scores set to compare (optional). This is the higher division.',
			options=[None] + [n for n in names if n != selected_name],
			format_func=lambda x: "None" if x is None else x.replace('_', ' ')
		)

		display_name = selected_name.replace('_', ' ')
		ori_df1 = sc_df_list[idx_map[selected_name]]
		summary, sc_df_long = get_summary_and_long_df(ori_df1)

		if compare_name is not None:
			display_name2 = compare_name.replace('_', ' ')
			ori_df2 = sc_df_list[idx_map[compare_name]]
			summary2, sc_df_long2 = get_summary_and_long_df(ori_df2)
			combined_ori_df = pd.concat([ori_df1, ori_df2], axis=0)
			combined_summary, combined_sc_df_long = get_summary_and_long_df(combined_ori_df)

			display_double, display_single = st.tabs(['Individual Stats', "Combined Stats"])
			with display_double:
				double_stats(summary, summary2, display_name, display_name2, sc_df_long, sc_df_long2)
			with display_single:
				single_stats(combined_summary, f"Combined {display_name} & {display_name2}", combined_sc_df_long)
		else:
			single_stats(summary, display_name, sc_df_long)
	question_breakdown()
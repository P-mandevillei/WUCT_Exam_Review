import numpy as np
import pandas as pd
import seaborn as sns
from matplotlib import pyplot as plt
import matplotlib.cm as cm
import streamlit as st
from helper import normalize_total_sc, summarize_total_score, get_normalized_question_sc, make_total_sc_df, extract_question_cols, summarize_questions
colors = plt.rcParams['axes.prop_cycle'].by_key()['color']
quality_cmap = {'good': colors[2], 'ok': colors[0], 'poor': colors[1], 'need review': colors[3]}
validity_cmap = {'reliable': colors[2], 'acceptable': colors[1], 'unreliable': colors[3]}

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
		stats_df.reset_index().rename(columns={'index': 'Exam'})[['Exam', 'internal_validity']],
		on='Exam'
	)
	
	st.header("Exam Breakdown")
	st.dataframe(stats_df)

	fig, ax = plt.subplots()
	sns.histplot(stats_df, x='cronbach_alpha', bins=10, ax=ax, hue='internal_validity', palette=validity_cmap)
	ax.set_title(f'Distribution of Cronbach\'s Alpha')
	st.pyplot(fig)
	
	st.subheader('Normalized Statistics')

	fig, ax = plt.subplots(figsize=(6, int(stats_df.shape[0]/2.5)))
	sns.violinplot(
		total_sc_df,
		x='Normalized Total', y='Exam',
		hue='internal_validity', palette=validity_cmap, ax=ax
	)
	ax.set_title(f"Normalized Exam Total Scores Distribution")
	st.pyplot(fig)

	plot_df = stats_df.copy()
	plot_df['cmap'] = plot_df['internal_validity'].apply(lambda x: validity_cmap[x])
	st.bar_chart(plot_df, y='normalized_mean', color='cmap')

	fig, ax = plt.subplots()
	sns.histplot(stats_df, x='normalized_mean', hue='internal_validity', palette=validity_cmap, bins=10)
	ax.set_title(f"Distribution of Average Normaliezd Exam Total")
	st.pyplot(fig)

	# question breakdown
	st.header("Question Breakdown")
	st.subheader("Normalized Statistics")

	@st.fragment()
	def question_breakdown():
		selected_name = st.selectbox(label='Select a scores set to view analysis.', options=names)
		display_name = selected_name.replace('_', ' ')
		selected_sc_df = sc_df_list[idx_map[selected_name]]
		norm_df = get_normalized_question_sc(selected_sc_df)
		summary = summarize_questions(selected_sc_df, norm_df)
		norm_df['Name'] = selected_sc_df['Name']
		norm_df['Normalized Total'] = selected_sc_df['Normalized Total']
		sc_df_long = norm_df.melt(
		    id_vars=['Name', 'Normalized Total'],
			value_vars=summary.index,
			var_name='Question',
			value_name='Score'
		)
		sc_df_long = sc_df_long.merge(
			summary.reset_index().rename(columns={'index': 'Question'})[['Question', 'quality']],
			on='Question'
		)
		
		st.dataframe(summary)
	
		fig, ax = plt.subplots(figsize=(6, int(summary.shape[0]/2.5)))
		sns.violinplot(
			sc_df_long,
			x='Score', y='Question', hue='quality', 
			palette=quality_cmap, ax=ax
		)
		ax.set_title(f"Question Scores Distribution, {display_name}")
		st.pyplot(fig)
	
		plot_df = summary.copy()
		plot_df['cmap'] = plot_df['quality'].apply(lambda x: quality_cmap[x])
		st.bar_chart(plot_df, y='avg', color='cmap')
		
		fig, ax = plt.subplots()
		sns.histplot(summary, x='avg', hue='quality', palette=quality_cmap, bins=10)
		ax.set_title(f"Average Question Scores, {display_name}")
		st.pyplot(fig)
		
		fig, ax = plt.subplots()
		sns.histplot(summary, x='discrimination_index', hue='quality', palette=quality_cmap)
		ax.set_title(f"Discrimination Index, {display_name}")
		st.pyplot(fig)
	
		fig, ax = plt.subplots(figsize=(6, int(summary.shape[0]/2.5)))
		sc_df_long['Normalized Total Bin'] = pd.qcut(sc_df_long['Normalized Total'], 2, labels=['Low', 'High'])
		sns.violinplot(
			sc_df_long,
			x='Score', y='Question',
			split=True, hue='Normalized Total Bin',
			ax=ax, inner=None,
			palette={'Low': '#1E88E5', 'High': '#FF0D57'}
		)
		ax.set_title(f"Question Scores Relative to Total Scores, {display_name}")
		st.pyplot(fig)
	question_breakdown()
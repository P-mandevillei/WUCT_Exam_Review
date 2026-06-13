import numpy as np
import pandas as pd
from constants import *

def normalize_total_sc(df):
	full_sc = 0
	match = None
	for col in extract_question_cols(df):
		match = col_reg.search(col)
		if (match):
			full_sc += float(match.group(1))
	df['Normalized Total'] = df['Total Score']/full_sc
	return df

def calc_cronbach_alpha(df):
	var_list = []
	for col in df.columns:
		if "Question" in col:
			var_list.append(df[col].std()**2)
	n = len(var_list)
	if n <= 1:
		return 0
	sum_var = np.sum(var_list)
	total_sc_var = df['Total Score'].std() ** 2
	ca = n/(n-1)*(1 - sum_var/total_sc_var)
	return ca

def summarize_total_score(df, name):
	summary = df['Total Score'].describe().to_frame()
	summary.columns = [name]
	summary = summary.transpose()
	summary['cronbach_alpha'] = calc_cronbach_alpha(df)
	summary['internal_consistency'] = pd.cut(summary['cronbach_alpha'], bins=CA_BINS, labels=CA_LABELS, right=True, include_lowest=True)
	normalized = df['Normalized Total']
	summary['normalized_mean'] = normalized.mean()
	summary['normalized_std'] = normalized.std()
	return summary

def make_total_sc_df(df_list, names):
	total_sc_df_list = []
	for df, name in zip(df_list, names):
		total_sc_df = df[['Normalized Total']].copy()
		total_sc_df['Exam'] = name
		total_sc_df_list.append(total_sc_df)
	return pd.concat(total_sc_df_list, axis=0)

def extract_question_cols(df):
	return [col for col in df.columns if 'Question' in col]

def get_normalized_question_sc(sc_df):
	norm_df_list = []
	for col in sc_df.columns:
		if "Question" in col:
			match = col_reg.search(col)
			if (match):
				full_sc = float(match.group(1))
				norm_scores = sc_df[col].apply(lambda x: x/full_sc)
				norm_df_list.append(norm_scores)
	norm_df = pd.concat(norm_df_list, axis=1)
	return norm_df

def summarize_questions(sc_df, norm_df):
	scores = sc_df['Total Score'].to_numpy()
	cutoffs = [np.quantile(scores, GROUP_QUANTILE), np.quantile(scores, 1-GROUP_QUANTILE)]
	
	high_sc_grp_mask = sc_df['Total Score'] >= cutoffs[1]
	low_sc_grp_mask = sc_df['Total Score'] <= cutoffs[0]
	summary_list = []
	for col in norm_df.columns:
		q = norm_df[col]
		hi_avg = q[high_sc_grp_mask].mean()
		lo_avg = q[low_sc_grp_mask].mean()
		di = np.round(hi_avg - lo_avg, 2)
		summary = pd.DataFrame({
			'avg': q.mean(),
			'std': q.std(),
			'high_group_avg': hi_avg,
			'low_group_avg': lo_avg,
			'discrimination_index': di,
		}, index=[col])
		summary['quality'] = pd.cut(summary['discrimination_index'], bins=DI_BINS, labels=DI_LABELS, right=True, include_lowest=True)
		summary['difficulty'] = pd.cut(summary['avg'], bins=DIFF_BINS, labels=DIFF_LABELS, right=True, include_lowest=True)
		summary_list.append(summary)
	summary_df = pd.concat(summary_list, axis=0)
	return summary_df

def categorize_q_type(low_summ, high_summ):
	# type 5: confusing questions
	type5 = (
		(low_summ['difficulty'] == DIFF_EASY) & 
		(high_summ['difficulty'] == DIFF_HARD)
	)
	# type 4: too hard questions
	type4 = (
		(high_summ['difficulty'] == DIFF_HARD) &
		((high_summ['quality'] == DIS_POOR) | (high_summ['quality'] == DIS_NEED_REVIEW))
	)
	# type 1: easy for both divisions
	type1 = (
		(low_summ['difficulty'] == DIFF_EASY) & 
		(high_summ['difficulty'] == DIFF_EASY)
	)
	# type 2: good discrimination for lower division
	type2 = (
		(low_summ['quality'] == DIS_GOOD) & (~type4)
	)
	# type 3: good discrimination for higher division
	type3 = high_summ['quality'] == DIS_GOOD
	new_df = low_summ.copy()
	new_df['type1'] = type1
	new_df['type2'] = type2
	new_df['type3'] = type3
	new_df['type4'] = type4
	new_df['type5'] = type5
	new_df = new_df[['type1', 'type2', 'type3', 'type4', 'type5']]
	type_df = new_df.reset_index().rename(columns={"index": "question"}).melt(id_vars = 'question', value_vars = ['type1', 'type2', 'type3', 'type4', 'type5'], var_name = 'type', value_name='true')
	type_df = type_df[type_df['true'].astype(bool)][['type', 'question']].reset_index(drop=True)
	new_df['type'] = new_df.apply(lambda series: ', '.join([col for col in series.index if series[col]]), axis=1)

	n = low_summ.shape[0]
	type1_prop = type1.sum()/n*100
	type2_prop = type2.sum()/n*100
	type3_prop = type3.sum()/n*100
	type4_prop = type4.sum()/n*100
	type5_prop = type5.sum()/n*100
	uncat_prop = (~(type1 | type2 | type3 | type4 | type5)).sum()/n*100
	type_prop_df = pd.DataFrame({
		'type1 - Easy for Both': type1_prop, 
		'type2 - Lower Division Discrimination': type2_prop, 
		'type3 - Higher Division Discrimination': type3_prop, 
		'type4 - Too Hard': type4_prop,
		'type5 - Confusing (Easy for LD, Hard for HD)': type5_prop,
		'uncategorized - Filler Questions': uncat_prop
	}, index=['Percent* (%)']).transpose()

	return new_df[['type']], type_prop_df, type_df

def get_summary_and_long_df(df):
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
	long_df['Normalized Total Bin'] = pd.qcut(long_df['Normalized Total'], 2, labels=BINARY_LABELS)
	return summ, long_df
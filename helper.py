import numpy as np
import pandas as pd
import re
GROUP_QUANTILE = 0.27
DI_GOOD = 0.6
DI_OK = 0.3
DI_POOR = 0
CA_RELIABLE = 0.9
CA_ACCEPTABLE = 0.7
col_reg = re.compile(r'\((\d+.\d+)\s+pts\)')

def normalize_total_sc(df):
	full_sc = 0
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
	sum_var = np.sum(var_list)
	total_sc_var = df['Total Score'].std() ** 2
	n = df.shape[0]
	ca = n/(n-1)*(1 - sum_var/total_sc_var)
	return ca

def ca_rating(ca):
	if ca > CA_RELIABLE:
		return 'reliable'
	elif ca > CA_ACCEPTABLE:
		return 'acceptable'
	else:
		return 'unreliable'

def summarize_total_score(df, name):
	summary = df['Total Score'].describe().to_frame()
	summary.columns = [name]
	summary = summary.transpose()
	summary['cronbach_alpha'] = calc_cronbach_alpha(df)
	summary['internal_validity'] = summary['cronbach_alpha'].apply(ca_rating)
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

def di_rating(di):
	if di > DI_GOOD:
		return 'good'
	elif di > DI_OK:
		return 'ok'
	elif di > DI_POOR:
		return 'poor'
	else:
		return 'need review'

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
		summary['quality'] = summary['discrimination_index'].apply(di_rating)
		summary_list.append(summary)
	summary_df = pd.concat(summary_list, axis=0)
	return summary_df
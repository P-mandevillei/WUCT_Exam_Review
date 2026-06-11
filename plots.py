import seaborn as sns
from matplotlib import pyplot as plt
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
"""Pure figure factories shared by Streamlit and static report output."""

import matplotlib

matplotlib.use("Agg")

import pandas as pd
import plotly.express as px
import seaborn as sns
from matplotlib import pyplot as plt

from constants import DIFF_BINS, binary_cmap, consistency_cmap, quality_cmap


def draw_diff_thre(ax):
    for threshold in DIFF_BINS[1:-1]:
        ax.axvline(threshold, color="red", linestyle="--", alpha=0.3)


def plot_q_breakdown(ax, df_long, plot_type, **kwargs):
    draw_diff_thre(ax)
    match plot_type:
        case "bar":
            sns.barplot(
                df_long,
                y="Question",
                x="Score",
                hue="quality",
                dodge=False,
                errorbar="sd",
                capsize=0.2,
                palette=quality_cmap,
                ax=ax,
                **kwargs,
            )
        case "box":
            sns.boxplot(
                df_long,
                y="Question",
                x="Score",
                hue="quality",
                dodge=False,
                palette=quality_cmap,
                ax=ax,
                **kwargs,
            )
        case "split-violin":
            sns.violinplot(
                df_long,
                x="Score",
                y="Question",
                split=True,
                hue="Normalized Total Bin",
                ax=ax,
                palette=binary_cmap,
                width=1,
                inner=None,
                **kwargs,
            )
            ax.set_xlim(-0.02, 1.02)
    return ax


def plot_exam_breakdown(ax, df, plot_type, **kwargs):
    draw_diff_thre(ax)
    match plot_type:
        case "bar":
            sns.barplot(
                df,
                y="Exam",
                x="Normalized Total",
                hue="internal_consistency",
                errorbar="sd",
                capsize=0.2,
                dodge=False,
                palette=consistency_cmap,
                ax=ax,
                **kwargs,
            )
        case "box":
            sns.boxplot(
                df,
                y="Exam",
                x="Normalized Total",
                hue="internal_consistency",
                dodge=False,
                palette=consistency_cmap,
                ax=ax,
                **kwargs,
            )
    return ax


def plot_consistency(summary, display_name):
    df = summary.reset_index().rename(columns={"index": "Question"})
    fig = px.scatter(
        df,
        x="correlation",
        y="alpha_increase",
        color="quality",
        color_discrete_map=quality_cmap,
        hover_name="Question",
        hover_data={
            "correlation": ":.3f",
            "alpha_increase": ":.4f",
            "avg": ":.2f",
            "discrimination_index": ":.3f",
            "quality": True,
        },
        title=f"Reliability Diagnostic Map, {display_name}",
        labels={
            "correlation": "Item-Total Correlation",
            "alpha_increase": "Change in Alpha if Deleted",
            "quality": "Question Quality",
        },
    )
    fig.add_hline(y=0, line_dash="dash", line_color="gray")
    fig.add_vline(x=0.3, line_dash="dash", line_color="gray")
    fig.update_layout(
        xaxis_title="Item-Total Correlation",
        yaxis_title="Change in Alpha if Deleted",
        legend_title="Question Quality",
        hovermode="closest",
    )
    return fig


def exam_average_distribution(stats_df):
    fig, ax = plt.subplots()
    sns.histplot(
        stats_df,
        x="normalized_mean",
        hue="internal_consistency",
        palette=consistency_cmap,
        bins=10,
        multiple="stack",
        ax=ax,
    )
    ax.set_title("Distribution of Average Normalized Exam Total")
    return fig


def exam_consistency_distribution(stats_df):
    fig, ax = plt.subplots()
    sns.histplot(
        stats_df,
        x="cronbach_alpha",
        bins=10,
        ax=ax,
        hue="internal_consistency",
        palette=consistency_cmap,
        multiple="stack",
    )
    ax.set_title("Distribution of Cronbach's Alpha")
    return fig


def exam_question_distribution(stats_df, total_sc_df, plot_type):
    fig, ax = plt.subplots(figsize=(6, max(2, int(stats_df.shape[0] / 5))))
    plot_exam_breakdown(ax, total_sc_df, plot_type)
    ax.set_title("Normalized Exam Averages (± SD)")
    ax.legend(loc="center left", bbox_to_anchor=(1, 0.5))
    return fig


def single_average_distribution(summary, display_name):
    fig, ax = plt.subplots()
    sns.histplot(
        summary,
        x="avg",
        hue="quality",
        palette=quality_cmap,
        bins=10,
        multiple="stack",
        ax=ax,
    )
    ax.set_title(f"Average Question Scores, {display_name}")
    return fig


def single_discrimination_distribution(summary, display_name):
    fig, ax = plt.subplots()
    sns.histplot(
        summary,
        x="discrimination_index",
        hue="quality",
        palette=quality_cmap,
        multiple="stack",
        ax=ax,
    )
    ax.set_title(f"Discrimination Index, {display_name}")
    return fig


def single_question_distribution(summary, sc_df_long, display_name, plot_type):
    height_divisor = 2 if plot_type == "split-violin" else 5
    fig, ax = plt.subplots(figsize=(6, max(2, int(summary.shape[0] / height_divisor))))

    plot_df = sc_df_long
    if plot_type == "split-violin":
        # Preserve the original median-bin calculation without mutating shared data.
        plot_df = sc_df_long.copy()
        plot_df["Normalized Total Bin"] = pd.qcut(
            plot_df["Normalized Total"],
            2,
            labels=["Low", "High"],
        )

    plot_q_breakdown(ax, plot_df, plot_type)
    if plot_type == "split-violin":
        ax.set_title(f"Question Scores Relative to Total Scores, {display_name}")
    else:
        ax.set_title(f"Question Averages, {display_name}")
    ax.legend(loc="center left", bbox_to_anchor=(1, 0.5))
    return fig


def comparison_overview_distribution(
    summary,
    summary2,
    display_name,
    display_name2,
    metric,
):
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 4), sharex=True, sharey=True)
    if metric == "average":
        x = "avg"
        title = "Average Question Scores"
        bins = 10
    else:
        x = "discrimination_index"
        title = "Discrimination Index"
        bins = None

    first_kwargs = {
        "data": summary,
        "x": x,
        "hue": "quality",
        "palette": quality_cmap,
        "ax": ax1,
        "multiple": "stack",
        "legend": False,
    }
    second_kwargs = {
        "data": summary2,
        "x": x,
        "hue": "quality",
        "palette": quality_cmap,
        "ax": ax2,
        "multiple": "stack",
    }
    if bins is not None:
        first_kwargs["bins"] = bins
        second_kwargs["bins"] = bins

    sns.histplot(**first_kwargs)
    ax1.set_title(display_name)
    sns.histplot(**second_kwargs)
    ax2.set_title(display_name2)
    fig.suptitle(title, fontsize=14)
    fig.tight_layout()
    return fig


def comparison_question_distribution(
    summary,
    summary2,
    sc_df_long,
    sc_df_long2,
    display_name,
    display_name2,
    plot_type,
):
    max_rows = max(summary.shape[0], summary2.shape[0])
    height_divisor = 2 if plot_type == "split-violin" else 5
    subplot_kwargs = {
        "figsize": (12, max(2, int(max_rows / height_divisor))),
        "sharey": True,
    }
    if plot_type != "split-violin":
        subplot_kwargs["sharex"] = True
    fig, (ax1, ax2) = plt.subplots(1, 2, **subplot_kwargs)

    plot_q_breakdown(ax1, sc_df_long, plot_type, legend=False)
    ax1.set_title(display_name)
    plot_q_breakdown(ax2, sc_df_long2, plot_type)
    ax2.set_title(display_name2)
    ax2.legend(loc="center left", bbox_to_anchor=(1, 0.5))

    if plot_type == "split-violin":
        title = "Question Scores Relative to Total Scores"
    else:
        title = "Question Averages"
    fig.suptitle(title, fontsize=16)
    fig.tight_layout()
    return fig

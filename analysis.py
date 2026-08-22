"""Reusable analysis models shared by the Streamlit and report renderers."""

from dataclasses import dataclass

import pandas as pd

from helper import (
    categorize_q_type,
    get_summary_and_long_df,
    make_total_sc_df,
    summarize_total_score,
)


@dataclass
class ExamAnalysis:
    """Calculated data for one uploaded exam."""

    name: str
    display_name: str
    scores: pd.DataFrame
    summary: pd.DataFrame
    long_scores: pd.DataFrame


@dataclass
class ComparisonAnalysis:
    """Calculated data and categorization tables for an ordered exam pair."""

    lower: ExamAnalysis
    higher: ExamAnalysis
    combined: ExamAnalysis
    type_categories: pd.DataFrame
    type_proportions: pd.DataFrame
    type_questions: pd.DataFrame
    normalized_summary: pd.DataFrame


@dataclass
class ReportModel:
    """All calculated data needed by either presentation layer."""

    exams: list[ExamAnalysis]
    stats: pd.DataFrame
    total_scores: pd.DataFrame

    @property
    def names(self) -> list[str]:
        return [exam.name for exam in self.exams]

    def exam(self, name: str) -> ExamAnalysis:
        for exam in self.exams:
            if exam.name == name:
                return exam
        raise KeyError(f"Unknown exam: {name}")

    def compare(self, lower_name: str, higher_name: str) -> ComparisonAnalysis:
        lower = self.exam(lower_name)
        higher = self.exam(higher_name)

        combined_scores = pd.concat([lower.scores, higher.scores], axis=0)
        combined_summary, combined_long_scores = get_summary_and_long_df(combined_scores)
        combined_display_name = f"Combined {lower.display_name} & {higher.display_name}"
        combined = ExamAnalysis(
            name=f"combined:{lower.name}:{higher.name}",
            display_name=combined_display_name,
            scores=combined_scores,
            summary=combined_summary,
            long_scores=combined_long_scores,
        )

        type_categories, type_proportions, type_questions = categorize_q_type(
            lower.summary,
            higher.summary,
        )
        normalized_summary = pd.concat(
            [type_categories, lower.summary, higher.summary],
            axis=1,
            keys=["type", lower.display_name, higher.display_name],
        )

        return ComparisonAnalysis(
            lower=lower,
            higher=higher,
            combined=combined,
            type_categories=type_categories,
            type_proportions=type_proportions,
            type_questions=type_questions,
            normalized_summary=normalized_summary,
        )


def build_report_model(score_frames: list[pd.DataFrame], names: list[str]) -> ReportModel:
    """Calculate the common report model from already normalized score frames."""

    if len(score_frames) != len(names):
        raise ValueError("Each score frame must have a corresponding name.")
    if len(set(names)) != len(names):
        raise ValueError("Uploaded score files must have unique filenames.")

    exams = []
    stats = []
    for score_frame, name in zip(score_frames, names):
        summary, long_scores = get_summary_and_long_df(score_frame)
        exams.append(
            ExamAnalysis(
                name=name,
                display_name=name.replace("_", " "),
                scores=score_frame,
                summary=summary,
                long_scores=long_scores,
            )
        )
        stats.append(summarize_total_score(score_frame, name))

    stats_df = pd.concat(stats, axis=0)
    total_scores = make_total_sc_df(score_frames, names)
    total_scores = total_scores.merge(
        stats_df.reset_index()
        .rename(columns={"index": "Exam"})[["Exam", "internal_consistency"]],
        on="Exam",
    )

    return ReportModel(exams=exams, stats=stats_df, total_scores=total_scores)

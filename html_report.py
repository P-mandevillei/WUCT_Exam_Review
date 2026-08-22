"""Generate a self-contained, interactive HTML report from a ReportModel."""

import base64
import html
from collections.abc import Callable
from datetime import datetime
from io import BytesIO

import pandas as pd
import plotly.io as pio
from matplotlib import pyplot as plt
from plotly.offline import get_plotlyjs

from analysis import ComparisonAnalysis, ExamAnalysis, ReportModel
from figures import (
    comparison_overview_distribution,
    comparison_question_distribution,
    exam_average_distribution,
    exam_consistency_distribution,
    exam_question_distribution,
    plot_consistency,
    single_average_distribution,
    single_discrimination_distribution,
    single_question_distribution,
)


REPORT_CSS = r"""
:root {
  color-scheme: light;
  --primary: #ff4b4b;
  --text: #31333f;
  --muted: #6b7280;
  --border: #e5e7eb;
  --surface: #ffffff;
  --surface-muted: #f8fafc;
}
* { box-sizing: border-box; }
html { scroll-behavior: smooth; }
body {
  margin: 0;
  color: var(--text);
  background: var(--surface);
  font-family: "Source Sans 3", "Segoe UI", Arial, sans-serif;
  line-height: 1.55;
}
.report-shell {
  width: min(100% - 2rem, 1120px);
  margin: 0 auto;
  padding: 3rem 0 5rem;
}
h1 { font-size: 2.5rem; margin: 0 0 .25rem; letter-spacing: -.035em; }
h2 {
  margin: 3rem 0 1rem;
  padding-bottom: .45rem;
  border-bottom: 1px solid var(--border);
  font-size: 1.75rem;
}
h3 { margin: 2rem 0 .8rem; font-size: 1.3rem; }
.report-meta { color: var(--muted); margin: 0 0 2rem; }
.callout {
  margin: 1rem 0 2rem;
  padding: .9rem 1rem;
  border-left: .3rem solid var(--primary);
  border-radius: .25rem;
  background: #fff7f7;
}
.tabset { margin: .5rem 0 1.5rem; }
.tab-buttons {
  display: flex;
  gap: 1.35rem;
  overflow-x: auto;
  overflow-y: hidden;
  border-bottom: 1px solid var(--border);
  scrollbar-width: thin;
}
.tab-button {
  flex: 0 0 auto;
  appearance: none;
  border: 0;
  border-bottom: 3px solid transparent;
  margin: 0 0 -1px;
  padding: .7rem .1rem .55rem;
  color: var(--muted);
  background: transparent;
  font: inherit;
  font-weight: 600;
  cursor: pointer;
}
.tab-button:hover { color: var(--text); }
.tab-button.active { color: var(--text); border-bottom-color: var(--primary); }
.tab-button:focus-visible { outline: 2px solid var(--primary); outline-offset: 3px; }
.tab-panel { display: none; padding: 1rem 0 .25rem; }
.tab-panel.active { display: block; }
.figure-card {
  margin: .5rem 0 1rem;
  padding: .75rem;
  overflow-x: auto;
  border: 1px solid var(--border);
  border-radius: .55rem;
  background: var(--surface);
}
.figure-card img { display: block; width: 100%; height: auto; margin: auto; }
.plotly-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 1rem;
}
.table-wrap {
  max-height: 38rem;
  overflow: auto;
  border: 1px solid var(--border);
  border-radius: .45rem;
}
table.dataframe { width: 100%; border-collapse: collapse; font-size: .9rem; }
table.dataframe th,
table.dataframe td {
  padding: .5rem .65rem;
  border-bottom: 1px solid var(--border);
  text-align: right;
  white-space: nowrap;
}
table.dataframe th { position: sticky; top: 0; z-index: 1; background: var(--surface-muted); }
table.dataframe tbody tr:nth-child(even) { background: var(--surface-muted); }
.caption { color: var(--muted); font-size: .9rem; font-style: italic; }
.empty-state { color: var(--muted); padding: .5rem 0; }
@media (max-width: 760px) {
  .report-shell { width: min(100% - 1rem, 1120px); padding-top: 1.5rem; }
  h1 { font-size: 2rem; }
  .plotly-grid { grid-template-columns: 1fr; }
}
@media print {
  .report-shell { width: 100%; padding: 0; }
  .tab-buttons { display: none; }
  .tab-panel { display: block !important; break-inside: avoid; }
  .figure-card { break-inside: avoid; border: 0; }
  .table-wrap { max-height: none; overflow: visible; }
  table.dataframe th { position: static; }
  h2 { break-before: page; }
}
"""


REPORT_JS = r"""
document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll(".tab-button").forEach((button) => {
    button.addEventListener("click", () => {
      const tabset = button.closest(".tabset");
      const buttonRow = button.parentElement;
      buttonRow.querySelectorAll(":scope > .tab-button").forEach((item) => {
        item.classList.toggle("active", item === button);
        item.setAttribute("aria-selected", item === button ? "true" : "false");
      });
      Array.from(tabset.children)
        .filter((child) => child.classList.contains("tab-panel"))
        .forEach((panel) => panel.classList.toggle("active", panel.id === button.dataset.target));
      const activePanel = document.getElementById(button.dataset.target);
      requestAnimationFrame(() => {
        if (window.Plotly && activePanel) {
          activePanel.querySelectorAll(".js-plotly-plot").forEach((plot) => Plotly.Plots.resize(plot));
        }
      });
    });
  });
});
"""


EXAM_BREAKDOWN_PLOTS = 4
SINGLE_EXAM_PLOTS = 6
COMPARISON_PLOTS = 13


def count_report_plots(
    model: ReportModel,
    selected_pairs: list[tuple[str, str]] | None = None,
) -> int:
    """Return the number of figures that will be embedded in a report."""

    return (
        EXAM_BREAKDOWN_PLOTS
        + SINGLE_EXAM_PLOTS * len(model.exams)
        + COMPARISON_PLOTS * len(selected_pairs or [])
    )


class HtmlReportRenderer:
    def __init__(
        self,
        total_plots: int,
        progress_callback: Callable[[int, int], None] | None = None,
    ):
        self._identifier = 0
        self._completed_plots = 0
        self._total_plots = total_plots
        self._progress_callback = progress_callback

    def _plot_completed(self) -> None:
        self._completed_plots += 1
        if self._progress_callback is not None:
            self._progress_callback(self._completed_plots, self._total_plots)

    def _next_id(self, prefix: str) -> str:
        self._identifier += 1
        return f"{prefix}-{self._identifier}"

    def tabs(self, items: list[tuple[str, str]]) -> str:
        if not items:
            return '<p class="empty-state">No content is available.</p>'

        group_id = self._next_id("tabs")
        buttons = []
        panels = []
        for index, (label, content) in enumerate(items):
            panel_id = f"{group_id}-panel-{index}"
            active = " active" if index == 0 else ""
            selected = "true" if index == 0 else "false"
            buttons.append(
                f'<button class="tab-button{active}" type="button" role="tab" '
                f'aria-selected="{selected}" aria-controls="{panel_id}" '
                f'data-target="{panel_id}">{html.escape(str(label))}</button>'
            )
            panels.append(
                f'<section class="tab-panel{active}" id="{panel_id}" role="tabpanel">'
                f"{content}</section>"
            )
        return (
            '<div class="tabset">'
            '<div class="tab-buttons" role="tablist">'
            + "".join(buttons)
            + "</div>"
            + "".join(panels)
            + "</div>"
        )

    def matplotlib_figure(self, figure) -> str:
        image_buffer = BytesIO()
        try:
            figure.savefig(
                image_buffer,
                format="png",
                dpi=160,
                bbox_inches="tight",
                facecolor="white",
            )
        finally:
            plt.close(figure)
        encoded = base64.b64encode(image_buffer.getvalue()).decode("ascii")
        figure_html = (
            '<div class="figure-card">'
            f'<img src="data:image/png;base64,{encoded}" alt="Generated statistical chart">'
            "</div>"
        )
        self._plot_completed()
        return figure_html

    def plotly_figure(self, figure) -> str:
        plot_id = self._next_id("plotly")
        figure.update_layout(autosize=True)
        chart = pio.to_html(
            figure,
            include_plotlyjs=False,
            full_html=False,
            config={"responsive": True, "displaylogo": False},
            default_width="100%",
            default_height="520px",
            div_id=plot_id,
        )
        figure_html = f'<div class="figure-card">{chart}</div>'
        self._plot_completed()
        return figure_html

    @staticmethod
    def dataframe(frame: pd.DataFrame) -> str:
        table = frame.to_html(
            classes=["dataframe"],
            border=0,
            escape=True,
            na_rep="—",
            float_format=lambda value: f"{value:.3f}",
        )
        return f'<div class="table-wrap">{table}</div>'

    def exam_breakdown(self, model: ReportModel) -> str:
        overview = self.tabs(
            [
                (
                    "By average",
                    self.matplotlib_figure(exam_average_distribution(model.stats)),
                ),
                (
                    "By Cronbach's alpha",
                    self.matplotlib_figure(exam_consistency_distribution(model.stats)),
                ),
            ]
        )
        details = self.tabs(
            [
                (
                    "Bar",
                    self.matplotlib_figure(
                        exam_question_distribution(model.stats, model.total_scores, "bar")
                    ),
                ),
                (
                    "Box",
                    self.matplotlib_figure(
                        exam_question_distribution(model.stats, model.total_scores, "box")
                    ),
                ),
                ("Data", self.dataframe(model.stats)),
            ]
        )
        return f"<h2>Exam Breakdown</h2><h3>Overview</h3>{overview}<h3>Exam-Level Statistics</h3>{details}"

    def single_exam(self, exam: ExamAnalysis, *, include_heading: bool = False) -> str:
        heading = f"<h2>{html.escape(exam.display_name)}</h2>" if include_heading else ""
        overview = self.tabs(
            [
                (
                    "Overview by average",
                    self.matplotlib_figure(
                        single_average_distribution(exam.summary, exam.display_name)
                    ),
                ),
                (
                    "Overview by DI",
                    self.matplotlib_figure(
                        single_discrimination_distribution(exam.summary, exam.display_name)
                    ),
                ),
            ]
        )
        question_stats = self.tabs(
            [
                (
                    "Consistency",
                    self.plotly_figure(plot_consistency(exam.summary, exam.display_name)),
                ),
                (
                    "Bar",
                    self.matplotlib_figure(
                        single_question_distribution(
                            exam.summary,
                            exam.long_scores,
                            exam.display_name,
                            "bar",
                        )
                    ),
                ),
                (
                    "Box",
                    self.matplotlib_figure(
                        single_question_distribution(
                            exam.summary,
                            exam.long_scores,
                            exam.display_name,
                            "box",
                        )
                    ),
                ),
                (
                    "Discrimination",
                    self.matplotlib_figure(
                        single_question_distribution(
                            exam.summary,
                            exam.long_scores,
                            exam.display_name,
                            "split-violin",
                        )
                    ),
                ),
                ("Data", self.dataframe(exam.summary)),
            ]
        )
        return f"{heading}<h3>Overview</h3>{overview}<h3>Question-Level Statistics</h3>{question_stats}"

    def comparison_individual(self, comparison: ComparisonAnalysis) -> str:
        lower = comparison.lower
        higher = comparison.higher
        overview = self.tabs(
            [
                (
                    "By average",
                    self.matplotlib_figure(
                        comparison_overview_distribution(
                            lower.summary,
                            higher.summary,
                            lower.display_name,
                            higher.display_name,
                            "average",
                        )
                    ),
                ),
                (
                    "By discrimination index",
                    self.matplotlib_figure(
                        comparison_overview_distribution(
                            lower.summary,
                            higher.summary,
                            lower.display_name,
                            higher.display_name,
                            "discrimination",
                        )
                    ),
                ),
            ]
        )
        categorization = self.tabs(
            [
                ("Overview", self.dataframe(comparison.type_proportions)),
                ("Question List", self.dataframe(comparison.type_questions)),
            ]
        )
        consistency = (
            '<div class="plotly-grid">'
            + self.plotly_figure(plot_consistency(lower.summary, lower.display_name))
            + self.plotly_figure(plot_consistency(higher.summary, higher.display_name))
            + "</div>"
        )
        normalized = self.tabs(
            [
                ("Consistency", consistency),
                (
                    "Bar",
                    self.matplotlib_figure(
                        comparison_question_distribution(
                            lower.summary,
                            higher.summary,
                            lower.long_scores,
                            higher.long_scores,
                            lower.display_name,
                            higher.display_name,
                            "bar",
                        )
                    ),
                ),
                (
                    "Box",
                    self.matplotlib_figure(
                        comparison_question_distribution(
                            lower.summary,
                            higher.summary,
                            lower.long_scores,
                            higher.long_scores,
                            lower.display_name,
                            higher.display_name,
                            "box",
                        )
                    ),
                ),
                (
                    "Discrimination",
                    self.matplotlib_figure(
                        comparison_question_distribution(
                            lower.summary,
                            higher.summary,
                            lower.long_scores,
                            higher.long_scores,
                            lower.display_name,
                            higher.display_name,
                            "split-violin",
                        )
                    ),
                ),
                ("Data", self.dataframe(comparison.normalized_summary)),
            ]
        )
        return (
            f"<h3>Overview</h3>{overview}"
            f"<h3>Question Categorization</h3>{categorization}"
            '<p class="caption">* Can sum to more than 100% when questions belong to multiple categories.</p>'
            f"<h3>Normalized Statistics</h3>{normalized}"
        )

    def comparison(self, comparison: ComparisonAnalysis) -> str:
        return self.tabs(
            [
                ("Individual Stats", self.comparison_individual(comparison)),
                ("Combined Stats", self.single_exam(comparison.combined)),
            ]
        )

    def render(self, model: ReportModel, selected_pairs: list[tuple[str, str]]) -> str:
        individual_tabs = self.tabs(
            [(exam.display_name, self.single_exam(exam)) for exam in model.exams]
        )

        comparison_tabs = []
        for lower_name, higher_name in selected_pairs:
            comparison = model.compare(lower_name, higher_name)
            label = f"{comparison.lower.display_name} vs {comparison.higher.display_name}"
            comparison_tabs.append((label, self.comparison(comparison)))

        comparison_section = ""
        if comparison_tabs:
            comparison_section = (
                "<h2>Selected Exam Comparisons</h2>" + self.tabs(comparison_tabs)
            )

        generated_at = datetime.now().astimezone().strftime("%B %d, %Y at %I:%M %p %Z")
        plotly_js = get_plotlyjs()
        return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>WUCT Exam Review Report</title>
  <style>{REPORT_CSS}</style>
  <script>{plotly_js}</script>
</head>
<body>
  <main class="report-shell">
    <h1>WUCT Exam Review</h1>
    <p class="report-meta">Static report generated {html.escape(generated_at)}</p>
    <div class="callout">This self-contained report includes calculated statistics and rendered graphics. The original CSV files are not required to view it.</div>
    {self.exam_breakdown(model)}
    <h2>Individual Exam Reports</h2>
    {individual_tabs}
    {comparison_section}
  </main>
  <script>{REPORT_JS}</script>
</body>
</html>"""


def generate_html_report(
    model: ReportModel,
    selected_pairs: list[tuple[str, str]] | None = None,
    progress_callback: Callable[[int, int], None] | None = None,
) -> bytes:
    """Return a complete UTF-8 HTML report suitable for direct download."""

    selected_pairs = selected_pairs or []
    total_plots = count_report_plots(model, selected_pairs)
    if progress_callback is not None:
        progress_callback(0, total_plots)
    renderer = HtmlReportRenderer(total_plots, progress_callback)
    return renderer.render(model, selected_pairs).encode("utf-8")

import unittest

import numpy as np
import pandas as pd

from analysis import build_report_model
from helper import normalize_total_sc
from html_report import count_report_plots, generate_html_report


def make_scores(label: str, offset: float) -> pd.DataFrame:
    random = np.random.default_rng(42 + int(offset * 100))
    latent = np.linspace(0.1, 0.9, 36) + offset
    question_columns = {}
    for question_number in range(1, 7):
        scores = np.clip(latent + random.normal(0, 0.08, latent.size), 0, 1)
        question_columns[f"Question {question_number} (1.0 pts)"] = scores
    frame = pd.DataFrame(question_columns)
    frame.insert(0, "Name", [f"PRIVATE-{label}-{index}" for index in range(len(frame))])
    frame["Total Score"] = frame[list(question_columns)].sum(axis=1)
    return normalize_total_sc(frame)


class HtmlReportTests(unittest.TestCase):
    def test_self_contained_report_contains_all_sections_without_student_names(self):
        model = build_report_model(
            [make_scores("lower", 0.0), make_scores("higher", 0.05)],
            ["Lower_Exam", "Higher_Exam"],
        )

        report = generate_html_report(model, [("Lower_Exam", "Higher_Exam")]).decode(
            "utf-8"
        )

        self.assertTrue(report.startswith("<!doctype html>"))
        self.assertIn("Exam Breakdown", report)
        self.assertIn("Individual Exam Reports", report)
        self.assertIn("Selected Exam Comparisons", report)
        self.assertIn("Lower Exam vs Higher Exam", report)
        self.assertIn("Question Categorization", report)
        self.assertIn("Combined Stats", report)
        self.assertIn("data:image/png;base64,", report)
        self.assertIn("plotly.js", report)
        self.assertNotIn("PRIVATE-lower", report)
        self.assertNotIn("Upload Exam Document", report)

    def test_progress_reports_each_embedded_plot(self):
        model = build_report_model(
            [make_scores("lower", 0.0), make_scores("higher", 0.05)],
            ["Lower_Exam", "Higher_Exam"],
        )
        selected_pairs = [("Lower_Exam", "Higher_Exam")]
        expected_total = count_report_plots(model, selected_pairs)
        updates = []

        generate_html_report(
            model,
            selected_pairs,
            progress_callback=lambda completed, total: updates.append(
                (completed, total)
            ),
        )

        self.assertEqual(29, expected_total)
        self.assertEqual((0, expected_total), updates[0])
        self.assertEqual((expected_total, expected_total), updates[-1])
        self.assertEqual(list(range(expected_total + 1)), [item[0] for item in updates])

    def test_duplicate_exam_names_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "unique filenames"):
            build_report_model(
                [make_scores("one", 0.0), make_scores("two", 0.05)],
                ["Exam", "Exam"],
            )


if __name__ == "__main__":
    unittest.main()

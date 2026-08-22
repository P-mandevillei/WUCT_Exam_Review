import unittest
from pathlib import Path

from streamlit.testing.v1 import AppTest

from test_html_report import make_scores


class StreamlitAppTests(unittest.TestCase):
    def test_uploaded_exams_expose_dynamic_report_controls_and_download(self):
        app_path = Path(__file__).resolve().parents[1] / "question_analysis.py"
        app = AppTest.from_file(app_path).run(timeout=30)
        files = [
            (
                "Lower_Exam.csv",
                make_scores("lower", 0.0).to_csv(index=False).encode("utf-8"),
                "text/csv",
            ),
            (
                "Higher_Exam.csv",
                make_scores("higher", 0.05).to_csv(index=False).encode("utf-8"),
                "text/csv",
            ),
        ]

        app = app.get("file_uploader")[0].set_value(files).run(timeout=60)
        self.assertEqual([], list(app.exception))

        # Tracked tabs render only their selected child. Switching the keyed tab
        # replaces that child rather than computing both branches.
        self.assertEqual(
            ["imgs"],
            [child.type for child in app.tabs[2].children.values()],
        )
        self.assertEqual([], list(app.tabs[3].children.values()))
        self.assertEqual([], list(app.tabs[4].children.values()))
        app.session_state["exam-level-tabs"] = "Data"
        app = app.run(timeout=60)
        self.assertEqual([], list(app.tabs[2].children.values()))
        self.assertEqual([], list(app.tabs[3].children.values()))
        self.assertEqual(
            ["dataframe"],
            [child.type for child in app.tabs[4].children.values()],
        )

        compare_selectbox = next(
            selectbox
            for selectbox in app.selectbox
            if selectbox.label.startswith("Select a second scores set")
        )
        app = compare_selectbox.select("Higher_Exam").run(timeout=60)
        individual_tab = next(
            tab for tab in app.tabs if tab.label == "Individual Stats"
        )
        combined_tab = next(
            tab for tab in app.tabs if tab.label == "Combined Stats"
        )
        self.assertNotEqual([], list(individual_tab.children.values()))
        self.assertEqual([], list(combined_tab.children.values()))

        app.session_state[
            "question-comparison-Lower_Exam-Higher_Exam-mode-tabs"
        ] = "Combined Stats"
        app = app.run(timeout=60)
        individual_tab = next(
            tab for tab in app.tabs if tab.label == "Individual Stats"
        )
        combined_tab = next(
            tab for tab in app.tabs if tab.label == "Combined Stats"
        )
        self.assertEqual([], list(individual_tab.children.values()))
        self.assertNotEqual([], list(combined_tab.children.values()))

        self.assertIn("Generate HTML Report", [header.value for header in app.header])
        self.assertIn("Lower division", [selectbox.label for selectbox in app.selectbox])
        self.assertIn("Higher division", [selectbox.label for selectbox in app.selectbox])

        self.assertIn("Add comparison", [button.label for button in app.button])
        self.assertEqual(
            1,
            sum(selectbox.label == "Lower division" for selectbox in app.selectbox),
        )

        add_button = next(
            button for button in app.button if button.label == "Add comparison"
        )
        app = add_button.click().run(timeout=60)
        self.assertEqual([], list(app.exception))
        self.assertEqual(
            2,
            sum(selectbox.label == "Lower division" for selectbox in app.selectbox),
        )
        remove_button = next(
            button for button in app.button if button.label == "Remove last"
        )
        app = remove_button.click().run(timeout=60)
        self.assertEqual([], list(app.exception))
        self.assertEqual(
            1,
            sum(selectbox.label == "Lower division" for selectbox in app.selectbox),
        )

        generate_button = next(
            button for button in app.button if button.label == "Generate HTML Report"
        )
        app = generate_button.click().run(timeout=90)
        self.assertEqual([], list(app.exception))
        progress = app.get("progress")[0]
        self.assertEqual(100, progress.value)
        self.assertEqual("Drawing report plots: 29 of 29", progress.text)
        self.assertIn(
            "Download HTML Report",
            [button.label for button in app.get("download_button")],
        )


if __name__ == "__main__":
    unittest.main()

from pathlib import Path
import unittest

from orca_discord_presence.core import choose_activity, format_model
from orca_discord_presence.models import AgentSession, OrcaFocus, PrivacyConfig


class ActivitySelectionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.focus = OrcaFocus(
            repo_id="repo",
            worktree_id="repo::/work/Trident-APE",
            tab_id="active-tab",
            project="Trident-APE",
        )
        self.session = AgentSession(
            pid=42,
            tab_id="active-tab",
            worktree_id="repo::/work/Trident-APE",
            cwd=Path("/work/Trident-APE"),
            started_at=1_700_000_000,
            agent="oh-my-pi",
            model="gpt-5.6-sol",
            session_name="Resolve Trident APE product outcome",
            small_image="omp1-transparent",
        )
        self.public = PrivacyConfig(True, True, True)

    def test_exact_session_uses_project_model_and_session_title(self) -> None:
        activity = choose_activity(self.focus, [self.session], 100, self.public)

        self.assertEqual(activity.details, "Trident-APE · GPT-5.6 Sol")
        self.assertEqual(activity.state, "Resolve Trident APE product outcome")
        self.assertEqual(activity.started_at, self.session.started_at)
        self.assertEqual(activity.small_image, "omp1-transparent")

    def test_switching_back_preserves_process_start_time(self) -> None:
        activity = choose_activity(self.focus, [self.session], 999, self.public)
        self.assertEqual(activity.started_at, 1_700_000_000)

    def test_fallback_uses_newest_session_and_reports_count(self) -> None:
        older = AgentSession(
            **{
                **self.session.__dict__,
                "pid": 41,
                "tab_id": "older-tab",
                "started_at": 1_600_000_000,
                "session_name": "Older task",
            }
        )
        missing_tab = OrcaFocus(
            repo_id=self.focus.repo_id,
            worktree_id=self.focus.worktree_id,
            tab_id="file-tab",
            project=self.focus.project,
        )

        activity = choose_activity(
            missing_tab, [older, self.session], 100, self.public
        )

        self.assertEqual(activity.state, "Resolve Trident APE product outcome · 2 sessions")
        self.assertEqual(activity.started_at, self.session.started_at)

    def test_missing_model_never_falls_back_to_agent_name(self) -> None:
        loading = AgentSession(**{**self.session.__dict__, "model": None})
        activity = choose_activity(self.focus, [loading], 100, self.public)
        self.assertEqual(activity.details, "Trident-APE · Model loading")
        self.assertNotIn("oh-my-pi", activity.details)
        self.assertNotIn("oh-my-pi", activity.state)

    def test_session_privacy_hides_title(self) -> None:
        privacy = PrivacyConfig(show_project=True, show_session=False, show_model=True)
        activity = choose_activity(self.focus, [self.session], 100, privacy)
        self.assertEqual(activity.details, "Trident-APE")
        self.assertEqual(activity.state, "GPT-5.6 Sol")

    def test_project_privacy_hides_project(self) -> None:
        privacy = PrivacyConfig(show_project=False, show_session=True, show_model=True)
        activity = choose_activity(self.focus, [self.session], 100, privacy)
        self.assertEqual(activity.details, "GPT-5.6 Sol")
        self.assertEqual(activity.state, "Resolve Trident APE product outcome")

    def test_no_agent_uses_orca_start_time(self) -> None:
        activity = choose_activity(self.focus, [], 1234, self.public)
        self.assertEqual(activity.details, "Trident-APE")
        self.assertEqual(activity.state, "Orca ADE")
        self.assertEqual(activity.started_at, 1234)

    def test_discord_fields_are_clipped(self) -> None:
        long_session = AgentSession(
            **{**self.session.__dict__, "session_name": "x" * 200}
        )
        activity = choose_activity(self.focus, [long_session], 100, self.public)
        self.assertEqual(len(activity.state), 128)
        self.assertTrue(activity.state.endswith("…"))

    def test_model_formatting(self) -> None:
        self.assertEqual(format_model("gpt-5.6-luna"), "GPT-5.6 Luna")
        self.assertEqual(format_model("o3-mini"), "O3 Mini")


if __name__ == "__main__":
    unittest.main()

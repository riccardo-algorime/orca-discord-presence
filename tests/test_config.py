from pathlib import Path
import tempfile
import unittest

from orca_discord_presence.config import DEFAULT_CLIENT_ID, load_config


class ConfigurationTests(unittest.TestCase):
    def test_missing_file_uses_public_defaults(self) -> None:
        config = load_config(Path("/definitely/missing/config.toml"))
        self.assertEqual(config.discord.client_id, DEFAULT_CLIENT_ID)
        self.assertTrue(config.privacy.show_session)
        self.assertEqual(config.discord.omp_small_image, "omp1-transparent")

    def test_overrides_privacy_paths_and_asset(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.toml"
            path.write_text(
                """
[privacy]
show_project = false
show_session = false
show_model = true

[discord]
omp_small_image = ""

[paths]
orca_executable = "~/Orca/orca-ide"
"""
            )
            config = load_config(path)

        self.assertFalse(config.privacy.show_project)
        self.assertFalse(config.privacy.show_session)
        self.assertIsNone(config.discord.omp_small_image)
        self.assertEqual(
            config.paths.orca_executable, Path.home() / "Orca/orca-ide"
        )

    def test_rejects_invalid_timing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.toml"
            path.write_text("[timing]\npoll_interval_seconds = 0\n")
            with self.assertRaisesRegex(ValueError, "positive number"):
                load_config(path)


if __name__ == "__main__":
    unittest.main()

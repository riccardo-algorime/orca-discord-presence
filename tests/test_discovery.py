import json
import os
from pathlib import Path
import tempfile
import unittest

from orca_discord_presence.discovery import LinuxDiscovery
from orca_discord_presence.models import PathsConfig


def title_line(title: str) -> bytes:
    payload = json.dumps({"type": "title", "title": title}, separators=(",", ":"))
    return (payload + " " * (255 - len(payload)) + "\n").encode()


def record(value: dict) -> bytes:
    return (json.dumps(value, separators=(",", ":")) + "\n").encode()


class OmpMetadataTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        self.discovery = LinuxDiscovery(
            PathsConfig(
                orca_executable=Path("/opt/Orca/orca-ide"),
                orca_config=root / "orca",
                omp_terminal_sessions=root / "terminal-sessions",
            ),
            omp_small_image="omp1-transparent",
        )
        self.session = root / "session.jsonl"

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_reads_model_and_true_omp_session_title(self) -> None:
        self.session.write_bytes(
            title_line("Resolve Trident APE product outcome")
            + record(
                {
                    "type": "model_change",
                    "model": "openai-codex/gpt-5.6-sol",
                }
            )
        )

        model, title = self.discovery.read_omp_metadata(self.session)

        self.assertEqual(model, "gpt-5.6-sol")
        self.assertEqual(title, "Resolve Trident APE product outcome")

    def test_detects_in_place_title_rewrite_without_size_change(self) -> None:
        self.session.write_bytes(
            title_line("Old session title")
            + record({"type": "model_change", "model": "gpt-5.6-sol"})
        )
        self.discovery.read_omp_metadata(self.session)
        previous = self.session.stat()

        with self.session.open("r+b") as stream:
            stream.write(title_line("New session title"))
        os.utime(
            self.session,
            ns=(previous.st_atime_ns, previous.st_mtime_ns + 1_000_000),
        )

        model, title = self.discovery.read_omp_metadata(self.session)

        self.assertEqual(model, "gpt-5.6-sol")
        self.assertEqual(title, "New session title")

    def test_incrementally_tracks_model_and_title_changes(self) -> None:
        self.session.write_bytes(
            title_line("Initial task")
            + record({"type": "model_change", "model": "gpt-5.6-luna"})
        )
        self.discovery.read_omp_metadata(self.session)

        with self.session.open("ab") as stream:
            stream.write(
                record(
                    {
                        "type": "model_change",
                        "model": "openai-codex/gpt-5.6-sol",
                    }
                )
            )
            stream.write(
                record(
                    {
                        "type": "title_change",
                        "title": "Final task title",
                    }
                )
            )

        model, title = self.discovery.read_omp_metadata(self.session)

        self.assertEqual(model, "gpt-5.6-sol")
        self.assertEqual(title, "Final task title")

    def test_assistant_record_supplies_model(self) -> None:
        candidate = LinuxDiscovery.model_from_record(
            {
                "type": "message",
                "message": {
                    "role": "assistant",
                    "provider": "openai-codex",
                    "model": "gpt-5.6-luna",
                },
            }
        )
        self.assertEqual(candidate, "gpt-5.6-luna")


if __name__ == "__main__":
    unittest.main()

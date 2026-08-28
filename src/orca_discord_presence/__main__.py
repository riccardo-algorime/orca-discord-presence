from __future__ import annotations

import argparse
from dataclasses import asdict
import json
import logging
from pathlib import Path
import time

from .config import DEFAULT_CONFIG_PATH, load_config
from .core import choose_activity
from .daemon import PresenceMonitor
from .discovery import LinuxDiscovery


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Focus-aware Discord Rich Presence for Orca ADE"
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=DEFAULT_CONFIG_PATH,
        help=f"configuration file (default: {DEFAULT_CONFIG_PATH})",
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="print the currently resolved activity without connecting to Discord",
    )
    return parser


def main() -> None:
    args = _parser().parse_args()
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )
    config = load_config(args.config.expanduser())

    if args.once:
        discovery = LinuxDiscovery(config.paths, config.discord.omp_small_image)
        orca_process = discovery.find_orca_process()
        if orca_process is None:
            print(json.dumps({"orca_open": False}))
            return
        _, orca_started_at = orca_process
        activity = choose_activity(
            discovery.read_orca_focus(),
            discovery.scan_agent_sessions(),
            orca_started_at or int(time.time()),
            config.privacy,
        )
        print(json.dumps({"orca_open": True, "activity": asdict(activity)}))
        return

    PresenceMonitor(config).run()


if __name__ == "__main__":
    main()

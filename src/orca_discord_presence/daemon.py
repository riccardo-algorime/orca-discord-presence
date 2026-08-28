from __future__ import annotations

import logging
import os
import signal
import time

from pypresence import Presence

from .core import choose_activity
from .discovery import LinuxDiscovery
from .models import Activity, Config, OrcaFocus

LOG = logging.getLogger("orca-discord-presence")


class PresenceMonitor:
    def __init__(self, config: Config):
        self.config = config
        self.discovery = LinuxDiscovery(
            config.paths, config.discord.omp_small_image
        )
        self.stop_requested = False

    def _request_stop(self, signum: int, _frame: object) -> None:
        self.stop_requested = True
        LOG.info("Stopping after signal %s", signum)

    @staticmethod
    def _dispose(rpc: Presence | None) -> None:
        if rpc is None:
            return
        writer = getattr(rpc, "sock_writer", None)
        if writer is not None:
            try:
                writer.close()
            except Exception:
                pass
        loop = getattr(rpc, "loop", None)
        if loop is not None and not loop.is_closed():
            try:
                loop.close()
            except Exception:
                pass

    def _publish(self, rpc: Presence, pid: int, activity: Activity) -> None:
        rpc.update(
            pid=pid,
            details=activity.details,
            state=activity.state,
            start=activity.started_at,
            large_image=self.config.discord.large_image,
            large_text=self.config.discord.large_text,
            small_image=activity.small_image,
            small_text=activity.small_text,
        )

    def run(self) -> None:
        signal.signal(signal.SIGINT, self._request_stop)
        signal.signal(signal.SIGTERM, self._request_stop)

        rpc: Presence | None = None
        activity_pid: int | None = None
        orca_started_at: int | None = None
        last_focus: OrcaFocus | None = None
        published_activity: Activity | None = None
        next_connect_at = 0.0
        last_publish_at = 0.0
        discord_unavailable_logged = False

        LOG.info("Monitor started; watching %s", self.config.paths.orca_executable)

        while not self.stop_requested:
            now = time.monotonic()
            orca_process = self.discovery.find_orca_process()

            if orca_process is None and activity_pid is not None:
                if rpc is not None:
                    try:
                        rpc.clear(pid=activity_pid)
                        LOG.info("Orca ADE closed; Rich Presence cleared")
                    except Exception as exc:
                        LOG.warning(
                            "Discord connection lost while clearing presence: %s", exc
                        )
                        self._dispose(rpc)
                        rpc = None
                activity_pid = None
                orca_started_at = None
                last_focus = None
                published_activity = None
                last_publish_at = 0.0

            if orca_process is not None:
                detected_pid, detected_start = orca_process
                if activity_pid != detected_pid:
                    activity_pid = detected_pid
                    orca_started_at = detected_start
                    published_activity = None
                    next_connect_at = 0.0
                    LOG.info("Orca ADE detected (PID %s)", activity_pid)

                current_focus = self.discovery.read_orca_focus()
                if current_focus is not None:
                    last_focus = current_focus
                activity = choose_activity(
                    last_focus,
                    self.discovery.scan_agent_sessions(),
                    orca_started_at or int(time.time()),
                    self.config.privacy,
                )
                activity_changed = activity != published_activity

                if rpc is None and now >= next_connect_at:
                    candidate: Presence | None = None
                    try:
                        candidate = Presence(self.config.discord.client_id)
                        candidate.connect()
                        self._publish(candidate, activity_pid, activity)
                        rpc = candidate
                        published_activity = activity
                        last_publish_at = now
                        if discord_unavailable_logged:
                            LOG.info("Discord IPC available again; reconnected")
                        LOG.info(
                            "Rich Presence active: %s | %s",
                            activity.details,
                            activity.state,
                        )
                        discord_unavailable_logged = False
                    except Exception as exc:
                        self._dispose(candidate)
                        next_connect_at = (
                            now + self.config.timing.reconnect_interval_seconds
                        )
                        if not discord_unavailable_logged:
                            LOG.info(
                                "Discord IPC unavailable; retrying quietly: %s", exc
                            )
                            discord_unavailable_logged = True
                elif rpc is not None and (
                    activity_changed
                    or now - last_publish_at
                    >= self.config.timing.refresh_interval_seconds
                ):
                    try:
                        self._publish(rpc, activity_pid, activity)
                        if activity_changed:
                            LOG.info(
                                "Rich Presence updated: %s | %s",
                                activity.details,
                                activity.state,
                            )
                        published_activity = activity
                        last_publish_at = now
                    except Exception as exc:
                        LOG.warning(
                            "Discord connection lost; reconnecting quietly: %s", exc
                        )
                        self._dispose(rpc)
                        rpc = None
                        next_connect_at = (
                            now + self.config.timing.reconnect_interval_seconds
                        )
                        discord_unavailable_logged = True

            time.sleep(self.config.timing.poll_interval_seconds)

        if rpc is not None:
            if activity_pid is not None:
                try:
                    rpc.clear(pid=activity_pid)
                except Exception:
                    pass
            self._dispose(rpc)
        LOG.info("Monitor stopped")

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class PathsConfig:
    orca_executable: Path
    orca_config: Path
    omp_terminal_sessions: Path


@dataclass(frozen=True)
class DiscordConfig:
    client_id: str
    large_image: str
    large_text: str
    omp_small_image: str | None


@dataclass(frozen=True)
class PrivacyConfig:
    show_project: bool
    show_session: bool
    show_model: bool


@dataclass(frozen=True)
class TimingConfig:
    poll_interval_seconds: float
    reconnect_interval_seconds: float
    refresh_interval_seconds: float


@dataclass(frozen=True)
class Config:
    paths: PathsConfig
    discord: DiscordConfig
    privacy: PrivacyConfig
    timing: TimingConfig


@dataclass(frozen=True)
class OrcaFocus:
    repo_id: str | None
    worktree_id: str | None
    tab_id: str | None
    project: str | None


@dataclass(frozen=True)
class AgentSession:
    pid: int
    tab_id: str
    worktree_id: str | None
    cwd: Path
    started_at: int
    agent: str
    model: str | None
    session_name: str | None
    small_image: str | None


@dataclass(frozen=True)
class Activity:
    details: str
    state: str
    started_at: int
    small_image: str | None
    small_text: str | None

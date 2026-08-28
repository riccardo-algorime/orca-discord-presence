from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import tomllib

from .models import Config, DiscordConfig, PathsConfig, PrivacyConfig, TimingConfig

DEFAULT_CLIENT_ID = "1542854905906331710"
DEFAULT_CONFIG_PATH = Path.home() / ".config/orca-discord-presence/config.toml"


def default_config() -> Config:
    return Config(
        paths=PathsConfig(
            orca_executable=Path("/opt/Orca/orca-ide"),
            orca_config=Path.home() / ".config/orca",
            omp_terminal_sessions=Path.home()
            / ".omp/agent/terminal-sessions",
        ),
        discord=DiscordConfig(
            client_id=DEFAULT_CLIENT_ID,
            large_image="orca",
            large_text="Orca ADE",
            omp_small_image="omp1-transparent",
        ),
        privacy=PrivacyConfig(
            show_project=True,
            show_session=True,
            show_model=True,
        ),
        timing=TimingConfig(
            poll_interval_seconds=2.0,
            reconnect_interval_seconds=10.0,
            refresh_interval_seconds=15.0,
        ),
    )


def _section(data: dict, name: str) -> dict:
    value = data.get(name, {})
    if not isinstance(value, dict):
        raise ValueError(f"[{name}] must be a TOML table")
    return value


def _string(section: dict, key: str, default: str) -> str:
    value = section.get(key, default)
    if not isinstance(value, str) or not value:
        raise ValueError(f"{key} must be a non-empty string")
    return value


def _optional_string(section: dict, key: str, default: str | None) -> str | None:
    value = section.get(key, default)
    if value is None or value == "":
        return None
    if not isinstance(value, str):
        raise ValueError(f"{key} must be a string")
    return value


def _boolean(section: dict, key: str, default: bool) -> bool:
    value = section.get(key, default)
    if not isinstance(value, bool):
        raise ValueError(f"{key} must be true or false")
    return value


def _positive_number(section: dict, key: str, default: float) -> float:
    value = section.get(key, default)
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value <= 0:
        raise ValueError(f"{key} must be a positive number")
    return float(value)


def _path(section: dict, key: str, default: Path) -> Path:
    value = _string(section, key, str(default))
    return Path(value).expanduser()


def load_config(path: Path = DEFAULT_CONFIG_PATH) -> Config:
    config = default_config()
    if not path.exists():
        return config

    with path.open("rb") as stream:
        data = tomllib.load(stream)

    paths = _section(data, "paths")
    discord = _section(data, "discord")
    privacy = _section(data, "privacy")
    timing = _section(data, "timing")

    return replace(
        config,
        paths=PathsConfig(
            orca_executable=_path(
                paths, "orca_executable", config.paths.orca_executable
            ),
            orca_config=_path(paths, "orca_config", config.paths.orca_config),
            omp_terminal_sessions=_path(
                paths,
                "omp_terminal_sessions",
                config.paths.omp_terminal_sessions,
            ),
        ),
        discord=DiscordConfig(
            client_id=_string(discord, "client_id", config.discord.client_id),
            large_image=_string(
                discord, "large_image", config.discord.large_image
            ),
            large_text=_string(discord, "large_text", config.discord.large_text),
            omp_small_image=_optional_string(
                discord, "omp_small_image", config.discord.omp_small_image
            ),
        ),
        privacy=PrivacyConfig(
            show_project=_boolean(
                privacy, "show_project", config.privacy.show_project
            ),
            show_session=_boolean(
                privacy, "show_session", config.privacy.show_session
            ),
            show_model=_boolean(privacy, "show_model", config.privacy.show_model),
        ),
        timing=TimingConfig(
            poll_interval_seconds=_positive_number(
                timing,
                "poll_interval_seconds",
                config.timing.poll_interval_seconds,
            ),
            reconnect_interval_seconds=_positive_number(
                timing,
                "reconnect_interval_seconds",
                config.timing.reconnect_interval_seconds,
            ),
            refresh_interval_seconds=_positive_number(
                timing,
                "refresh_interval_seconds",
                config.timing.refresh_interval_seconds,
            ),
        ),
    )

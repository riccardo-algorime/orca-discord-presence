from __future__ import annotations

import json
import os
from pathlib import Path

from .models import AgentSession, OrcaFocus, PathsConfig

AGENT_BY_EXECUTABLE = {
    "omp": "oh-my-pi",
    "codex": "Codex",
    "claude": "Claude",
    "gemini": "Gemini",
}


class LinuxDiscovery:
    def __init__(self, paths: PathsConfig, omp_small_image: str | None):
        self.paths = paths
        self.omp_small_image = omp_small_image
        self.clock_ticks = os.sysconf(os.sysconf_names["SC_CLK_TCK"])
        self.boot_time = self._read_boot_time()
        self.session_cache: dict[
            Path, tuple[int, int, str | None, str | None]
        ] = {}
        self.last_model_by_tab: dict[str, str] = {}
        self.last_session_name_by_tab: dict[str, str] = {}

    @staticmethod
    def _read_boot_time() -> int:
        for line in Path("/proc/stat").read_text().splitlines():
            if line.startswith("btime "):
                return int(line.split()[1])
        raise RuntimeError("Linux boot time is unavailable")

    def _process_start_time(self, pid: int) -> int:
        stat = Path(f"/proc/{pid}/stat").read_text()
        fields = stat[stat.rfind(")") + 2 :].split()
        start_ticks = int(fields[19])
        return self.boot_time + start_ticks // self.clock_ticks

    def find_orca_process(self) -> tuple[int, int] | None:
        for proc_dir in Path("/proc").iterdir():
            if not proc_dir.name.isdigit():
                continue
            try:
                if Path(os.readlink(proc_dir / "exe")) != self.paths.orca_executable:
                    continue
                argv = (proc_dir / "cmdline").read_bytes().rstrip(b"\0").split(b"\0")
                child_args = argv[1:]
                if any(arg.startswith(b"--type=") for arg in child_args):
                    continue
                if any(b"daemon-entry.js" in arg for arg in child_args):
                    continue
                pid = int(proc_dir.name)
                return pid, self._process_start_time(pid)
            except (FileNotFoundError, PermissionError, ProcessLookupError, ValueError):
                continue
        return None

    @staticmethod
    def _read_json(path: Path) -> dict | None:
        try:
            value = json.loads(path.read_bytes())
            return value if isinstance(value, dict) else None
        except (FileNotFoundError, PermissionError, json.JSONDecodeError):
            return None

    def read_orca_focus(self) -> OrcaFocus | None:
        index = self._read_json(self.paths.orca_config / "orca-profile-index.json")
        if index is None or not isinstance(index.get("activeProfileId"), str):
            return None
        data = self._read_json(
            self.paths.orca_config
            / "profiles"
            / index["activeProfileId"]
            / "orca-data.json"
        )
        if data is None:
            return None

        workspace = data.get("workspaceSession")
        if not isinstance(workspace, dict):
            return None
        repo_id = workspace.get("activeRepoId")
        worktree_id = workspace.get("activeWorktreeId")
        tab_id = workspace.get("activeTabId")

        project = None
        repos = data.get("repos")
        if isinstance(repos, list):
            for repo in repos:
                if not isinstance(repo, dict) or repo.get("id") != repo_id:
                    continue
                display_name = repo.get("displayName")
                repo_path = repo.get("path")
                if isinstance(display_name, str) and display_name:
                    project = display_name
                elif isinstance(repo_path, str) and repo_path:
                    project = Path(repo_path).name
                break

        if project is None and isinstance(worktree_id, str) and "::" in worktree_id:
            project = Path(worktree_id.split("::", 1)[1]).name

        return OrcaFocus(
            repo_id=repo_id if isinstance(repo_id, str) else None,
            worktree_id=worktree_id if isinstance(worktree_id, str) else None,
            tab_id=tab_id if isinstance(tab_id, str) else None,
            project=project,
        )

    @staticmethod
    def _process_environment(proc_dir: Path) -> dict[str, str]:
        result: dict[str, str] = {}
        for item in (proc_dir / "environ").read_bytes().split(b"\0"):
            if b"=" not in item:
                continue
            key, value = item.split(b"=", 1)
            result[key.decode(errors="replace")] = value.decode(errors="replace")
        return result

    @staticmethod
    def _identify_agent(executable: str, argv: list[str]) -> str | None:
        names = [Path(executable).name, *(Path(arg).name for arg in argv[:3])]
        for name in names:
            normalized = name.lower()
            if normalized.endswith((".js", ".mjs", ".cjs")):
                normalized = Path(normalized).stem
            if normalized in AGENT_BY_EXECUTABLE:
                return normalized
        return None

    @staticmethod
    def _model_from_arguments(argv: list[str]) -> str | None:
        for index, arg in enumerate(argv):
            if arg in ("--model", "-m") and index + 1 < len(argv):
                return argv[index + 1]
            if arg.startswith("--model="):
                return arg.split("=", 1)[1]
        return None

    @staticmethod
    def model_from_record(record: dict) -> str | None:
        message = record.get("message")
        if isinstance(message, dict) and message.get("role") == "assistant":
            candidate = message.get("model")
            if isinstance(candidate, str) and candidate:
                return candidate.rsplit("/", 1)[-1]

        if record.get("type") in ("model_change", "modelChange"):
            data = record.get("data")
            candidate = (
                data.get("model") if isinstance(data, dict) else record.get("model")
            )
            if isinstance(candidate, str) and candidate:
                return candidate.rsplit("/", 1)[-1]
        return None

    @staticmethod
    def title_from_record(record: dict) -> str | None:
        if record.get("type") not in ("title", "title_change", "session"):
            return None
        candidate = record.get("title")
        if isinstance(candidate, str) and candidate.strip():
            return candidate.strip()
        return None

    def read_omp_metadata(self, session_path: Path) -> tuple[str | None, str | None]:
        stat = session_path.stat()
        cached = self.session_cache.get(session_path)
        cache_key = (stat.st_mtime_ns, stat.st_size)
        if cached is not None and cached[:2] == cache_key:
            return cached[2], cached[3]

        model = cached[2] if cached is not None else None
        title = cached[3] if cached is not None else None
        offset = cached[1] if cached is not None and stat.st_size >= cached[1] else 0

        with session_path.open("rb") as stream:
            first_line = stream.readline()
            try:
                first_record = json.loads(first_line)
            except json.JSONDecodeError:
                first_record = None
            if isinstance(first_record, dict):
                current_title = self.title_from_record(first_record)
                if current_title is not None:
                    title = current_title

            stream.seek(offset if offset >= len(first_line) else 0)
            for line in stream:
                try:
                    record = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if not isinstance(record, dict):
                    continue
                current_model = self.model_from_record(record)
                if current_model is not None:
                    model = current_model
                current_title = self.title_from_record(record)
                if current_title is not None:
                    title = current_title

        self.session_cache[session_path] = (*cache_key, model, title)
        return model, title

    def _omp_metadata_for_pid(self, pid: int) -> tuple[str | None, str | None]:
        try:
            tty = Path(os.readlink(f"/proc/{pid}/fd/0"))
            if tty.parent != Path("/dev/pts"):
                return None, None
            pointer = self.paths.omp_terminal_sessions / f"pts-{tty.name}"
            pointer_lines = pointer.read_text().splitlines()
            return self.read_omp_metadata(Path(pointer_lines[-1]))
        except (
            FileNotFoundError,
            PermissionError,
            ProcessLookupError,
            IndexError,
            OSError,
        ):
            return None, None

    def scan_agent_sessions(self) -> list[AgentSession]:
        sessions_by_tab: dict[str, AgentSession] = {}
        for proc_dir in Path("/proc").iterdir():
            if not proc_dir.name.isdigit():
                continue
            try:
                executable = os.readlink(proc_dir / "exe")
                argv = [
                    arg.decode(errors="replace")
                    for arg in (proc_dir / "cmdline").read_bytes().split(b"\0")
                    if arg
                ]
                agent_key = self._identify_agent(executable, argv)
                if agent_key is None or any(
                    arg.startswith("__omp_worker") for arg in argv
                ):
                    continue
                environment = self._process_environment(proc_dir)
                tab_id = environment.get("ORCA_TAB_ID")
                if not tab_id:
                    continue
                pid = int(proc_dir.name)
                started_at = self._process_start_time(pid)
                cwd = Path(os.readlink(proc_dir / "cwd"))
            except (
                FileNotFoundError,
                PermissionError,
                ProcessLookupError,
                UnicodeError,
                ValueError,
            ):
                continue

            agent = AGENT_BY_EXECUTABLE[agent_key]
            if agent_key == "omp":
                model, session_name = self._omp_metadata_for_pid(pid)
                small_image = self.omp_small_image
            else:
                model = self._model_from_arguments(argv)
                session_name = None
                small_image = None

            if model:
                self.last_model_by_tab[tab_id] = model
            else:
                model = self.last_model_by_tab.get(tab_id)
            if session_name:
                self.last_session_name_by_tab[tab_id] = session_name
            else:
                session_name = self.last_session_name_by_tab.get(tab_id)

            session = AgentSession(
                pid=pid,
                tab_id=tab_id,
                worktree_id=environment.get("ORCA_WORKTREE_ID"),
                cwd=cwd,
                started_at=started_at,
                agent=agent,
                model=model,
                session_name=session_name,
                small_image=small_image,
            )
            existing = sessions_by_tab.get(tab_id)
            if existing is None or session.started_at > existing.started_at:
                sessions_by_tab[tab_id] = session
        return list(sessions_by_tab.values())

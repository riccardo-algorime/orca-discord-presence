# Orca Discord Presence

Focus-aware Discord Rich Presence for Orca ADE on Linux.

Instead of Discord's generic `orca-ide` process detection, this companion publishes the project, AI model, true OMP session title, session timer, Orca artwork, and an oh-my-pi badge:

```text
Orca ADE
Trident-APE · GPT-5.6 Sol
Resolve Trident APE product outcome
12:08:31 elapsed
```

This is an independent community project. It is not affiliated with Discord or Orca.

## What it does

- Follows the project and tab currently focused in Orca.
- Joins Orca's `activeTabId` to the agent process through `ORCA_TAB_ID`.
- Reads the real OMP session title and current model from the local JSONL session.
- Preserves each agent process's original start time when you switch away and back.
- Falls back to the newest agent in the active worktree when the focused tab is not an agent.
- Clears the activity when Orca closes.
- Reconnects quietly when Discord starts later or restarts.
- Starts automatically at desktop login through a systemd user service.

## Requirements

- Linux with systemd user services
- Discord desktop
- Orca ADE installed at `/opt/Orca/orca-ide` by default
- Python 3.11 or newer with `venv`
- oh-my-pi for model and session-title detection; Codex, Claude, and Gemini process detection is also supported

No bot token, OAuth flow, Discord public key, or sudo access is required.

## Install

```bash
git clone https://github.com/riccardo-algorime/orca-discord-presence.git
cd orca-discord-presence
./install.sh
```

The installer creates:

```text
~/.local/share/orca-discord-presence/venv/
~/.config/orca-discord-presence/config.toml
~/.config/systemd/user/orca-discord-presence.service
```

Check it:

```bash
systemctl --user status orca-discord-presence.service
journalctl --user -u orca-discord-presence.service -f
```

Inspect the resolved activity without connecting to Discord:

```bash
~/.local/share/orca-discord-presence/venv/bin/orca-discord-presence --once
```

## Configuration

Edit:

```text
~/.config/orca-discord-presence/config.toml
```

The default configuration is in [`config.example.toml`](config.example.toml).
Restart after a change:

```bash
systemctl --user restart orca-discord-presence.service
```

### Privacy

Project and session titles can contain private work information. Disable any field before streaming or working on confidential repositories:

```toml
[privacy]
show_project = true
show_session = false
show_model = true
```

The daemon reads process metadata, Orca state, and OMP session metadata locally. It sends Discord only the fields visible in the Rich Presence. It does not send prompts, responses, source files, environment variables, or repository contents.

### Custom Discord application

The bundled Client ID is public and provides the `orca` and `omp1-transparent` artwork. To use your own Discord Developer Application, override:

```toml
[discord]
client_id = "YOUR_APPLICATION_ID"
large_image = "orca"
large_text = "Orca ADE"
omp_small_image = "omp1-transparent"
```

Upload assets with matching keys in the Discord Developer Portal. Set `omp_small_image = ""` to disable the small badge.

### Nonstandard paths

```toml
[paths]
orca_executable = "/opt/Orca/orca-ide"
orca_config = "~/.config/orca"
omp_terminal_sessions = "~/.omp/agent/terminal-sessions"
```

## Update

```bash
cd ~/lavoro/orca-discord-presence
git pull
./install.sh
```

The installer upgrades the dedicated virtual environment, preserves your configuration, and restarts the user service.

## Uninstall

Preserve configuration:

```bash
./uninstall.sh
```

Remove everything, including configuration:

```bash
./uninstall.sh --purge
```

## How focus selection works

1. The active Orca profile points to its live `orca-data.json`.
2. `workspaceSession` supplies `activeRepoId`, `activeWorktreeId`, and `activeTabId`.
3. Orca-launched agents inherit `ORCA_TAB_ID` and `ORCA_WORKTREE_ID`.
4. The matching agent process supplies its CWD and kernel process start time.
5. For OMP, the process TTY points to its JSONL session, which supplies model and title changes.

The daemon polls every two seconds and refreshes Discord every fifteen seconds. These values are configurable.

## Development

Run the standard-library test suite:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

Run live discovery from the source checkout after installing dependencies:

```bash
PYTHONPATH=src python3 -m orca_discord_presence --once
```

## License

[MIT](LICENSE)

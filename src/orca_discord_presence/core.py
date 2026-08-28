from __future__ import annotations

from .models import Activity, AgentSession, OrcaFocus, PrivacyConfig

DISCORD_FIELD_LIMIT = 128


def format_model(model: str) -> str:
    words = model.replace("_", "-").split("-")
    if words and words[0].lower() == "gpt":
        head = f"GPT-{words[1]}" if len(words) > 1 else "GPT"
        return " ".join(
            [head, *(word[:1].upper() + word[1:] for word in words[2:])]
        )

    formatted = []
    for word in words:
        lower = word.lower()
        if lower in {"o1", "o3", "o4"}:
            formatted.append(lower.upper())
        else:
            formatted.append(word[:1].upper() + word[1:])
    return " ".join(formatted)


def _clip(value: str) -> str:
    if len(value) <= DISCORD_FIELD_LIMIT:
        return value
    return f"{value[: DISCORD_FIELD_LIMIT - 1]}…"


def _select_session(
    focus: OrcaFocus | None, sessions: list[AgentSession]
) -> tuple[AgentSession | None, bool, int]:
    if focus is not None and focus.tab_id is not None:
        exact = next(
            (session for session in sessions if session.tab_id == focus.tab_id), None
        )
        if exact is not None:
            return exact, True, 1

    if focus is not None and focus.worktree_id is not None:
        candidates = [
            session
            for session in sessions
            if session.worktree_id == focus.worktree_id
        ]
    elif focus is None:
        candidates = sessions
    else:
        candidates = []

    if not candidates:
        return None, False, 0
    return max(candidates, key=lambda session: session.started_at), False, len(
        candidates
    )


def choose_activity(
    focus: OrcaFocus | None,
    sessions: list[AgentSession],
    orca_started_at: int,
    privacy: PrivacyConfig,
) -> Activity:
    selected, exact_focus, candidate_count = _select_session(focus, sessions)
    project = (
        focus.project
        if focus is not None and focus.project
        else selected.cwd.name if selected is not None else "Orca ADE"
    )

    if selected is None:
        details = project if privacy.show_project else "Orca ADE"
        return Activity(
            details=_clip(details),
            state="Orca ADE",
            started_at=orca_started_at,
            small_image=None,
            small_text=None,
        )

    model_parts = [] if selected.agent == "oh-my-pi" else [selected.agent]
    if selected.model:
        model_parts.append(format_model(selected.model))
    if not model_parts:
        model_parts.append("Model loading")
    model_text = " · ".join(model_parts)

    if privacy.show_session and selected.session_name:
        headline_parts = []
        if privacy.show_project:
            headline_parts.append(project)
        if privacy.show_model:
            headline_parts.append(model_text)
        details = " · ".join(headline_parts) or "Orca ADE"
        state = selected.session_name
    else:
        details = project if privacy.show_project else "Orca ADE"
        state = model_text if privacy.show_model else selected.agent

    if not exact_focus and candidate_count > 1:
        state = f"{state} · {candidate_count} sessions"

    return Activity(
        details=_clip(details),
        state=_clip(state),
        started_at=selected.started_at,
        small_image=selected.small_image,
        small_text=selected.agent,
    )

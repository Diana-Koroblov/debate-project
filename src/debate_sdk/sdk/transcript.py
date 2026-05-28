"""Transcript formatting and persistence for debate sessions."""

from __future__ import annotations

from pathlib import Path
from typing import Any


def build_transcript_markdown(
    events: list[dict[str, Any]],
    final_judgment: dict[str, Any],
    session_id: str,
) -> str:
    """Render a readable per-session transcript artifact."""
    lines = [
        f"# Debate Transcript {session_id}",
        "",
        "```text",
    ]

    for event in events:
        if event.get("type") != "argument":
            continue
        agent_id = event.get("agent_id", "unknown")
        round_number = event.get("round_number", "?")
        payload = event.get("payload", {})
        text = str(payload.get("text", "")).strip()
        lines.append(f"[{agent_id}] Round {round_number}")
        lines.append(text)

        citations = payload.get("citations", [])
        if citations:
            lines.append("Citations:")
            for citation in citations:
                title = citation.get("title", "Untitled source")
                url = citation.get("url", "")
                lines.append(f"- {title}: {url}" if url else f"- {title}")
        lines.append("")

    lines.append("[judge] Final Judgment")
    lines.append(f"Winner: {final_judgment.get('winner_id', 'unknown')}")
    lines.append(
        f"Differential score: {final_judgment.get('differential_score', 0)}"
    )

    for item in final_judgment.get("justification", []):
        if isinstance(item, dict):
            point = item.get("point", "")
            evidence = item.get("evidence", "")
            detail = f"{point}: {evidence}".strip(": ")
            if detail:
                lines.append(f"- {detail}")

    lines.extend(["```", ""])
    return "\n".join(lines)


def write_transcript(
    transcript_markdown: str,
    results_dir: Path | str,
    session_id: str,
) -> Path:
    """Persist the transcript artifact into the results directory."""
    target_dir = Path(results_dir)
    target_dir.mkdir(parents=True, exist_ok=True)
    path = target_dir / f"transcript_{session_id}.md"
    path.write_text(transcript_markdown, encoding="utf-8")
    return path
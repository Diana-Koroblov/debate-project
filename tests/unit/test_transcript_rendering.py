from debate_sdk.sdk.transcript import build_transcript_markdown, write_transcript


def test_build_transcript_markdown_skips_non_arguments_and_formats_citations():
    events = [
        {"type": "topic_selected", "topic": "Ignored"},
        {
            "type": "argument",
            "agent_id": "pro_agent",
            "round_number": 1,
            "payload": {
                "text": "Opening point.",
                "citations": [
                    {"title": "Paper A", "url": "https://example.com/a"},
                    {"title": "Paper B"},
                ],
            },
        },
    ]
    judgment = {
        "winner_id": "pro_agent",
        "differential_score": 2.5,
        "justification": [
            {"point": "Evidence", "evidence": "Cited a source."},
            {"point": "", "evidence": ""},
        ],
    }

    rendered = build_transcript_markdown(events, judgment, "session-1")

    assert "Topic: Topic not provided" in rendered
    assert "[pro_agent] Round 1" in rendered
    assert "- Paper A: https://example.com/a" in rendered
    assert "- Paper B" in rendered
    assert "- Evidence: Cited a source." in rendered


def test_write_transcript_persists_markdown(tmp_path):
    path = write_transcript("# demo\n", tmp_path, "abc123")

    assert path == tmp_path / "transcript_abc123.md"
    assert path.read_text(encoding="utf-8") == "# demo\n"
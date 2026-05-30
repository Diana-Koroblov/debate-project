from threading import Event

from debate_sdk.sdk.logstream import follow_logs


def test_follow_logs_reads_appended_lines_after_initial_empty_pass(monkeypatch, tmp_path):
    log_path = tmp_path / "agent_logs_01.log"
    log_path.write_text("", encoding="utf-8")
    lines = []
    stop_event = Event()
    state = {"slept": False}

    def on_line(line: str) -> None:
        lines.append(line)
        if len(lines) == 2:
            stop_event.set()

    def fake_sleep(_: float) -> None:
        if not state["slept"]:
            log_path.write_text("first\nsecond\n", encoding="utf-8")
            state["slept"] = True

    monkeypatch.setattr("debate_sdk.sdk.logstream.time.sleep", fake_sleep)

    follow_logs(tmp_path, stop_event, on_line, poll_interval=0)

    assert lines == ["first", "second"]
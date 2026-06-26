import json
import logging

from raqe.observability.logging import log_stage


def test_log_stage_emits_json_payload(caplog) -> None:
    caplog.set_level(logging.INFO, logger="raqe")
    log_stage("execution_complete", {"documents": 2, "chunks": 5})
    assert len(caplog.records) == 1
    message = caplog.records[0].getMessage()
    payload = json.loads(message)
    assert payload["stage"] == "execution_complete"
    assert payload["documents"] == 2
    assert payload["chunks"] == 5

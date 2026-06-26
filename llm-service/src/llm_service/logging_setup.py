from __future__ import annotations

import logging
import sys


def configure_logging(*, debug: bool) -> None:
    level = logging.DEBUG if debug else logging.INFO
    root = logging.getLogger()
    if not root.handlers:
        logging.basicConfig(
            level=level,
            format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
            stream=sys.stdout,
        )
    else:
        root.setLevel(level)
    logging.getLogger("llm_service").setLevel(level)


def configure_litellm_debug(*, enabled: bool) -> None:
    if not enabled:
        return
    log = logging.getLogger(__name__)
    try:
        import litellm

        litellm._turn_on_debug()
        if hasattr(litellm, "set_verbose"):
            litellm.set_verbose(True)
        log.info("LiteLLM debug enabled (_turn_on_debug)")
    except Exception as e:
        log.warning("Failed to enable LiteLLM debug: %s", e)

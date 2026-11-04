from __future__ import annotations

import logging
import threading
from typing import Optional

from fake_useragent import UserAgent

from ..core.settings import get_config_value

logger = logging.getLogger(__name__)

_resolved_user_agent: Optional[str] = None
_lock = threading.Lock()
_DEFAULT_FALLBACK_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/131.0.0.0 Safari/537.36"
)


def init_user_agent_async() -> None:
    thread = threading.Thread(
        target=get_user_agent,
        name="capri-user-agent-init",
        daemon=True,
    )
    thread.start()


def get_user_agent() -> str:
    global _resolved_user_agent

    if _resolved_user_agent is not None:
        return _resolved_user_agent

    with _lock:
        if _resolved_user_agent is not None:
            return _resolved_user_agent

        try:
            custom_ua = get_config_value("network.user_agent")
            if custom_ua and isinstance(custom_ua, str) and custom_ua.strip():
                _resolved_user_agent = custom_ua.strip()
                logger.debug("Используется пользовательский User-Agent из конфига: %s", _resolved_user_agent)
                return _resolved_user_agent
        except Exception as e:
            logger.debug("Не удалось прочитать User-Agent из конфига: %s", e)

        try:
            ua = UserAgent(platforms="pc", fallback=_DEFAULT_FALLBACK_UA)
            _resolved_user_agent = str(ua.random)
            logger.debug("Сгенерирован User-Agent через fake-useragent: %s", _resolved_user_agent)
        except Exception as e:
            logger.warning("Ошибка fake-useragent, используется fallback: %s", e)
            _resolved_user_agent = _DEFAULT_FALLBACK_UA

        return _resolved_user_agent

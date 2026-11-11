"""Модуль интеграции с Windows Core Audio API для управления системной громкостью.

Использует интерфейс IAudioEndpointVolume через pycaw для прямого аппаратного
контроля общей громкости Windows, уровней децибел и состояния Mute.
"""

from __future__ import annotations

import contextlib
import logging

import comtypes
from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume

logger = logging.getLogger(__name__)


class SystemVolumeService:
    """Сервис управления общей мастер-громкостью Windows Core Audio."""

    _instance: SystemVolumeService | None = None

    def __init__(self) -> None:
        self._endpoint: IAudioEndpointVolume | None = None

    @classmethod
    def get_instance(cls) -> SystemVolumeService:
        """Получить синглтон-экземпляр сервиса системной громкости."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _ensure_endpoint(self) -> IAudioEndpointVolume | None:
        """Инициализировать или вернуть кэшированный аудио-эндпоинт с поддержкой COM."""
        with contextlib.suppress(Exception):
            comtypes.CoInitialize()

        try:
            device = AudioUtilities.GetSpeakers()
            if device is None:
                logger.warning("Устройство вывода звука по умолчанию не найдено.")
                return None
            return device.EndpointVolume
        except (comtypes.COMError, OSError, AttributeError) as exc:
            logger.error("Ошибка при получении IAudioEndpointVolume: %s", exc)
            return None

    def get_volume(self) -> int:
        """Получить текущую громкость в процентах (0–100)."""
        endpoint = self._ensure_endpoint()
        if endpoint is None:
            return 50
        try:
            scalar: float = endpoint.GetMasterVolumeLevelScalar()
            return round(scalar * 100.0)
        except (comtypes.COMError, OSError, AttributeError) as exc:
            logger.error("Ошибка чтения громкости: %s", exc)
            return 50

    def set_volume(self, percent: int) -> int:
        """Установить мастер-громкость в процентах (0–100).

        Возвращает фактически установленный процент громкости.
        """
        clamped = max(0, min(100, int(percent)))
        endpoint = self._ensure_endpoint()
        if endpoint is None:
            return clamped
        try:
            scalar = clamped / 100.0
            endpoint.SetMasterVolumeLevelScalar(scalar, None)
            # Если звук был заглушен и громкость поднята > 0, автоматически снимаем mute
            if clamped > 0 and self.is_muted():
                self.set_mute(False)
            return clamped
        except (comtypes.COMError, OSError, AttributeError) as exc:
            logger.error("Ошибка установки громкости на %d%%: %s", clamped, exc)
            return clamped

    def change_volume(self, delta: int) -> int:
        """Относительное изменение громкости на delta процентов.

        Возвращает новый процент громкости.
        """
        current = self.get_volume()
        target = current + delta
        return self.set_volume(target)

    def is_muted(self) -> bool:
        """Проверить, выключен ли звук (Mute)."""
        endpoint = self._ensure_endpoint()
        if endpoint is None:
            return False
        try:
            return bool(endpoint.GetMute())
        except (comtypes.COMError, OSError, AttributeError) as exc:
            logger.error("Ошибка чтения статуса mute: %s", exc)
            return False

    def set_mute(self, mute: bool) -> bool:
        """Включить или выключить приглушение звука (Mute).

        Возвращает новое состояние mute.
        """
        endpoint = self._ensure_endpoint()
        if endpoint is None:
            return mute
        try:
            endpoint.SetMute(1 if mute else 0, None)
            return mute
        except (comtypes.COMError, OSError, AttributeError) as exc:
            logger.error("Ошибка изменения mute на %s: %s", mute, exc)
            return mute

    def toggle_mute(self) -> bool:
        """Переключить состояние mute на противоположное.

        Возвращает новое состояние mute.
        """
        return self.set_mute(not self.is_muted())

    def get_volume_db(self) -> float:
        """Получить текущий уровень громкости в децибелах (dB)."""
        endpoint = self._ensure_endpoint()
        if endpoint is None:
            return 0.0
        try:
            return float(endpoint.GetMasterVolumeLevel())
        except (comtypes.COMError, OSError, AttributeError) as exc:
            logger.error("Ошибка чтения уровня громкости в dB: %s", exc)
            return 0.0


def get_system_volume_service() -> SystemVolumeService:
    """Глобальный аксессор к сервису управления мастер-громкостью Windows."""
    return SystemVolumeService.get_instance()

"""Синтез и воспроизведение звуковых эффектов речи и интерфейса.

Управляет воспроизведением процедурных аудиофайлов через QSoundEffect.
Математика синтеза PCM-волн вынесена в capri.audio.sfx_generators.
"""

from __future__ import annotations

import logging
import tempfile
import time
from pathlib import Path

from PySide6.QtCore import QObject, QUrl
from PySide6.QtMultimedia import QMediaDevices, QSoundEffect

from ..audio.sfx_generators import (
    SFX_VERSION,
    _ensure_wav_cache_sync,
    _generate_session_lock_wav,
    _generate_session_power_wav,
    _generate_session_reboot_wav,
    _generate_session_suspend_wav,
    preload_sfx_cache_async,
)

logger = logging.getLogger(__name__)


class SpeechSFX(QObject):
    """Менеджер процедурных звуковых эффектов речи и интерфейсных событий."""

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._enabled = True
        self._speech_sound_enabled = True
        self._effects_sound_enabled = True
        self._volume = 0.5
        self._throttle_interval = 0.045
        self._last_chirp_time = 0.0
        self._available = False

        self._swoosh_path: Path | None = None
        self._close_path: Path | None = None
        self._chirp_path: Path | None = None
        self._lightning_strike_path: Path | None = None
        self._lightning_arc_path: Path | None = None
        self._lightning_zap_path: Path | None = None
        self._target_acquired_path: Path | None = None
        self._data_rip_path: Path | None = None
        self._voice_start_path: Path | None = None
        self._voice_success_path: Path | None = None
        self._voice_cancel_path: Path | None = None
        self._core_destabilize_path: Path | None = None
        self._session_paths: dict[str, Path] = {}

        self._swoosh_effect: QSoundEffect | None = None
        self._close_effect: QSoundEffect | None = None
        self._lightning_strike_effect: QSoundEffect | None = None
        self._lightning_arc_effect: QSoundEffect | None = None
        self._lightning_zap_effect: QSoundEffect | None = None
        self._target_acquired_effect: QSoundEffect | None = None
        self._data_rip_effect: QSoundEffect | None = None
        self._voice_start_effect: QSoundEffect | None = None
        self._voice_success_effect: QSoundEffect | None = None
        self._voice_cancel_effect: QSoundEffect | None = None
        self._core_destabilize_effect: QSoundEffect | None = None
        self._session_effects: dict[str, QSoundEffect] = {}
        self._chirp_pool: list[QSoundEffect] = []
        self._chirp_index = 0
        self._chirp_pools_by_style: dict[str, list[QSoundEffect]] = {}
        self._chirp_indices_by_style: dict[str, int] = {}
        self._chirp_paths_by_style: dict[str, Path] = {}
        self._suppressed = False

        self._media_devices = QMediaDevices(self)
        self._media_devices.audioOutputsChanged.connect(
            self._on_audio_outputs_changed
        )

        self._init_sounds()

    def _init_sounds(self) -> None:
        try:
            temp_dir = Path(tempfile.gettempdir()) / f"capri_sfx_{SFX_VERSION}"
            swoosh_path = temp_dir / "cyber_swoosh.wav"
            close_path = temp_dir / "cyber_close.wav"
            chirp_path = temp_dir / "retro_chirp.wav"
            strike_path = temp_dir / "cyber_lightning_strike.wav"
            arc_path = temp_dir / "cyber_lightning_arc.wav"
            zap_path = temp_dir / "cyber_lightning_zap.wav"
            drop_path = temp_dir / "cyber_teleport_drop.wav"
            target_path = temp_dir / "cyber_target_acquired.wav"
            data_rip_path = temp_dir / "cyber_data_rip.wav"
            voice_start_path = temp_dir / "cyber_voice_start.wav"
            voice_success_path = temp_dir / "cyber_voice_success.wav"
            voice_cancel_path = temp_dir / "cyber_voice_cancel.wav"
            core_destabilize_path = temp_dir / "cyber_core_destabilize.wav"
            relay_snap_path = temp_dir / "cyber_relay_snap.wav"
            intro_breach_path = temp_dir / "cyber_intro_breach.wav"

            session_specs = {
                "lock": (
                    "cyber_session_lock.wav",
                    _generate_session_lock_wav,
                ),
                "power_off": (
                    "cyber_session_power.wav",
                    _generate_session_power_wav,
                ),
                "suspend": (
                    "cyber_session_suspend.wav",
                    _generate_session_suspend_wav,
                ),
                "reboot": (
                    "cyber_session_reboot.wav",
                    _generate_session_reboot_wav,
                ),
            }

            _ensure_wav_cache_sync(temp_dir)

            self._swoosh_path = swoosh_path
            self._close_path = close_path
            self._chirp_path = chirp_path
            self._lightning_strike_path = strike_path
            self._lightning_arc_path = arc_path
            self._lightning_zap_path = zap_path
            self._teleport_drop_path = drop_path
            self._target_acquired_path = target_path
            self._data_rip_path = data_rip_path
            self._voice_start_path = voice_start_path
            self._voice_success_path = voice_success_path
            self._voice_cancel_path = voice_cancel_path
            self._core_destabilize_path = core_destabilize_path
            self._relay_snap_path = relay_snap_path
            self._intro_breach_path = intro_breach_path

            for action, (filename, _generator) in session_specs.items():
                path = temp_dir / filename
                self._session_paths[action] = path
                effect = QSoundEffect(self)
                effect.setSource(QUrl.fromLocalFile(str(path)))
                effect.setVolume(self._volume * 0.85)
                self._session_effects[action] = effect

            swoosh = QSoundEffect(self)
            swoosh.setSource(QUrl.fromLocalFile(str(swoosh_path)))
            swoosh.setVolume(self._volume)
            self._swoosh_effect = swoosh

            close_sfx = QSoundEffect(self)
            close_sfx.setSource(QUrl.fromLocalFile(str(close_path)))
            close_sfx.setVolume(self._volume)
            self._close_effect = close_sfx

            strike_sfx = QSoundEffect(self)
            strike_sfx.setSource(QUrl.fromLocalFile(str(strike_path)))
            strike_sfx.setVolume(self._volume)
            self._lightning_strike_effect = strike_sfx

            arc_sfx = QSoundEffect(self)
            arc_sfx.setSource(QUrl.fromLocalFile(str(arc_path)))
            arc_sfx.setVolume(self._volume * 0.85)
            self._lightning_arc_effect = arc_sfx

            zap_sfx = QSoundEffect(self)
            zap_sfx.setSource(QUrl.fromLocalFile(str(zap_path)))
            zap_sfx.setVolume(self._volume * 0.75)
            self._lightning_zap_effect = zap_sfx

            drop_sfx = QSoundEffect(self)
            drop_sfx.setSource(QUrl.fromLocalFile(str(drop_path)))
            drop_sfx.setVolume(self._volume * 0.95)
            self._teleport_drop_effect = drop_sfx

            target_sfx = QSoundEffect(self)
            target_sfx.setSource(QUrl.fromLocalFile(str(target_path)))
            target_sfx.setVolume(self._volume * 0.8)
            self._target_acquired_effect = target_sfx

            rip_sfx = QSoundEffect(self)
            rip_sfx.setSource(QUrl.fromLocalFile(str(data_rip_path)))
            rip_sfx.setVolume(self._volume * 0.9)
            self._data_rip_effect = rip_sfx

            v_start_sfx = QSoundEffect(self)
            v_start_sfx.setSource(QUrl.fromLocalFile(str(voice_start_path)))
            v_start_sfx.setVolume(self._volume * 0.85)
            self._voice_start_effect = v_start_sfx

            v_succ_sfx = QSoundEffect(self)
            v_succ_sfx.setSource(QUrl.fromLocalFile(str(voice_success_path)))
            v_succ_sfx.setVolume(self._volume * 0.85)
            self._voice_success_effect = v_succ_sfx

            v_canc_sfx = QSoundEffect(self)
            v_canc_sfx.setSource(QUrl.fromLocalFile(str(voice_cancel_path)))
            v_canc_sfx.setVolume(self._volume * 0.8)
            self._voice_cancel_effect = v_canc_sfx

            core_destab_sfx = QSoundEffect(self)
            core_destab_sfx.setSource(QUrl.fromLocalFile(str(core_destabilize_path)))
            core_destab_sfx.setVolume(self._volume * 0.8)
            self._core_destabilize_effect = core_destab_sfx

            relay_sfx = QSoundEffect(self)
            relay_sfx.setSource(QUrl.fromLocalFile(str(relay_snap_path)))
            relay_sfx.setVolume(self._volume * 0.9)
            self._relay_snap_effect = relay_sfx

            intro_breach_sfx = QSoundEffect(self)
            intro_breach_sfx.setSource(QUrl.fromLocalFile(str(intro_breach_path)))
            intro_breach_sfx.setVolume(self._volume * 0.95)
            self._intro_breach_effect = intro_breach_sfx

            # Пул эмоциональных звуков речи
            self._chirp_paths_by_style = {}
            self._chirp_pools_by_style = {}
            self._chirp_indices_by_style = {}
            styles = ("normal", "exclamation", "question", "ellipsis")
            for st in styles:
                st_path = temp_dir / f"cyber_chirp_{st}.wav"
                self._chirp_paths_by_style[st] = st_path
                st_pool: list[QSoundEffect] = []
                st_url = QUrl.fromLocalFile(str(st_path))
                for _ in range(3):
                    eff = QSoundEffect(self)
                    eff.setSource(st_url)
                    eff.setVolume(self._volume * (0.85 if st == "exclamation" else 0.7))
                    st_pool.append(eff)
                self._chirp_pools_by_style[st] = st_pool
                self._chirp_indices_by_style[st] = 0

            self._chirp_pool = self._chirp_pools_by_style.get("normal", [])
            self._chirp_path = self._chirp_paths_by_style.get("normal", chirp_path)

            self._available = True
        except (OSError, RuntimeError, ValueError) as exc:
            logger.warning(
                "Не удалось инициализировать SFX звуки: %s. Работаем в беззвучном режиме.",
                exc,
            )
            self._available = False

    def _on_audio_outputs_changed(self) -> None:
        self.reload_audio_devices()

    def reload_audio_devices(self) -> None:
        try:
            self._init_sounds()
        except (OSError, RuntimeError, ValueError) as exc:
            logger.debug("SFX device reload failed: %s", exc)

    def _play_file(
        self, path: Path | None, fallback_effect: QSoundEffect | None
    ) -> None:
        if not self.is_enabled() or fallback_effect is None:
            return
        try:
            if (
                fallback_effect.status() == QSoundEffect.Status.Error
                and path is not None
                and path.exists()
            ):
                fallback_effect.setSource(QUrl.fromLocalFile(str(path)))
            fallback_effect.play()
        except (RuntimeError, OSError) as exc:
            logger.debug("QSoundEffect error: %s", exc)

    @property
    def is_available(self) -> bool:
        return self._available

    def is_enabled(self) -> bool:
        return self._enabled and self._available and not self._suppressed

    def set_suppressed(self, suppressed: bool) -> None:
        self._suppressed = bool(suppressed)

    def set_enabled(self, enabled: bool) -> None:
        self._enabled = bool(enabled)

    def is_speech_sound_enabled(self) -> bool:
        return self._speech_sound_enabled and self.is_enabled()

    def set_speech_sound_enabled(self, enabled: bool) -> None:
        self._speech_sound_enabled = bool(enabled)

    def is_effects_sound_enabled(self) -> bool:
        return self._effects_sound_enabled and self.is_enabled()

    def set_effects_sound_enabled(self, enabled: bool) -> None:
        self._effects_sound_enabled = bool(enabled)

    def get_volume(self) -> float:
        return self._volume

    def set_volume(self, volume: float) -> None:
        self._volume = max(0.0, min(1.0, float(volume)))
        if self._swoosh_effect is not None:
            self._swoosh_effect.setVolume(self._volume)
        if self._close_effect is not None:
            self._close_effect.setVolume(self._volume)
        if self._lightning_strike_effect is not None:
            self._lightning_strike_effect.setVolume(self._volume)
        if self._lightning_arc_effect is not None:
            self._lightning_arc_effect.setVolume(self._volume * 0.85)
        if self._lightning_zap_effect is not None:
            self._lightning_zap_effect.setVolume(self._volume * 0.75)
        if (
            hasattr(self, "_teleport_drop_effect")
            and self._teleport_drop_effect is not None
        ):
            self._teleport_drop_effect.setVolume(self._volume * 0.95)
        if (
            hasattr(self, "_target_acquired_effect")
            and self._target_acquired_effect is not None
        ):
            self._target_acquired_effect.setVolume(self._volume * 0.8)
        if (
            hasattr(self, "_data_rip_effect")
            and self._data_rip_effect is not None
        ):
            self._data_rip_effect.setVolume(self._volume * 0.9)
        if (
            hasattr(self, "_voice_start_effect")
            and self._voice_start_effect is not None
        ):
            self._voice_start_effect.setVolume(self._volume * 0.85)
        if (
            hasattr(self, "_voice_success_effect")
            and self._voice_success_effect is not None
        ):
            self._voice_success_effect.setVolume(self._volume * 0.85)
        if (
            hasattr(self, "_voice_cancel_effect")
            and self._voice_cancel_effect is not None
        ):
            self._voice_cancel_effect.setVolume(self._volume * 0.8)
        if (
            hasattr(self, "_core_destabilize_effect")
            and self._core_destabilize_effect is not None
        ):
            self._core_destabilize_effect.setVolume(self._volume * 0.8)
        if (
            hasattr(self, "_relay_snap_effect")
            and self._relay_snap_effect is not None
        ):
            self._relay_snap_effect.setVolume(self._volume * 0.9)
        if (
            hasattr(self, "_intro_breach_effect")
            and self._intro_breach_effect is not None
        ):
            self._intro_breach_effect.setVolume(self._volume * 0.95)
        for effect in self._session_effects.values():
            effect.setVolume(self._volume * 0.85)
        for pool in self._chirp_pools_by_style.values():
            for effect in pool:
                effect.setVolume(self._volume * 0.7)

    def play_swoosh(self) -> None:
        if not self.is_speech_sound_enabled():
            return
        self._play_file(self._swoosh_path, self._swoosh_effect)

    def play_close(self) -> None:
        if not self.is_speech_sound_enabled():
            return
        self._play_file(self._close_path, self._close_effect)

    def play_lightning_strike(self) -> None:
        if not self.is_effects_sound_enabled():
            return
        self._play_file(
            self._lightning_strike_path, self._lightning_strike_effect
        )

    def play_lightning_arc(self) -> None:
        if not self.is_effects_sound_enabled():
            return
        self._play_file(
            self._lightning_arc_path, self._lightning_arc_effect
        )

    def play_lightning_zap(self) -> None:
        if not self.is_effects_sound_enabled():
            return
        self._play_file(
            self._lightning_zap_path, self._lightning_zap_effect
        )

    def play_teleport_drop(self) -> None:
        if not self.is_effects_sound_enabled():
            return
        self._play_file(
            getattr(self, "_teleport_drop_path", None),
            getattr(self, "_teleport_drop_effect", None),
        )

    def play_target_acquired(self) -> None:
        if not self.is_effects_sound_enabled():
            return
        self._play_file(
            getattr(self, "_target_acquired_path", None),
            getattr(self, "_target_acquired_effect", None),
        )

    def play_data_rip(self) -> None:
        if not self.is_effects_sound_enabled():
            return
        self._play_file(
            getattr(self, "_data_rip_path", None),
            getattr(self, "_data_rip_effect", None),
        )

    def play_voice_start(self) -> None:
        """Звук активации голосового прослушивания."""
        if not self.is_speech_sound_enabled():
            return
        self._play_file(
            getattr(self, "_voice_start_path", None),
            getattr(self, "_voice_start_effect", None),
        )

    def play_voice_success(self) -> None:
        """Звук успешного распознавания команды."""
        if not self.is_speech_sound_enabled():
            return
        self._play_file(
            getattr(self, "_voice_success_path", None),
            getattr(self, "_voice_success_effect", None),
        )

    def play_voice_cancel(self) -> None:
        """Звук отмены/сброса голосового ожидания."""
        if not self.is_speech_sound_enabled():
            return
        self._play_file(
            getattr(self, "_voice_cancel_path", None),
            getattr(self, "_voice_cancel_effect", None),
        )

    def play_core_destabilize(self) -> None:
        """Звук перегрузки и нарастающего напряжения ядра."""
        if not self.is_effects_sound_enabled():
            return
        self._play_file(
            getattr(self, "_core_destabilize_path", None),
            getattr(self, "_core_destabilize_effect", None),
        )

    def play_relay_snap(self) -> None:
        """Звук аппаратного переключения реле / разряда конденсатора при регулировке звука."""
        if not self.is_effects_sound_enabled():
            return
        self._play_file(
            getattr(self, "_relay_snap_path", None),
            getattr(self, "_relay_snap_effect", None),
        )

    def play_intro_breach(self) -> None:
        """Кинематографичный звук первого пробоя Blackwall (свист катушек + раскол стекла)."""
        if not self.is_effects_sound_enabled():
            return
        self._play_file(
            getattr(self, "_intro_breach_path", None),
            getattr(self, "_intro_breach_effect", None),
        )

    def play_session_action(self, action: str) -> None:
        if not self.is_effects_sound_enabled():
            return
        path = self._session_paths.get(action)
        self._play_file(path, self._session_effects.get(action))

    def play_chirp(self, char: str = "") -> None:
        """Воспроизводит фонетический импульс печати с учетом пунктуации."""
        if not self.is_speech_sound_enabled():
            return
        now = time.monotonic()
        if now - self._last_chirp_time < self._throttle_interval:
            return
        self._last_chirp_time = now

        # Определение стиля звучания по текущему символу
        style = "normal"
        if char in ("!", "¡"):
            style = "exclamation"
        elif char in ("?", "¿"):
            style = "question"
        elif char in (".", "…", "-", "—"):
            style = "ellipsis"

        pool = self._chirp_pools_by_style.get(style) or self._chirp_pool
        path = self._chirp_paths_by_style.get(style) or self._chirp_path
        if not pool or path is None:
            return

        idx = self._chirp_indices_by_style.get(style, 0)
        fallback = pool[idx]
        self._chirp_indices_by_style[style] = (idx + 1) % len(pool)

        self._play_file(path, fallback)

    def stop_all(self, timeout: float = 0.3) -> None:
        pass


class _SpeechSFXHolder:
    instance: SpeechSFX | None = None


def get_speech_sfx() -> SpeechSFX:
    if _SpeechSFXHolder.instance is None:
        _SpeechSFXHolder.instance = SpeechSFX()
    return _SpeechSFXHolder.instance


__all__ = [
    "SpeechSFX",
    "get_speech_sfx",
    "preload_sfx_cache_async",
]

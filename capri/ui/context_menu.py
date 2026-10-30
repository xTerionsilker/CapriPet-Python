from __future__ import annotations

from typing import Any

from PySide6.QtCore import QPoint
from PySide6.QtGui import QActionGroup, QGuiApplication
from PySide6.QtMultimedia import QMediaDevices
from PySide6.QtWidgets import QMenu, QWidget

from ..core.settings import ACTIVITY_TIMEOUT_OPTIONS_MS
from .cyber_menu import CyberMenu
from .speech_sfx import get_speech_sfx


class ContextMenuBuilder:
    """Конструктор контекстного меню для питомца Капри."""

    def __init__(self, window: Any) -> None:
        self.window = window

    def build(self, for_tray: bool = False) -> QMenu:
        """Создает и настраивает контекстное меню."""
        menu = CyberMenu(self.window if isinstance(self.window, QWidget) else None)

        if for_tray:
            call_act = menu.addAction("🐾  Позвать Капри")
            trigger_fn = getattr(
                self.window, "activate_command_mode", getattr(self.window, "show", None)
            )
            if trigger_fn is not None:
                call_act.triggered.connect(trigger_fn)
            font = call_act.font()
            font.setBold(True)
            call_act.setFont(font)
            menu.setDefaultAction(call_act)
            menu.addSeparator()

        # 1. Быстрые действия и переключатели (верхний приоритет)
        self._add_quick_actions(menu)

        menu.addSeparator()

        # 2. Аудиоинтерфейс (Звук, Микрофон, Громкость)
        self._add_audio_section(menu)

        menu.addSeparator()

        # 3. Визуальный блок и дисплей (Масштаб, Глитчи, Монитор)
        self._add_visual_section(menu)

        menu.addSeparator()

        # 4. Поведение и система (Таймаут сна, Напоминания)
        self._add_behavior_section(menu)

        menu.addSeparator()

        # 5. Завершение работы
        quit_act = menu.addAction("✖  Завершить работу")
        quit_act.triggered.connect(self.window.close)

        return menu

    def _add_submenu(self, parent_menu: QMenu, title: str) -> CyberMenu:
        submenu = CyberMenu(parent_menu, title=title)
        parent_menu.addMenu(submenu)
        return submenu

    def _add_quick_actions(self, parent_menu: QMenu) -> None:
        voice_listening = False
        if hasattr(self.window, "_voice"):
            voice_listening = self.window._voice.is_listening

        voice_act = parent_menu.addAction("🎙  Голосовой ввод")
        voice_act.setCheckable(True)
        voice_act.setChecked(voice_listening)
        voice_act.triggered.connect(
            lambda *_: (
                self.window.toggle_voice()
                if hasattr(self.window, "toggle_voice")
                else self.window._toggle_voice()
            )
        )

        glitches_enabled = getattr(self.window, "glitches_enabled", False)
        if not glitches_enabled and hasattr(self.window, "_glitches"):
            glitches_enabled = self.window._glitches.is_enabled

        glitch_act = parent_menu.addAction("⚡  Экранные глитчи")
        glitch_act.setCheckable(True)
        glitch_act.setChecked(glitches_enabled)
        glitch_act.triggered.connect(
            lambda *_: self.window.process_input("глитч")
        )

    def _add_audio_section(self, parent_menu: QMenu) -> None:
        # Аудио-блок
        self._add_sound_menu(parent_menu)
        self._add_volume_menu(parent_menu)
        self._add_microphone_menu(parent_menu)

    def _add_visual_section(self, parent_menu: QMenu) -> None:
        # Визуальные настройки
        self._add_scale_menu(parent_menu)
        self._add_glitch_intensity_menu(parent_menu)
        self._add_screen_menu(parent_menu)

    def _add_behavior_section(self, parent_menu: QMenu) -> None:
        # Поведение
        self._add_activity_timeout_menu(parent_menu)
        self._add_reminder_toggle(parent_menu)

    def _add_screen_menu(self, parent_menu: QMenu) -> None:
        screen_menu = self._add_submenu(parent_menu, "🖥  Монитор")
        screen_group = QActionGroup(screen_menu)
        screen_group.setExclusive(True)

        current_scr = self.window.get_designated_screen()
        primary_scr = QGuiApplication.primaryScreen()

        for scr in QGuiApplication.screens():
            geo = scr.geometry()
            name = scr.name()
            extra = []
            if primary_scr and scr.name() == primary_scr.name():
                extra.append("основной")
            extra_str = f" [{', '.join(extra)}]" if extra else ""
            label = f"{name} ({geo.width()}x{geo.height()}){extra_str}"

            action = screen_menu.addAction(label)
            action.setCheckable(True)
            if current_scr and scr.name() == current_scr.name():
                action.setChecked(True)
            action.triggered.connect(
                lambda *_, s=scr: self.window.set_designated_screen(s)
            )
            screen_group.addAction(action)

    def _add_microphone_menu(self, parent_menu: QMenu) -> None:
        mic_menu = self._add_submenu(parent_menu, "🎙  Входной микрофон")
        mic_group = QActionGroup(mic_menu)
        mic_group.setExclusive(True)

        current_mic = getattr(self.window, "selected_microphone", None)
        if current_mic is None and hasattr(self.window, "_voice"):
            current_mic = self.window._voice.selected_device

        default_mic = QMediaDevices.defaultAudioInput()
        default_label = (
            f"По умолчанию ({default_mic.description()})"
            if not default_mic.isNull()
            else "По умолчанию"
        )
        def_action = mic_menu.addAction(default_label)
        def_action.setCheckable(True)
        if current_mic is None or current_mic.isNull():
            def_action.setChecked(True)
        def_action.triggered.connect(
            lambda *_: self.window.set_designated_microphone(None)
        )
        mic_group.addAction(def_action)

        for dev in QMediaDevices.audioInputs():
            if not default_mic.isNull() and dev.id() == default_mic.id():
                continue
            act = mic_menu.addAction(dev.description())
            act.setCheckable(True)
            if current_mic and dev.id() == current_mic.id():
                act.setChecked(True)
            act.triggered.connect(
                lambda *_, d=dev: self.window.set_designated_microphone(d)
            )
            mic_group.addAction(act)

    def _add_sound_menu(self, parent_menu: QMenu) -> None:
        sound_menu = self._add_submenu(parent_menu, "🔊  Звуковые эффекты")
        speech_sfx = get_speech_sfx()

        msg_sound_act = sound_menu.addAction("💬  Синтез речи (SFX)")
        msg_sound_act.setCheckable(True)
        msg_sound_act.setChecked(speech_sfx.is_speech_sound_enabled())
        msg_sound_act.triggered.connect(
            lambda checked: self.window.set_speech_sound_enabled(checked)
        )

        fx_sound_act = sound_menu.addAction("⚡  UI эффекты")
        fx_sound_act.setCheckable(True)
        fx_sound_act.setChecked(speech_sfx.is_effects_sound_enabled())
        fx_sound_act.triggered.connect(
            lambda checked: self.window.set_effects_sound_enabled(checked)
        )

    def _add_volume_menu(self, parent_menu: QMenu) -> None:
        volume_menu = self._add_submenu(parent_menu, "🔉  Громкость SFX")
        volume_group = QActionGroup(volume_menu)
        volume_group.setExclusive(True)

        current_volume = getattr(self.window, "volume_percent", 50)
        for opt in (25, 50, 75, 100):
            act = volume_menu.addAction(f"{opt}%")
            act.setCheckable(True)
            if current_volume == opt:
                act.setChecked(True)
            act.triggered.connect(
                lambda *_, v=opt: self.window.set_master_volume(v)
            )
            volume_group.addAction(act)

    def _add_scale_menu(self, parent_menu: QMenu) -> None:
        size_menu = self._add_submenu(parent_menu, "📐  Масштаб проекции")
        size_group = QActionGroup(size_menu)
        size_group.setExclusive(True)

        current_scale = getattr(
            self.window, "scale_percent", getattr(self.window, "_scale_percent", 100)
        )
        scale_options = [50, 75, 100, 125, 150]
        for opt in scale_options:
            act = size_menu.addAction(f"{opt}%")
            act.setCheckable(True)
            if current_scale == opt:
                act.setChecked(True)
            act.triggered.connect(
                lambda *_, s=opt: self.window.set_sprite_scale(s)
            )
            size_group.addAction(act)

    def _add_glitch_intensity_menu(self, parent_menu: QMenu) -> None:
        intensity_menu = self._add_submenu(parent_menu, "⚡  Интенсивность глитчей")
        group = QActionGroup(intensity_menu)
        group.setExclusive(True)

        current_intensity = getattr(self.window, "glitch_intensity", "weak")
        options = (
            ("weak", "Низкая"),
            ("medium", "Средняя"),
            ("strong", "Максимальная"),
        )
        for key, label in options:
            act = intensity_menu.addAction(label)
            act.setCheckable(True)
            if current_intensity == key:
                act.setChecked(True)
            act.triggered.connect(
                lambda *_, k=key: self.window.set_glitch_intensity(k)
            )
            group.addAction(act)

    def _add_activity_timeout_menu(self, parent_menu: QMenu) -> None:
        timeout_menu = self._add_submenu(parent_menu, "⏱  Таймаут ухода в сон")
        timeout_group = QActionGroup(timeout_menu)
        timeout_group.setExclusive(True)

        current_seconds = getattr(
            self.window, "activity_timeout_seconds", ACTIVITY_TIMEOUT_OPTIONS_MS[0] // 1000
        )
        for timeout_ms in ACTIVITY_TIMEOUT_OPTIONS_MS:
            seconds = timeout_ms // 1000
            act = timeout_menu.addAction(f"{seconds} сек")
            act.setCheckable(True)
            if current_seconds == seconds:
                act.setChecked(True)
            act.triggered.connect(
                lambda *_, s=seconds: self.window.set_activity_timeout(s)
            )
            timeout_group.addAction(act)

    def _add_reminder_toggle(self, parent_menu: QMenu) -> None:
        remind_act = parent_menu.addAction("🔔  Автономные реплики")
        remind_act.setCheckable(True)
        remind_act.setChecked(bool(getattr(self.window, "reminders_enabled", True)))
        remind_act.triggered.connect(
            lambda checked: self.window.set_reminders_enabled(checked)
        )


def build_pet_context_menu(window: Any, _pos: QPoint | None = None) -> QMenu:
    """Функция построения контекстного меню для питомца."""
    builder = ContextMenuBuilder(window)
    return builder.build(for_tray=False)


def build_tray_context_menu(window: Any) -> QMenu:
    """Функция построения контекстного меню для системного трея."""
    builder = ContextMenuBuilder(window)
    return builder.build(for_tray=True)

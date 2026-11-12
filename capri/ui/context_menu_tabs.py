"""Модульные страницы вкладок для Cyber Hub контекстного меню."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from PySide6.QtCore import Qt
from PySide6.QtMultimedia import QMediaDevices
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from ..core.settings import (
    ACTIVITY_TIMEOUT_OPTIONS_MS,
    get_config_value,
    set_config_value,
)
from .theme import (
    ACID_GREEN,
    CSS_CYBER_UI,
    NEON_CRIMSON,
    OBSIDIAN_BLACK,
    PURE_WHITE,
)

if TYPE_CHECKING:
    pass

_LABEL_STYLE = (
    f"color: {PURE_WHITE}; font-family: {CSS_CYBER_UI}; "
    "font-size: 11px; font-weight: bold;"
)
_HEADER_STYLE = (
    f"color: {ACID_GREEN}; font-family: {CSS_CYBER_UI}; "
    "font-size: 12px; font-weight: bold; letter-spacing: 1px;"
)
_BTN_STYLE = f"""
QPushButton {{
    background-color: {OBSIDIAN_BLACK};
    color: {PURE_WHITE};
    border: 1px solid {NEON_CRIMSON};
    padding: 6px 12px;
    font-family: {CSS_CYBER_UI};
    font-size: 11px;
    font-weight: bold;
}}
QPushButton:hover {{
    background-color: {NEON_CRIMSON};
    color: {PURE_WHITE};
}}
QPushButton:pressed {{
    background-color: {ACID_GREEN};
    color: {OBSIDIAN_BLACK};
}}
"""

_BTN_ACCENT_STYLE = f"""
QPushButton {{
    background-color: {OBSIDIAN_BLACK};
    color: {ACID_GREEN};
    border: 1px solid {ACID_GREEN};
    padding: 6px 12px;
    font-family: {CSS_CYBER_UI};
    font-size: 11px;
    font-weight: bold;
}}
QPushButton:hover {{
    background-color: {ACID_GREEN};
    color: {OBSIDIAN_BLACK};
}}
"""

_HALT_BTN_STYLE = f"""
QPushButton {{
    background-color: {NEON_CRIMSON};
    color: {PURE_WHITE};
    border: 1px solid {PURE_WHITE};
    padding: 8px 16px;
    font-family: {CSS_CYBER_UI};
    font-size: 12px;
    font-weight: bold;
}}
QPushButton:hover {{
    background-color: {PURE_WHITE};
    color: {OBSIDIAN_BLACK};
}}
"""
_CHECKBOX_STYLE = f"""
QCheckBox {{
    color: {PURE_WHITE};
    font-family: {CSS_CYBER_UI};
    font-size: 11px;
    spacing: 8px;
}}
QCheckBox::indicator {{
    width: 14px;
    height: 14px;
    border: 1px solid {NEON_CRIMSON};
    background-color: {OBSIDIAN_BLACK};
}}
QCheckBox::indicator:checked {{
    background-color: {ACID_GREEN};
    border: 1px solid {PURE_WHITE};
}}
"""

_COMBO_STYLE = f"""
QComboBox {{
    background-color: {OBSIDIAN_BLACK};
    color: {PURE_WHITE};
    border: 1px solid {NEON_CRIMSON};
    padding: 4px 8px;
    font-family: {CSS_CYBER_UI};
    font-size: 11px;
}}
QComboBox QAbstractItemView {{
    background-color: {OBSIDIAN_BLACK};
    color: {PURE_WHITE};
    selection-background-color: {NEON_CRIMSON};
    selection-color: {PURE_WHITE};
    border: 1px solid {ACID_GREEN};
}}
"""

_GROUP_STYLE = f"""
QGroupBox {{
    color: {ACID_GREEN};
    font-family: {CSS_CYBER_UI};
    font-size: 11px;
    font-weight: bold;
    border: 1px solid rgba(246, 2, 63, 0.4);
    margin-top: 10px;
    padding-top: 10px;
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    left: 8px;
    padding: 0 4px;
}}
"""
class CoreTabPage(QWidget):
    """Вкладка основных команд и действий питомца."""

    def __init__(self, window: Any, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.window = window
        self._init_ui()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        grp_actions = QGroupBox("[TACTICAL_ACTIONS]", self)
        grp_actions.setStyleSheet(_GROUP_STYLE)
        act_layout = QGridLayout(grp_actions)
        act_layout.setSpacing(10)

        self.btn_summon = QPushButton("[SUMMON] Позвать Капри", self)
        self.btn_summon.setStyleSheet(_BTN_ACCENT_STYLE)
        self.btn_summon.clicked.connect(self._on_summon)
        act_layout.addWidget(self.btn_summon, 0, 0)

        self.btn_teleport = QPushButton("[AIM] Телепорт / Прицел", self)
        self.btn_teleport.setStyleSheet(_BTN_STYLE)
        self.btn_teleport.clicked.connect(self._on_teleport)
        act_layout.addWidget(self.btn_teleport, 0, 1)

        self.btn_reset_pos = QPushButton("[POS] Сброс позиции", self)
        self.btn_reset_pos.setStyleSheet(_BTN_STYLE)
        self.btn_reset_pos.clicked.connect(self._on_reset_pos)
        act_layout.addWidget(self.btn_reset_pos, 1, 0, 1, 2)
        layout.addWidget(grp_actions)

        grp_toggles = QGroupBox("[NEURAL_OVERRIDES]", self)
        grp_toggles.setStyleSheet(_GROUP_STYLE)
        tog_layout = QVBoxLayout(grp_toggles)
        tog_layout.setSpacing(8)

        self.chk_voice = QCheckBox("Голосовой интерфейс (ASR / VAD)", self)
        self.chk_voice.setStyleSheet(_CHECKBOX_STYLE)
        self.chk_voice.setChecked(get_config_value("audio.voice_enabled", True))
        self.chk_voice.toggled.connect(self._on_toggle_voice)
        tog_layout.addWidget(self.chk_voice)

        self.chk_glitches = QCheckBox("Экранные глитчи (Blackwall ICE)", self)
        self.chk_glitches.setStyleSheet(_CHECKBOX_STYLE)
        self.chk_glitches.setChecked(
            get_config_value("effects.glitches_enabled", True)
        )
        self.chk_glitches.toggled.connect(self._on_toggle_glitches)
        tog_layout.addWidget(self.chk_glitches)
        layout.addWidget(grp_toggles)
        layout.addStretch()
    def _on_summon(self) -> None:
        fn = getattr(self.window, "activate_command_mode", None)
        if callable(fn):
            fn()

    def _on_teleport(self) -> None:
        fn = getattr(self.window, "activate_teleport", None)
        if callable(fn):
            fn()

    def _on_reset_pos(self) -> None:
        fn = getattr(self.window, "_reset_position", None)
        if callable(fn):
            fn()

    def _on_toggle_voice(self, checked: bool) -> None:
        actions = getattr(self.window, "actions", None)
        if actions and hasattr(actions, "toggle_voice"):
            actions.toggle_voice()
        else:
            set_config_value("audio.voice_enabled", checked)

    def _on_toggle_glitches(self, checked: bool) -> None:
        fn = getattr(self.window, "_toggle_glitches", None)
        if callable(fn):
            fn()
        else:
            set_config_value("effects.glitches_enabled", checked)


class AudioTabPage(QWidget):
    """Вкладка управления звуковыми эффектами, громкостью и микрофоном."""

    def __init__(self, window: Any, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.window = window
        self._init_ui()
    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        grp_vol = QGroupBox("[MASTER_VOLUME]", self)
        grp_vol.setStyleSheet(_GROUP_STYLE)
        vol_layout = QVBoxLayout(grp_vol)

        cur_vol = int(get_config_value("audio.volume", 50))
        self.lbl_vol = QLabel(f"ГРОМКОСТЬ: {cur_vol}%", self)
        self.lbl_vol.setStyleSheet(_LABEL_STYLE)
        vol_layout.addWidget(self.lbl_vol)

        self.slider_vol = QSlider(Qt.Orientation.Horizontal, self)
        self.slider_vol.setRange(0, 100)
        self.slider_vol.setValue(cur_vol)
        self.slider_vol.valueChanged.connect(self._on_slider_changed)
        vol_layout.addWidget(self.slider_vol)

        presets_layout = QHBoxLayout()
        for p in (25, 50, 75, 100):
            btn = QPushButton(f"{p}%", self)
            btn.setStyleSheet(_BTN_STYLE)
            btn.clicked.connect(lambda _, val=p: self._set_volume(val))
            presets_layout.addWidget(btn)
        vol_layout.addLayout(presets_layout)
        layout.addWidget(grp_vol)

        grp_sfx = QGroupBox("[AUDIO_CHANNELS]", self)
        grp_sfx.setStyleSheet(_GROUP_STYLE)
        sfx_layout = QVBoxLayout(grp_sfx)

        self.chk_speech = QCheckBox("Звуки диалогов и речи", self)
        self.chk_speech.setStyleSheet(_CHECKBOX_STYLE)
        self.chk_speech.setChecked(
            get_config_value("audio.speech_sound_enabled", True)
        )
        self.chk_speech.toggled.connect(self._on_toggle_speech_sound)
        sfx_layout.addWidget(self.chk_speech)

        self.chk_fx = QCheckBox("Звуки эффектов и молний", self)
        self.chk_fx.setStyleSheet(_CHECKBOX_STYLE)
        self.chk_fx.setChecked(
            get_config_value("audio.effects_sound_enabled", True)
        )
        self.chk_fx.toggled.connect(self._on_toggle_fx_sound)
        sfx_layout.addWidget(self.chk_fx)
        layout.addWidget(grp_sfx)
        grp_mic = QGroupBox("[AUDIO_INPUT_DEVICE]", self)
        grp_mic.setStyleSheet(_GROUP_STYLE)
        mic_layout = QVBoxLayout(grp_mic)

        self.combo_mic = QComboBox(self)
        self.combo_mic.setStyleSheet(_COMBO_STYLE)
        self.combo_mic.addItem("Системный по умолчанию", None)
        try:
            for dev in QMediaDevices.audioInputs():
                self.combo_mic.addItem(dev.description(), dev)
        except Exception:
            pass
        self.combo_mic.currentIndexChanged.connect(self._on_mic_changed)
        mic_layout.addWidget(self.combo_mic)
        layout.addWidget(grp_mic)
        layout.addStretch()

    def _on_slider_changed(self, val: int) -> None:
        self.lbl_vol.setText(f"ГРОМКОСТЬ: {val}%")
        self._set_volume(val)

    def _set_volume(self, val: int) -> None:
        actions = getattr(self.window, "actions", None)
        if actions and hasattr(actions, "set_volume"):
            actions.set_volume(val)
        else:
            set_config_value("audio.volume", val)

    def _on_toggle_speech_sound(self, checked: bool) -> None:
        actions = getattr(self.window, "actions", None)
        if actions and hasattr(actions, "set_speech_sound_enabled"):
            actions.set_speech_sound_enabled(checked)
        else:
            set_config_value("audio.speech_sound_enabled", checked)

    def _on_toggle_fx_sound(self, checked: bool) -> None:
        actions = getattr(self.window, "actions", None)
        if actions and hasattr(actions, "set_effects_sound_enabled"):
            actions.set_effects_sound_enabled(checked)
        else:
            set_config_value("audio.effects_sound_enabled", checked)

    def _on_mic_changed(self, index: int) -> None:
        dev = self.combo_mic.itemData(index)
        actions = getattr(self.window, "actions", None)
        if actions and hasattr(actions, "set_designated_microphone"):
            actions.set_designated_microphone(dev)
class VisualTabPage(QWidget):
    """Вкладка настроек графики, масштаба и видеоадаптера."""

    def __init__(self, window: Any, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.window = window
        self._init_ui()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        grp_scale = QGroupBox("[SPRITE_SCALE]", self)
        grp_scale.setStyleSheet(_GROUP_STYLE)
        scale_layout = QHBoxLayout(grp_scale)

        cur_scale = int(get_config_value("appearance.scale", 100))
        for s in (50, 75, 100, 125, 150):
            btn = QPushButton(f"{s}%", self)
            btn.setStyleSheet(_BTN_ACCENT_STYLE if s == cur_scale else _BTN_STYLE)
            btn.clicked.connect(lambda _, val=s: self._on_scale_selected(val))
            scale_layout.addWidget(btn)
        layout.addWidget(grp_scale)

        grp_glitch = QGroupBox("[GLITCH_INTENSITY]", self)
        grp_glitch.setStyleSheet(_GROUP_STYLE)
        glitch_layout = QHBoxLayout(grp_glitch)

        cur_intensity = str(get_config_value("effects.glitch_intensity", "weak"))
        options = (("weak", "Низкая"), ("medium", "Средняя"), ("strong", "Макс"))
        for k, title in options:
            btn = QPushButton(f"[{title}]", self)
            btn.setStyleSheet(
                _BTN_ACCENT_STYLE if k == cur_intensity else _BTN_STYLE
            )
            btn.clicked.connect(lambda _, key=k: self._on_glitch_selected(key))
            glitch_layout.addWidget(btn)
        layout.addWidget(grp_glitch)

        grp_misc = QGroupBox("[PROJECTION_CONTROL]", self)
        grp_misc.setStyleSheet(_GROUP_STYLE)
        misc_layout = QVBoxLayout(grp_misc)

        self.btn_breach = QPushButton(
            "[BREACH] Повторить пробой экрана (Intro)", self
        )
        self.btn_breach.setStyleSheet(_BTN_STYLE)
        self.btn_breach.clicked.connect(self._on_replay_breach)
        misc_layout.addWidget(self.btn_breach)
        layout.addWidget(grp_misc)
        layout.addStretch()
    def _on_scale_selected(self, val: int) -> None:
        fn = getattr(self.window, "set_sprite_scale", None)
        if callable(fn):
            fn(val)
        else:
            set_config_value("appearance.scale", val)

    def _on_glitch_selected(self, key: str) -> None:
        fn = getattr(self.window, "set_glitch_intensity", None)
        if callable(fn):
            fn(key)
        else:
            set_config_value("effects.glitch_intensity", key)

    def _on_replay_breach(self) -> None:
        effects = getattr(self.window, "_effects_coordinator", None)
        if effects and hasattr(effects, "play_intro_breach"):
            self.window.hide()
            effects.play_intro_breach(self.window.reveal_on_startup)


class SystemTabPage(QWidget):
    """Вкладка управления поведением системы, тайм-аутами и аварийной остановки."""

    def __init__(self, window: Any, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.window = window
        self._init_ui()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        grp_standby = QGroupBox("[STANDBY_TIMER]", self)
        grp_standby.setStyleSheet(_GROUP_STYLE)
        stb_layout = QHBoxLayout(grp_standby)

        cur_timeout = int(get_config_value("behavior.inactivity_timeout_ms", 5000))
        for ms in ACTIVITY_TIMEOUT_OPTIONS_MS:
            sec = ms // 1000
            btn = QPushButton(f"{sec} сек", self)
            btn.setStyleSheet(
                _BTN_ACCENT_STYLE if ms == cur_timeout else _BTN_STYLE
            )
            btn.clicked.connect(lambda _, val=sec: self._on_timeout_selected(val))
            stb_layout.addWidget(btn)
        layout.addWidget(grp_standby)
        grp_beh = QGroupBox("[AUTONOMOUS_DAEMONS]", self)
        grp_beh.setStyleSheet(_GROUP_STYLE)
        beh_layout = QVBoxLayout(grp_beh)

        self.chk_reminders = QCheckBox("Автономные реплики и напоминания", self)
        self.chk_reminders.setStyleSheet(_CHECKBOX_STYLE)
        self.chk_reminders.setChecked(
            get_config_value("behavior.reminders_enabled", True)
        )
        self.chk_reminders.toggled.connect(self._on_toggle_reminders)
        beh_layout.addWidget(self.chk_reminders)

        self.chk_game = QCheckBox("Игровой режим (Stealth Game Suppression)", self)
        self.chk_game.setStyleSheet(_CHECKBOX_STYLE)
        self.chk_game.setChecked(
            get_config_value("game_mode.suppression_enabled", True)
        )
        self.chk_game.toggled.connect(self._on_toggle_game_mode)
        beh_layout.addWidget(self.chk_game)

        self.chk_discord = QCheckBox("Интеграция с Discord RPC", self)
        self.chk_discord.setStyleSheet(_CHECKBOX_STYLE)
        self.chk_discord.setChecked(get_config_value("discord.enabled", True))
        self.chk_discord.toggled.connect(self._on_toggle_discord)
        beh_layout.addWidget(self.chk_discord)

        self.chk_shredder = QCheckBox("Протокол уничтожения файлов Blackwall", self)
        self.chk_shredder.setStyleSheet(_CHECKBOX_STYLE)
        self.chk_shredder.setChecked(
            get_config_value("behavior.file_shredder_enabled", True)
        )
        self.chk_shredder.toggled.connect(self._on_toggle_shredder)
        beh_layout.addWidget(self.chk_shredder)
        layout.addWidget(grp_beh)

        layout.addStretch()

        self.btn_halt = QPushButton("[SYS.HALT] АВАРИЙНОЕ ЗАВЕРШЕНИЕ РАБОТЫ", self)
        self.btn_halt.setStyleSheet(_HALT_BTN_STYLE)
        self.btn_halt.clicked.connect(self._on_halt)
        layout.addWidget(self.btn_halt)
    def _on_timeout_selected(self, sec: int) -> None:
        fn = getattr(self.window, "set_activity_timeout", None)
        if callable(fn):
            fn(sec)
        else:
            set_config_value("behavior.inactivity_timeout_ms", sec * 1000)

    def _on_toggle_reminders(self, checked: bool) -> None:
        actions = getattr(self.window, "actions", None)
        if actions and hasattr(actions, "set_reminders_enabled"):
            actions.set_reminders_enabled(checked)
        else:
            set_config_value("behavior.reminders_enabled", checked)

    def _on_toggle_game_mode(self, checked: bool) -> None:
        actions = getattr(self.window, "actions", None)
        if actions and hasattr(actions, "set_game_suppression_enabled"):
            actions.set_game_suppression_enabled(checked)
        else:
            set_config_value("game_mode.suppression_enabled", checked)

    def _on_toggle_discord(self, checked: bool) -> None:
        actions = getattr(self.window, "actions", None)
        if actions and hasattr(actions, "set_discord_enabled"):
            actions.set_discord_enabled(checked)
        else:
            set_config_value("discord.enabled", checked)

    def _on_toggle_shredder(self, checked: bool) -> None:
        set_config_value("behavior.file_shredder_enabled", checked)

    def _on_halt(self) -> None:
        fn = getattr(self.window, "close", None)
        if callable(fn):
            fn()


__all__ = [
    "CoreTabPage",
    "AudioTabPage",
    "VisualTabPage",
    "SystemTabPage",
]

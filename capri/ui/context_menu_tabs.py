"""Модульные страницы вкладок для Cyber Hub контекстного меню."""

from __future__ import annotations

import contextlib
from typing import TYPE_CHECKING, Any

from PySide6.QtCore import Qt
from PySide6.QtGui import QGuiApplication
from PySide6.QtMultimedia import QMediaDevices
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
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
from .reminder_dialog import ReminderRangeDialog
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
        self.pet_window = window
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

        self.btn_deck = QPushButton("[DECK] Кибердэка (ввод команд)", self)
        self.btn_deck.setStyleSheet(_BTN_STYLE)
        self.btn_deck.clicked.connect(self._on_deck)
        act_layout.addWidget(self.btn_deck, 0, 1)

        self.btn_teleport = QPushButton("[AIM] Прицел / Телепорт", self)
        self.btn_teleport.setStyleSheet(_BTN_STYLE)
        self.btn_teleport.clicked.connect(self._on_teleport)
        act_layout.addWidget(self.btn_teleport, 1, 0)

        self.btn_reset_pos = QPushButton("[POS] Сброс позиции", self)
        self.btn_reset_pos.setStyleSheet(_BTN_STYLE)
        self.btn_reset_pos.clicked.connect(self._on_reset_pos)
        act_layout.addWidget(self.btn_reset_pos, 1, 1)
        layout.addWidget(grp_actions)

        grp_toggles = QGroupBox("[NEURAL_OVERRIDES]", self)
        grp_toggles.setStyleSheet(_GROUP_STYLE)
        tog_layout = QVBoxLayout(grp_toggles)
        tog_layout.setSpacing(8)

        self.chk_discord = QCheckBox("[DISCORD] Discord Rich Presence", self)
        self.chk_discord.setStyleSheet(_CHECKBOX_STYLE)
        orchestrator = getattr(self.pet_window, "_orchestrator", None)
        rpc_enabled = (
            getattr(orchestrator, "_discord_enabled", True)
            if orchestrator
            else get_config_value("discord.enabled", True)
        )
        self.chk_discord.setChecked(rpc_enabled)
        self.chk_discord.toggled.connect(self._on_toggle_discord)
        tog_layout.addWidget(self.chk_discord)

        self.chk_voice = QCheckBox("[VOICE] Голосовой ввод", self)
        self.chk_voice.setStyleSheet(_CHECKBOX_STYLE)
        voice_listening = False
        if hasattr(self.pet_window, "voice_coordinator"):
            voice_listening = getattr(self.pet_window.voice_coordinator, "is_listening", False)
        elif hasattr(self.pet_window, "voice"):
            voice_listening = getattr(self.pet_window.voice, "is_listening", False)
        else:
            voice_listening = get_config_value("audio.voice_enabled", True)
        self.chk_voice.setChecked(voice_listening)
        self.chk_voice.toggled.connect(self._on_toggle_voice)
        tog_layout.addWidget(self.chk_voice)

        self.chk_glitches = QCheckBox("[GLITCH] Экранные глитчи", self)
        self.chk_glitches.setStyleSheet(_CHECKBOX_STYLE)
        glitches_enabled = getattr(self.pet_window, "glitches_enabled", False)
        if not glitches_enabled and hasattr(self.pet_window, "glitches"):
            glitches_enabled = getattr(self.pet_window.glitches, "is_enabled", False)
        elif not glitches_enabled:
            glitches_enabled = get_config_value("effects.glitches_enabled", True)
        self.chk_glitches.setChecked(glitches_enabled)
        self.chk_glitches.toggled.connect(self._on_toggle_glitches)
        tog_layout.addWidget(self.chk_glitches)
        layout.addWidget(grp_toggles)
        layout.addStretch()

    def _on_summon(self) -> None:
        fn = getattr(self.pet_window, "activate_command_mode", None)
        if callable(fn):
            fn()

    def _on_deck(self) -> None:
        fn = getattr(self.pet_window, "open_console", None)
        if callable(fn):
            fn()

    def _on_teleport(self) -> None:
        fn = getattr(self.pet_window, "activate_teleport", None)
        if callable(fn):
            fn()

    def _on_reset_pos(self) -> None:
        fn = getattr(self.pet_window, "_reset_position", None)
        if callable(fn):
            fn()

    def _on_toggle_discord(self, checked: bool) -> None:
        actions = getattr(self.pet_window, "actions", None)
        if actions and hasattr(actions, "set_discord_enabled"):
            actions.set_discord_enabled(checked)
        elif hasattr(self.pet_window, "set_discord_enabled"):
            self.pet_window.set_discord_enabled(checked)
        else:
            set_config_value("discord.enabled", checked)

    def _on_toggle_voice(self, checked: bool) -> None:
        actions = getattr(self.pet_window, "actions", None)
        if actions and hasattr(actions, "toggle_voice"):
            actions.toggle_voice()
        elif hasattr(self.pet_window, "toggle_voice"):
            self.pet_window.toggle_voice()
        else:
            set_config_value("audio.voice_enabled", checked)

    def _on_toggle_glitches(self, checked: bool) -> None:
        actions = getattr(self.pet_window, "actions", None)
        if actions and hasattr(actions, "toggle_glitches"):
            actions.toggle_glitches()
        elif hasattr(self.pet_window, "_toggle_glitches"):
            self.pet_window._toggle_glitches()
        elif hasattr(self.pet_window, "process_input"):
            self.pet_window.process_input("глитч")
        else:
            set_config_value("effects.glitches_enabled", checked)


class AudioTabPage(QWidget):
    """Вкладка управления звуковыми эффектами, громкостью и микрофоном."""

    def __init__(self, window: Any, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.pet_window = window
        self._init_ui()
    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        grp_sfx = QGroupBox("[AUDIO.FX] Звуковые эффекты", self)
        grp_sfx.setStyleSheet(_GROUP_STYLE)
        sfx_layout = QVBoxLayout(grp_sfx)

        self.chk_speech = QCheckBox("[SYNTH] Синтез речи (SFX)", self)
        self.chk_speech.setStyleSheet(_CHECKBOX_STYLE)
        self.chk_speech.setChecked(
            get_config_value("audio.speech_sound_enabled", True)
        )
        self.chk_speech.toggled.connect(self._on_toggle_speech_sound)
        sfx_layout.addWidget(self.chk_speech)

        self.chk_fx = QCheckBox("[UI] UI эффекты", self)
        self.chk_fx.setStyleSheet(_CHECKBOX_STYLE)
        self.chk_fx.setChecked(
            get_config_value("audio.effects_sound_enabled", True)
        )
        self.chk_fx.toggled.connect(self._on_toggle_fx_sound)
        sfx_layout.addWidget(self.chk_fx)

        self.chk_vol_hud = QCheckBox("Экранный оверлей (Volume HUD)", self)
        self.chk_vol_hud.setStyleSheet(_CHECKBOX_STYLE)
        self.chk_vol_hud.setChecked(
            get_config_value("audio.volume_hud_enabled", True)
        )
        self.chk_vol_hud.toggled.connect(self._on_toggle_volume_hud)
        sfx_layout.addWidget(self.chk_vol_hud)
        layout.addWidget(grp_sfx)

        self.chk_vol_hud = QCheckBox("Экранный оверлей (Volume HUD)", self)
        self.chk_vol_hud.setStyleSheet(_CHECKBOX_STYLE)
        self.chk_vol_hud.setChecked(
            get_config_value("audio.volume_hud_enabled", True)
        )
        self.chk_vol_hud.toggled.connect(self._on_toggle_volume_hud)
        sfx_layout.addWidget(self.chk_vol_hud)
        layout.addWidget(grp_sfx)

        grp_vol = QGroupBox("[VOL] Громкость SFX", self)
        grp_vol.setStyleSheet(_GROUP_STYLE)
        vol_layout = QVBoxLayout(grp_vol)

        cur_vol = int(get_config_value("audio.volume", 50))
        cur_vol = max(25, min(100, round(cur_vol / 25) * 25))
        self.lbl_vol = QLabel(f"ГРОМКОСТЬ: {cur_vol}%", self)
        self.lbl_vol.setStyleSheet(_LABEL_STYLE)
        vol_layout.addWidget(self.lbl_vol)

        self.slider_vol = QSlider(Qt.Orientation.Horizontal, self)
        self.slider_vol.setRange(25, 100)
        self.slider_vol.setSingleStep(25)
        self.slider_vol.setPageStep(25)
        self.slider_vol.setTickInterval(25)
        self.slider_vol.setValue(cur_vol)
        self.slider_vol.valueChanged.connect(self._on_slider_changed)
        vol_layout.addWidget(self.slider_vol)

        presets_layout = QHBoxLayout()
        self._preset_buttons: dict[int, QPushButton] = {}
        for p in (25, 50, 75, 100):
            btn = QPushButton(f"{p}%", self)
            btn.setStyleSheet(_BTN_ACCENT_STYLE if p == cur_vol else _BTN_STYLE)
            btn.clicked.connect(lambda _, val=p: self._set_volume(val))
            presets_layout.addWidget(btn)
            self._preset_buttons[p] = btn
        vol_layout.addLayout(presets_layout)
        layout.addWidget(grp_vol)

        grp_mic = QGroupBox("[AUDIO.IN] Входной микрофон", self)
        grp_mic.setStyleSheet(_GROUP_STYLE)
        mic_layout = QVBoxLayout(grp_mic)

        self.combo_mic = QComboBox(self)
        self.combo_mic.setStyleSheet(_COMBO_STYLE)
        default_mic = QMediaDevices.defaultAudioInput()
        def_desc = default_mic.description() if not default_mic.isNull() else "Системный"
        self.combo_mic.addItem(f"По умолчанию ({def_desc})", None)
        active_idx = 0
        cfg_mic = get_config_value("audio.designated_microphone", None)
        try:
            for idx, dev in enumerate(QMediaDevices.audioInputs(), start=1):
                self.combo_mic.addItem(dev.description(), dev)
                if cfg_mic and dev.description() == cfg_mic:
                    active_idx = idx
        except Exception:
            pass
        self.combo_mic.setCurrentIndex(active_idx)
        self.combo_mic.currentIndexChanged.connect(self._on_mic_changed)
        mic_layout.addWidget(self.combo_mic)
        layout.addWidget(grp_mic)
        layout.addStretch()

    def _on_slider_changed(self, raw_val: int) -> None:
        val = round(raw_val / 25) * 25
        val = max(25, min(100, val))
        if self.slider_vol.value() != val:
            self.slider_vol.blockSignals(True)
            self.slider_vol.setValue(val)
            self.slider_vol.blockSignals(False)
        self._set_volume(val)

    def _set_volume(self, val: int) -> None:
        val = round(val / 25) * 25
        val = max(25, min(100, val))
        self.lbl_vol.setText(f"ГРОМКОСТЬ: {val}%")
        if self.slider_vol.value() != val:
            self.slider_vol.blockSignals(True)
            self.slider_vol.setValue(val)
            self.slider_vol.blockSignals(False)

        for p, btn in getattr(self, "_preset_buttons", {}).items():
            btn.setStyleSheet(_BTN_ACCENT_STYLE if p == val else _BTN_STYLE)

        actions = getattr(self.pet_window, "actions", None)
        if actions and hasattr(actions, "set_master_volume"):
            actions.set_master_volume(val)
        elif hasattr(self.pet_window, "set_master_volume"):
            self.pet_window.set_master_volume(val)
        else:
            set_config_value("audio.volume", val)

    def _on_toggle_volume_hud(self, checked: bool) -> None:
        set_config_value("audio.volume_hud_enabled", checked)

    def _on_toggle_speech_sound(self, checked: bool) -> None:
        actions = getattr(self.pet_window, "actions", None)
        if actions and hasattr(actions, "set_speech_sound_enabled"):
            actions.set_speech_sound_enabled(checked)
        else:
            set_config_value("audio.speech_sound_enabled", checked)

    def _on_toggle_fx_sound(self, checked: bool) -> None:
        actions = getattr(self.pet_window, "actions", None)
        if actions and hasattr(actions, "set_effects_sound_enabled"):
            actions.set_effects_sound_enabled(checked)
        else:
            set_config_value("audio.effects_sound_enabled", checked)

    def _on_mic_changed(self, index: int) -> None:
        dev = self.combo_mic.itemData(index)
        actions = getattr(self.pet_window, "actions", None)
        if actions and hasattr(actions, "set_designated_microphone"):
            actions.set_designated_microphone(dev)
class VisualTabPage(QWidget):
    """Вкладка настроек графики, масштаба и видеоадаптера."""

    def __init__(self, window: Any, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.pet_window = window
        self._init_ui()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        grp_scale = QGroupBox("[SCALE] Масштаб проекции", self)
        grp_scale.setStyleSheet(_GROUP_STYLE)
        scale_layout = QHBoxLayout(grp_scale)

        cur_scale = int(get_config_value("appearance.scale", 100))
        self._scale_buttons: dict[int, QPushButton] = {}
        for s in (50, 75, 100, 125, 150):
            btn = QPushButton(f"{s}%", self)
            btn.setStyleSheet(_BTN_ACCENT_STYLE if s == cur_scale else _BTN_STYLE)
            btn.clicked.connect(lambda _, val=s: self._on_scale_selected(val))
            scale_layout.addWidget(btn)
            self._scale_buttons[s] = btn
        layout.addWidget(grp_scale)

        grp_glitch = QGroupBox("[FX.RATE] Интенсивность глитчей", self)
        grp_glitch.setStyleSheet(_GROUP_STYLE)
        glitch_layout = QHBoxLayout(grp_glitch)

        cur_intensity = str(get_config_value("effects.glitch_intensity", "weak"))
        options = (("weak", "Низкая"), ("medium", "Средняя"), ("strong", "Максимальная"))
        self._glitch_buttons: dict[str, QPushButton] = {}
        for k, title in options:
            btn = QPushButton(f"[{title}]", self)
            btn.setStyleSheet(
                _BTN_ACCENT_STYLE if k == cur_intensity else _BTN_STYLE
            )
            btn.clicked.connect(lambda _, key=k: self._on_glitch_selected(key))
            glitch_layout.addWidget(btn)
            self._glitch_buttons[k] = btn
        layout.addWidget(grp_glitch)

        grp_screen = QGroupBox("[DISP] Монитор", self)
        grp_screen.setStyleSheet(_GROUP_STYLE)
        scr_layout = QVBoxLayout(grp_screen)
        self.combo_screen = QComboBox(self)
        self.combo_screen.setStyleSheet(_COMBO_STYLE)
        primary_scr = QGuiApplication.primaryScreen()
        cur_scr_name = get_config_value("screen.designated_screen", None)
        active_scr_idx = 0
        for idx, scr in enumerate(QGuiApplication.screens()):
            geo = scr.geometry()
            extra = " [основной]" if primary_scr and scr.name() == primary_scr.name() else ""
            self.combo_screen.addItem(f"{scr.name()} ({geo.width()}x{geo.height()}){extra}", scr)
            if cur_scr_name and scr.name() == cur_scr_name:
                active_scr_idx = idx
        self.combo_screen.setCurrentIndex(active_scr_idx)
        self.combo_screen.currentIndexChanged.connect(self._on_screen_changed)
        scr_layout.addWidget(self.combo_screen)
        layout.addWidget(grp_screen)

        grp_misc = QGroupBox("[PROJECTION_CONTROL]", self)
        grp_misc.setStyleSheet(_GROUP_STYLE)
        misc_layout = QVBoxLayout(grp_misc)

        self.btn_breach = QPushButton(
            "[FX] Blackwall Breach Intro", self
        )
        self.btn_breach.setStyleSheet(_BTN_STYLE)
        self.btn_breach.clicked.connect(self._on_replay_breach)
        misc_layout.addWidget(self.btn_breach)
        layout.addWidget(grp_misc)
        layout.addStretch()
    def _on_scale_selected(self, val: int) -> None:
        for s, btn in getattr(self, "_scale_buttons", {}).items():
            btn.setStyleSheet(_BTN_ACCENT_STYLE if s == val else _BTN_STYLE)
        fn = getattr(self.pet_window, "set_sprite_scale", None)
        if callable(fn):
            fn(val)
        else:
            set_config_value("appearance.scale", val)

    def _on_glitch_selected(self, key: str) -> None:
        for k, btn in getattr(self, "_glitch_buttons", {}).items():
            btn.setStyleSheet(_BTN_ACCENT_STYLE if k == key else _BTN_STYLE)
        fn = getattr(self.pet_window, "set_glitch_intensity", None)
        if callable(fn):
            fn(key)
        else:
            set_config_value("effects.glitch_intensity", key)

    def _on_screen_changed(self, index: int) -> None:
        scr = self.combo_screen.itemData(index)
        if scr is not None:
            actions = getattr(self.pet_window, "actions", None)
            if actions and hasattr(actions, "set_designated_screen"):
                actions.set_designated_screen(scr)
            elif hasattr(self.pet_window, "set_designated_screen"):
                self.pet_window.set_designated_screen(scr)

    def _on_replay_breach(self) -> None:
        top = self.window()
        if isinstance(top, QDialog):
            top.reject()

        actions = getattr(self.pet_window, "actions", None)
        if actions and hasattr(actions, "trigger_intro_breach"):
            actions.trigger_intro_breach()
        elif hasattr(self.pet_window, "trigger_intro_breach"):
            self.pet_window.trigger_intro_breach()
        elif hasattr(self.pet_window, "_effects") and hasattr(
            self.pet_window._effects, "play_intro_breach"
        ):
            self.pet_window.hide()
            self.pet_window._effects.play_intro_breach(
                getattr(self.pet_window, "_reveal_on_startup", None)
            )


class SystemTabPage(QWidget):
    """Вкладка управления поведением системы, тайм-аутами и аварийной остановки."""

    def __init__(self, window: Any, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.pet_window = window
        self._freq_buttons: dict[str, QPushButton] = {}
        self._init_ui()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        grp_standby = QGroupBox("[STANDBY] Таймаут ухода в сон", self)
        grp_standby.setStyleSheet(_GROUP_STYLE)
        stb_layout = QHBoxLayout(grp_standby)

        cur_timeout = int(get_config_value("behavior.inactivity_timeout_ms", 5000))
        self._timeout_buttons: dict[int, QPushButton] = {}
        for ms in ACTIVITY_TIMEOUT_OPTIONS_MS:
            sec = ms // 1000
            btn = QPushButton(f"{sec} сек", self)
            btn.setStyleSheet(
                _BTN_ACCENT_STYLE if ms == cur_timeout else _BTN_STYLE
            )
            btn.clicked.connect(lambda _, val=sec: self._on_timeout_selected(val))
            stb_layout.addWidget(btn)
            self._timeout_buttons[sec] = btn
        layout.addWidget(grp_standby)

        grp_beh = QGroupBox("[AUTONOMY] Автономные реплики", self)
        grp_beh.setStyleSheet(_GROUP_STYLE)
        beh_layout = QVBoxLayout(grp_beh)

        self.chk_reminders = QCheckBox("Включить реплики", self)
        self.chk_reminders.setStyleSheet(_CHECKBOX_STYLE)
        self.chk_reminders.setChecked(
            get_config_value("behavior.reminders_enabled", True)
        )
        self.chk_reminders.toggled.connect(self._on_toggle_reminders)
        beh_layout.addWidget(self.chk_reminders)

        lbl_freq = QLabel("Частота напоминаний:", self)
        lbl_freq.setStyleSheet(_LABEL_STYLE)
        beh_layout.addWidget(lbl_freq)

        freq_layout = QHBoxLayout()
        curr_min_ms = int(get_config_value("behavior.reminder_min_interval_ms", 600_000))
        curr_max_ms = int(get_config_value("behavior.reminder_max_interval_ms", 3_600_000))
        actions = getattr(self.pet_window, "actions", None)
        raw_range = getattr(actions, "reminder_interval_range", None)
        if isinstance(raw_range, (tuple, list)) and len(raw_range) == 2:
            curr_min_ms, curr_max_ms = int(raw_range[0]), int(raw_range[1])
        else:
            win_range = getattr(self.pet_window, "reminder_interval_range", None)
            if isinstance(win_range, (tuple, list)) and len(win_range) == 2:
                curr_min_ms, curr_max_ms = int(win_range[0]), int(win_range[1])

        freq_presets = (
            ("Часто (1 – 5 мин)", 60_000, 300_000),
            ("Обычно (10 – 60 мин)", 600_000, 3_600_000),
            ("Редко (30 – 120 мин)", 1_800_000, 7_200_000),
        )
        is_preset_matched = False
        for label, mn, mx in freq_presets:
            btn = QPushButton(label, self)
            matched = abs(curr_min_ms - mn) < 1000 and abs(curr_max_ms - mx) < 1000
            if matched:
                is_preset_matched = True
            btn.setStyleSheet(_BTN_ACCENT_STYLE if matched else _BTN_STYLE)
            btn.clicked.connect(lambda _, m1=mn, m2=mx, b=btn: self._on_freq_preset_clicked(m1, m2, b))
            freq_layout.addWidget(btn)
            self._freq_buttons[label] = btn

        curr_min_m = max(1, round(curr_min_ms / 60_000))
        curr_max_m = max(curr_min_m, round(curr_max_ms / 60_000))
        custom_label = (
            f"Своя частота ({curr_min_m} – {curr_max_m} мин)..."
            if not is_preset_matched
            else "Своя частота..."
        )
        self.btn_custom_range = QPushButton(custom_label, self)
        self.btn_custom_range.setStyleSheet(
            _BTN_ACCENT_STYLE if not is_preset_matched else _BTN_STYLE
        )
        self.btn_custom_range.clicked.connect(self._on_custom_reminder_range)
        freq_layout.addWidget(self.btn_custom_range)
        self._freq_buttons["custom"] = self.btn_custom_range

        beh_layout.addLayout(freq_layout)

        self.chk_game = QCheckBox("[GAME] Игровой режим (тишина)", self)
        self.chk_game.setStyleSheet(_CHECKBOX_STYLE)
        self.chk_game.setChecked(
            get_config_value("game_mode.suppression_enabled", True)
        )
        self.chk_game.toggled.connect(self._on_toggle_game_mode)
        beh_layout.addWidget(self.chk_game)

        self.chk_discord = QCheckBox("[DISCORD] Discord Rich Presence", self)
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

        self.btn_halt = QPushButton("[SYS.HALT] Завершить работу", self)
        self.btn_halt.setStyleSheet(_HALT_BTN_STYLE)
        self.btn_halt.clicked.connect(self._on_halt)
        layout.addWidget(self.btn_halt)
    def _on_timeout_selected(self, sec: int) -> None:
        for s, btn in getattr(self, "_timeout_buttons", {}).items():
            btn.setStyleSheet(_BTN_ACCENT_STYLE if s == sec else _BTN_STYLE)
        fn = getattr(self.pet_window, "set_activity_timeout", None)
        if callable(fn):
            fn(sec)
        else:
            set_config_value("behavior.inactivity_timeout_ms", sec * 1000)

    def _set_reminder_range(self, min_ms: int, max_ms: int) -> None:
        actions = getattr(self.pet_window, "actions", None)
        if actions and hasattr(actions, "set_reminder_interval_range"):
            actions.set_reminder_interval_range(min_ms, max_ms)
        elif hasattr(self.pet_window, "set_reminder_interval_range"):
            self.pet_window.set_reminder_interval_range(min_ms, max_ms)
        else:
            set_config_value("behavior.reminder_min_interval_ms", min_ms)
            set_config_value("behavior.reminder_max_interval_ms", max_ms)

    def _on_freq_preset_clicked(self, min_ms: int, max_ms: int, clicked_btn: QPushButton) -> None:
        self._set_reminder_range(min_ms, max_ms)
        for btn in self._freq_buttons.values():
            btn.setStyleSheet(_BTN_STYLE)
        clicked_btn.setStyleSheet(_BTN_ACCENT_STYLE)
        self.btn_custom_range.setText("Своя частота...")

    def _on_custom_reminder_range(self) -> None:
        curr_min_m = int(get_config_value("behavior.reminder_min_interval_ms", 600_000)) // 60_000
        curr_max_m = int(get_config_value("behavior.reminder_max_interval_ms", 3_600_000)) // 60_000
        dialog = ReminderRangeDialog(curr_min_m, curr_max_m, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            new_min_m = dialog.spin_from.value()
            new_max_m = max(new_min_m, dialog.spin_to.value())
            new_min_ms = new_min_m * 60_000
            new_max_ms = new_max_m * 60_000
            self._set_reminder_range(new_min_ms, new_max_ms)
            for btn in self._freq_buttons.values():
                btn.setStyleSheet(_BTN_STYLE)
            self.btn_custom_range.setText(f"Своя частота ({new_min_m} – {new_max_m} мин)...")
            self.btn_custom_range.setStyleSheet(_BTN_ACCENT_STYLE)

    def _on_toggle_reminders(self, checked: bool) -> None:
        actions = getattr(self.pet_window, "actions", None)
        if actions and hasattr(actions, "set_reminders_enabled"):
            actions.set_reminders_enabled(checked)
        else:
            set_config_value("behavior.reminders_enabled", checked)

    def _on_toggle_game_mode(self, checked: bool) -> None:
        actions = getattr(self.pet_window, "actions", None)
        if actions and hasattr(actions, "set_game_suppression_enabled"):
            actions.set_game_suppression_enabled(checked)
        else:
            set_config_value("game_mode.suppression_enabled", checked)

    def _on_toggle_discord(self, checked: bool) -> None:
        actions = getattr(self.pet_window, "actions", None)
        if actions and hasattr(actions, "set_discord_enabled"):
            actions.set_discord_enabled(checked)
        else:
            set_config_value("discord.enabled", checked)

    def _on_toggle_shredder(self, checked: bool) -> None:
        set_config_value("behavior.file_shredder_enabled", checked)

    def _on_halt(self) -> None:
        win = self.window()
        if isinstance(win, QDialog):
            with contextlib.suppress(Exception):
                if hasattr(win, "close"):
                    try:
                        win.close(immediate=True)  # type: ignore[call-arg]
                    except TypeError:
                        win.close()
                elif hasattr(win, "reject"):
                    win.reject()
        fn = getattr(self.pet_window, "close", None)
        if callable(fn):
            fn()


__all__ = [
    "CoreTabPage",
    "AudioTabPage",
    "VisualTabPage",
    "SystemTabPage",
]

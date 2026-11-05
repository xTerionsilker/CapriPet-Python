from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

from PySide6.QtCore import QPoint, QRect, Qt
from PySide6.QtGui import QActionGroup, QColor, QGuiApplication, QIcon, QPainter, QPen, QPixmap
from PySide6.QtMultimedia import QMediaDevices
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QHBoxLayout,
    QLabel,
    QMenu,
    QPushButton,
    QSpinBox,
    QSystemTrayIcon,
    QVBoxLayout,
    QWidget,
)

from ..core.settings import ACTIVITY_TIMEOUT_OPTIONS_MS
from .speech_sfx import get_speech_sfx
from .theme import (
    ACID_GREEN,
    CSS_CYBER_TERMINAL,
    CSS_CYBER_UI,
    CYBER_MENU_STYLE,
    ELECTRIC_BLUE,
    NEON_CRIMSON,
    NEON_VIOLET,
    OBSIDIAN_BLACK,
    PURE_WHITE,
)

if TYPE_CHECKING:
    from .pet_window import CapriWindow

_CORNER_CUT = 10
CAPRI_ICON = Path(__file__).resolve().parent.parent.parent / "assets" / "capri_icon.png"

class CyberMenu(QMenu):

    def __init__(self, parent: QWidget | None = None, title: str = "") -> None:
        super().__init__(title, parent)
        self.setStyleSheet(CYBER_MENU_STYLE)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)

        rect = self.rect().adjusted(0, 0, -1, -1)
        painter.fillRect(rect, QColor(OBSIDIAN_BLACK))

        scan_pen = QPen(QColor(246, 2, 63, 14), 1)
        painter.setPen(scan_pen)
        for y in range(rect.top() + 3, rect.bottom(), 3):
            painter.drawLine(rect.left() + 2, y, rect.right() - 2, y)

        cut = _CORNER_CUT
        border_pen = QPen(QColor(NEON_CRIMSON), 1)
        painter.setPen(border_pen)
        painter.drawLine(rect.left() + cut, rect.top(), rect.right() - cut, rect.top())
        painter.drawLine(rect.right() - cut, rect.top(), rect.right(), rect.top() + cut)
        painter.drawLine(rect.right(), rect.top() + cut, rect.right(), rect.bottom() - 3)
        painter.drawLine(rect.right() - 3, rect.bottom(), rect.left() + cut, rect.bottom())
        painter.drawLine(rect.left() + cut, rect.bottom(), rect.left(), rect.bottom() - cut)
        painter.drawLine(rect.left(), rect.bottom() - cut, rect.left(), rect.top() + cut)
        painter.drawLine(rect.left(), rect.top() + cut, rect.left() + cut, rect.top())

        painter.setPen(QPen(QColor(ACID_GREEN), 2))
        painter.drawLine(rect.left() + 1, rect.top() + cut + 2, rect.left() + 1, rect.top() + cut + 16)
        painter.fillRect(QRect(rect.left() + 3, rect.top() + 3, 3, 3), QColor(ACID_GREEN))

        painter.fillRect(QRect(rect.right() - 24, rect.top() + 3, 12, 2), QColor(ACID_GREEN))
        painter.fillRect(QRect(rect.right() - 10, rect.top() + 3, 6, 2), QColor(ELECTRIC_BLUE))

        painter.setPen(QPen(QColor(NEON_CRIMSON), 2))
        painter.drawLine(rect.right() - 1, rect.bottom() - 16, rect.right() - 1, rect.bottom() - 2)
        painter.drawLine(rect.right() - 16, rect.bottom() - 1, rect.right() - 2, rect.bottom() - 1)

        painter.fillRect(QRect(rect.left() + cut + 2, rect.bottom() - 3, 10, 2), QColor(PURE_WHITE))
        painter.fillRect(QRect(rect.left() + cut + 14, rect.bottom() - 3, 6, 2), QColor(NEON_VIOLET))

        painter.end()
        super().paintEvent(event)

class ContextMenuBuilder:
    

    def __init__(self, window: Any) -> None:
        self.window = window

    def build(self, for_tray: bool = False) -> QMenu:
        
        menu = CyberMenu(self.window if isinstance(self.window, QWidget) else None)

        hdr = menu.addAction("▶ CAPRI//NEURAL_LINK [ONLINE]")
        hdr.setEnabled(False)
        menu.addSeparator()

        if for_tray:
            call_act = menu.addAction("▲  [SUMMON] Позвать Капри")
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

        self._add_quick_actions(menu)

        menu.addSeparator()

        self._add_audio_section(menu)

        menu.addSeparator()

        self._add_visual_section(menu)

        menu.addSeparator()

        self._add_behavior_section(menu)

        menu.addSeparator()

        quit_act = menu.addAction("✖  [SYS.HALT] Завершить работу")
        quit_act.triggered.connect(self.window.close)

        return menu

    def _add_submenu(self, parent_menu: QMenu, title: str) -> CyberMenu:
        submenu = CyberMenu(parent_menu, title=title)
        parent_menu.addMenu(submenu)
        return submenu

    def _add_quick_actions(self, parent_menu: QMenu) -> None:
        voice_listening = False
        if hasattr(self.window, "voice_coordinator"):
            voice_listening = self.window.voice_coordinator.is_listening
        elif hasattr(self.window, "_voice"):
            voice_listening = self.window._voice.is_listening

        voice_act = parent_menu.addAction("▶  [VOICE] Голосовой ввод")
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

        glitch_act = parent_menu.addAction("▶  [GLITCH] Экранные глитчи")
        glitch_act.setCheckable(True)
        glitch_act.setChecked(glitches_enabled)
        glitch_act.triggered.connect(
            lambda *_: self.window.process_input("глитч")
        )

    def _add_audio_section(self, parent_menu: QMenu) -> None:
        self._add_asr_model_menu(parent_menu)
        self._add_sound_menu(parent_menu)
        self._add_volume_menu(parent_menu)
        self._add_microphone_menu(parent_menu)

    def _add_visual_section(self, parent_menu: QMenu) -> None:

        self._add_scale_menu(parent_menu)
        self._add_glitch_intensity_menu(parent_menu)
        self._add_screen_menu(parent_menu)

    def _add_behavior_section(self, parent_menu: QMenu) -> None:

        self._add_activity_timeout_menu(parent_menu)
        self._add_reminder_toggle(parent_menu)
        self._add_discord_rpc_toggle(parent_menu)

    def _add_discord_rpc_toggle(self, parent_menu: QMenu) -> None:
        orchestrator = getattr(self.window, "_orchestrator", None)
        is_enabled = getattr(orchestrator, "_discord_enabled", True) if orchestrator else True

        rpc_act = parent_menu.addAction("▶  [DISCORD] Discord Rich Presence")
        rpc_act.setCheckable(True)
        rpc_act.setChecked(is_enabled)
        rpc_act.triggered.connect(
            lambda checked: self.window.set_discord_enabled(checked)
        )

    def _add_screen_menu(self, parent_menu: QMenu) -> None:
        screen_menu = self._add_submenu(parent_menu, "◇  [DISP] Монитор")
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
        mic_menu = self._add_submenu(parent_menu, "◇  [AUDIO.IN] Входной микрофон")
        mic_group = QActionGroup(mic_menu)
        mic_group.setExclusive(True)

        current_mic = getattr(self.window, "selected_microphone", None)
        if current_mic is None and hasattr(self.window, "voice_coordinator"):
            current_mic = self.window.voice_coordinator.selected_device
        elif current_mic is None and hasattr(self.window, "_voice"):
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

    def _add_asr_model_menu(self, parent_menu: QMenu) -> None:
        model_menu = self._add_submenu(parent_menu, "◇  [ASR.CORE] Модель распознавания")
        group = QActionGroup(model_menu)
        group.setExclusive(True)

        from ..audio.recognizer import get_backend

        current_backend = get_backend()
        options = (
            ("vosk", "Vosk (быстрая, легковесная, ru)"),
            ("whisper", "Faster-Whisper (мультиязычная, ru/en)"),
        )
        for key, label in options:
            act = model_menu.addAction(label)
            act.setCheckable(True)
            if current_backend == key:
                act.setChecked(True)
            act.triggered.connect(
                lambda *_, k=key: self.window.set_asr_backend(k)
            )
            group.addAction(act)

    def _add_sound_menu(self, parent_menu: QMenu) -> None:
        sound_menu = self._add_submenu(parent_menu, "◇  [AUDIO.FX] Звуковые эффекты")
        speech_sfx = get_speech_sfx()

        msg_sound_act = sound_menu.addAction("▶  [SYNTH] Синтез речи (SFX)")
        msg_sound_act.setCheckable(True)
        msg_sound_act.setChecked(speech_sfx.is_speech_sound_enabled())
        msg_sound_act.triggered.connect(
            lambda checked: self.window.set_speech_sound_enabled(checked)
        )

        fx_sound_act = sound_menu.addAction("▶  [UI] UI эффекты")
        fx_sound_act.setCheckable(True)
        fx_sound_act.setChecked(speech_sfx.is_effects_sound_enabled())
        fx_sound_act.triggered.connect(
            lambda checked: self.window.set_effects_sound_enabled(checked)
        )

    def _add_volume_menu(self, parent_menu: QMenu) -> None:
        volume_menu = self._add_submenu(parent_menu, "◇  [VOL] Громкость SFX")
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
        size_menu = self._add_submenu(parent_menu, "◇  [SCALE] Масштаб проекции")
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
        intensity_menu = self._add_submenu(parent_menu, "◇  [FX.RATE] Интенсивность глитчей")
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
        timeout_menu = self._add_submenu(parent_menu, "◇  [STANDBY] Таймаут ухода в сон")
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
        remind_menu = parent_menu.addMenu("▶  [AUTONOMY] Автономные реплики")
        remind_act = remind_menu.addAction("Включить реплики")
        remind_act.setCheckable(True)
        remind_act.setChecked(bool(getattr(self.window, "reminders_enabled", True)))
        remind_act.triggered.connect(
            lambda checked: self.window.set_reminders_enabled(checked)
        )

        remind_menu.addSeparator()
        range_menu = remind_menu.addMenu("Частота напоминаний")
        range_group = QActionGroup(self.window)

        intervals = (
            ("Часто (1 – 5 мин)", 60_000, 300_000),
            ("Обычно (10 – 60 мин)", 600_000, 3_600_000),
            ("Редко (30 – 120 мин)", 1_800_000, 7_200_000),
        )

        curr_range = getattr(
            self.window, "reminder_interval_range", (600_000, 3_600_000)
        )
        is_preset_matched = False
        for label, min_ms, max_ms in intervals:
            act = range_menu.addAction(label)
            act.setCheckable(True)
            if abs(curr_range[0] - min_ms) < 1000 and abs(curr_range[1] - max_ms) < 1000:
                act.setChecked(True)
                is_preset_matched = True
            act.triggered.connect(
                lambda *_, mn=min_ms, mx=max_ms: self.window.set_reminder_interval_range(mn, mx)
            )
            range_group.addAction(act)

        range_menu.addSeparator()
        curr_min_m = max(1, round(curr_range[0] / 60_000))
        curr_max_m = max(curr_min_m, round(curr_range[1] / 60_000))
        custom_label = (
            f"Своя частота ({curr_min_m} – {curr_max_m} мин)..."
            if not is_preset_matched
            else "Своя частота..."
        )
        custom_act = range_menu.addAction(custom_label)
        custom_act.setCheckable(True)
        if not is_preset_matched:
            custom_act.setChecked(True)
        custom_act.triggered.connect(self._prompt_custom_reminder_range)
        range_group.addAction(custom_act)

    def _prompt_custom_reminder_range(self) -> None:
        parent_widget = self.window if isinstance(self.window, QWidget) else None
        curr_range = getattr(
            self.window, "reminder_interval_range", (600_000, 3_600_000)
        )
        init_min = max(1, round(curr_range[0] / 60_000))
        init_max = max(init_min, round(curr_range[1] / 60_000))

        dlg = QDialog(parent_widget)
        dlg.setWindowTitle("ДИАПАЗОН НАПОМИНАНИЙ")
        dlg.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.CustomizeWindowHint | Qt.WindowType.WindowTitleHint | Qt.WindowType.WindowCloseButtonHint)
        dlg.setStyleSheet(
            f"""
            QDialog {{
                background-color: {OBSIDIAN_BLACK};
                border: 1px solid {NEON_CRIMSON};
                color: {PURE_WHITE};
                font-family: {CSS_CYBER_UI};
            }}
            QLabel {{
                color: {PURE_WHITE};
                font-size: 12px;
            }}
            QSpinBox {{
                background-color: #110e1a;
                border: 1px solid {NEON_CRIMSON};
                color: {PURE_WHITE};
                padding: 4px 8px;
                font-family: {CSS_CYBER_TERMINAL};
                font-size: 13px;
                selection-background-color: {NEON_CRIMSON};
            }}
            QSpinBox:focus {{
                border: 1px solid {ACID_GREEN};
            }}
            QPushButton {{
                background-color: #110e1a;
                border: 1px solid {NEON_CRIMSON};
                color: {PURE_WHITE};
                font-size: 12px;
                padding: 6px 16px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                border-color: {ACID_GREEN};
                color: {ACID_GREEN};
            }}
            QPushButton:pressed {{
                background-color: rgba(246, 2, 63, 0.3);
            }}
            """
        )

        layout = QVBoxLayout(dlg)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)

        header = QLabel("Настройка частоты автономных реплик (в минутах):")
        header.setStyleSheet(f"color: {ACID_GREEN}; font-weight: bold; font-size: 12px;")
        layout.addWidget(header)

        inputs_layout = QHBoxLayout()
        inputs_layout.setSpacing(10)

        lbl_from = QLabel("От:")
        spin_from = QSpinBox()
        spin_from.setRange(1, 1440)
        spin_from.setValue(init_min)
        spin_from.setSuffix(" мин")

        lbl_to = QLabel("До:")
        spin_to = QSpinBox()
        spin_to.setRange(1, 1440)
        spin_to.setValue(init_max)
        spin_to.setSuffix(" мин")

        def _on_from_changed(val: int) -> None:
            if spin_to.value() < val:
                spin_to.setValue(val)

        def _on_to_changed(val: int) -> None:
            if spin_from.value() > val:
                spin_from.setValue(val)

        spin_from.valueChanged.connect(_on_from_changed)
        spin_to.valueChanged.connect(_on_to_changed)

        inputs_layout.addWidget(lbl_from)
        inputs_layout.addWidget(spin_from)
        inputs_layout.addWidget(lbl_to)
        inputs_layout.addWidget(spin_to)
        layout.addLayout(inputs_layout)

        btns_layout = QHBoxLayout()
        btns_layout.addStretch()
        btn_cancel = QPushButton("ОТМЕНА")
        btn_ok = QPushButton("ПРИМЕНИТЬ")
        btn_cancel.clicked.connect(dlg.reject)
        btn_ok.clicked.connect(dlg.accept)
        btns_layout.addWidget(btn_cancel)
        btns_layout.addWidget(btn_ok)
        layout.addLayout(btns_layout)

        if dlg.exec() == QDialog.DialogCode.Accepted:
            min_m = spin_from.value()
            max_m = max(min_m, spin_to.value())
            min_ms = min_m * 60_000
            max_ms = max_m * 60_000
            self.window.set_reminder_interval_range(min_ms, max_ms)
            if hasattr(self.window, "speak"):
                self.window.speak(f"Частота напоминаний: {min_m}–{max_m} мин.")

def build_pet_context_menu(window: Any, _pos: QPoint | None = None) -> QMenu:
    builder = ContextMenuBuilder(window)
    return builder.build(for_tray=False)

def build_tray_context_menu(window: Any) -> QMenu:
    builder = ContextMenuBuilder(window)
    return builder.build(for_tray=True)

class TrayManager:

    def __init__(self, window: CapriWindow) -> None:
        self._window = window
        self._tray_icon: QSystemTrayIcon | None = None
        self._tray_menu = None
        self.init_tray()

    @property
    def tray_icon(self) -> QSystemTrayIcon | None:
        return self._tray_icon

    def init_tray(self) -> None:
        icon = QIcon(str(CAPRI_ICON))
        if icon.isNull():
            pix = self._window.pixmap if hasattr(self._window, "pixmap") and not self._window.pixmap.isNull() else QPixmap(32, 32)
            icon = QIcon(pix)

        self._window.setWindowIcon(icon)
        app = QApplication.instance()
        if app is not None:
            app.setWindowIcon(icon)

        self._tray_icon = QSystemTrayIcon(icon, self._window)
        self._tray_icon.setToolTip("CapriPet")

        self._tray_menu = build_tray_context_menu(self._window)
        self._tray_icon.setContextMenu(self._tray_menu)

        self._tray_icon.activated.connect(self._on_tray_activated)
        self._tray_icon.show()

    def _on_tray_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason in (
            QSystemTrayIcon.ActivationReason.Trigger,
            QSystemTrayIcon.ActivationReason.DoubleClick,
        ):
            self._window.activate_command_mode()


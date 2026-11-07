"""Контекстное меню и управление системным треем CapriPet.

Предоставляет киберпанк-стилизованное меню, диалог настройки интервалов
напоминаний и интеграцию с областью уведомлений Windows.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

from PySide6.QtCore import QPoint, QRect, Qt
from PySide6.QtGui import (
    QActionGroup,
    QColor,
    QGuiApplication,
    QIcon,
    QMouseEvent,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
)
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
    OBSIDIAN_BLACK,
    PURE_WHITE,
    get_hud_font,
)

if TYPE_CHECKING:
    from .pet_window import CapriWindow

_CORNER_CUT = 10
CAPRI_ICON = (
    Path(__file__).resolve().parent.parent.parent
    / "assets"
    / "capri_icon.png"
)


class CyberMenu(QMenu):
    """Стилизованное всплывающее контекстное меню в эстетике киберпанк."""

    def __init__(
        self, parent: QWidget | None = None, title: str = ""
    ) -> None:
        super().__init__(title, parent)
        self.setStyleSheet(CYBER_MENU_STYLE)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)

        rect = self.rect().adjusted(0, 0, -1, -1)
        w = rect.width()
        h = rect.height()
        c = 14

        path = QPainterPath()
        path.moveTo(0, 0)
        path.lineTo(w - c, 0)
        path.lineTo(w, c)
        path.lineTo(w, h)
        path.lineTo(0, h)
        path.closeSubpath()

        painter.fillPath(path, QColor(OBSIDIAN_BLACK))

        painter.save()
        painter.setClipPath(path)
        scan_pen = QPen(QColor(246, 2, 63, 14), 1)
        painter.setPen(scan_pen)
        for y in range(rect.top() + 3, rect.bottom(), 3):
            painter.drawLine(rect.left(), y, rect.right(), y)
        painter.restore()

        crimson_pen = QPen(QColor(NEON_CRIMSON), 1)
        painter.strokePath(path, crimson_pen)

        accent_pen = QPen(QColor(ACID_GREEN), 2)
        painter.setPen(accent_pen)
        painter.drawLine(w - c, 0, w, c)

        painter.drawLine(0, 0, 10, 0)
        painter.drawLine(0, 0, 0, 10)
        painter.drawLine(0, h - 10, 0, h)
        painter.drawLine(0, h, 10, h)
        painter.drawLine(w - 10, h, w, h)
        painter.drawLine(w, h - 10, w, h)

        painter.fillRect(QRect(w - 24, 3, 10, 2), QColor(ACID_GREEN))
        painter.fillRect(QRect(w - 12, 3, 6, 2), QColor(ELECTRIC_BLUE))
        painter.fillRect(QRect(3, h - 5, 8, 2), QColor(PURE_WHITE))

        painter.end()
        super().paintEvent(event)


class ReminderRangeDialog(QDialog):
    """Диалоговое окно настройки пользовательского диапазона интервалов напоминаний."""

    def __init__(
        self,
        init_min: int,
        init_max: int,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(
            parent,
            Qt.WindowType.Dialog
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint,
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setWindowTitle("CAPRI // REMINDER_CONFIG")
        self._drag_pos: QPoint | None = None
        self._chamfer = 14
        self._shadow_offset = 6

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 32, 18, 18)
        layout.setSpacing(14)

        header = QLabel("НАСТРОЙКА ЧАСТОТЫ РЕПЛИК (МИН)")
        header.setStyleSheet(
            f"color: {ACID_GREEN}; font-family: {CSS_CYBER_TERMINAL}; font-weight: bold; font-size: 11px; letter-spacing: 1px;"
        )
        layout.addWidget(header)

        inputs_layout = QHBoxLayout()
        inputs_layout.setSpacing(12)

        lbl_from = QLabel("ОТ:")
        lbl_from.setStyleSheet(
            f"color: {PURE_WHITE}; font-family: {CSS_CYBER_TERMINAL}; font-size: 11px; font-weight: bold;"
        )
        self.spin_from = QSpinBox()
        self.spin_from.setRange(1, 1440)
        self.spin_from.setValue(init_min)
        self.spin_from.setSuffix(" МИН")

        lbl_to = QLabel("ДО:")
        lbl_to.setStyleSheet(
            f"color: {PURE_WHITE}; font-family: {CSS_CYBER_TERMINAL}; font-size: 11px; font-weight: bold;"
        )
        self.spin_to = QSpinBox()
        self.spin_to.setRange(1, 1440)
        self.spin_to.setValue(init_max)
        self.spin_to.setSuffix(" МИН")

        spin_style = f"""
        QSpinBox {{
            background-color: {OBSIDIAN_BLACK};
            border: 1px solid {NEON_CRIMSON};
            color: {PURE_WHITE};
            padding: 5px 8px;
            font-family: {CSS_CYBER_TERMINAL};
            font-size: 12px;
            font-weight: bold;
            selection-background-color: {NEON_CRIMSON};
        }}
        QSpinBox:focus {{
            border: 1px solid {ACID_GREEN};
        }}
        QSpinBox::up-button, QSpinBox::down-button {{
            background-color: {OBSIDIAN_BLACK};
            border-left: 1px solid {NEON_CRIMSON};
            width: 16px;
        }}
        QSpinBox::up-button:hover, QSpinBox::down-button:hover {{
            background-color: rgba(246, 2, 63, 0.35);
        }}
        """
        self.spin_from.setStyleSheet(spin_style)
        self.spin_to.setStyleSheet(spin_style)

        self.spin_from.valueChanged.connect(self._on_from_changed)
        self.spin_to.valueChanged.connect(self._on_to_changed)

        inputs_layout.addWidget(lbl_from)
        inputs_layout.addWidget(self.spin_from)
        inputs_layout.addWidget(lbl_to)
        inputs_layout.addWidget(self.spin_to)
        layout.addLayout(inputs_layout)

        btns_layout = QHBoxLayout()
        btns_layout.addStretch()

        btn_cancel = QPushButton("ОТМЕНА")
        btn_ok = QPushButton("ПРИМЕНИТЬ")
        btn_cancel.clicked.connect(self.reject)
        btn_ok.clicked.connect(self.accept)

        btn_style = f"""
        QPushButton {{
            background-color: {OBSIDIAN_BLACK};
            border: 1px solid {NEON_CRIMSON};
            color: {PURE_WHITE};
            font-family: {CSS_CYBER_UI};
            font-size: 11px;
            padding: 6px 16px;
            font-weight: bold;
            letter-spacing: 1px;
        }}
        QPushButton:hover {{
            border-color: {ACID_GREEN};
            color: {ACID_GREEN};
            background-color: rgba(6, 248, 104, 0.1);
        }}
        QPushButton:pressed {{
            background-color: rgba(246, 2, 63, 0.35);
            border-color: {NEON_CRIMSON};
            color: {PURE_WHITE};
        }}
        """
        btn_cancel.setStyleSheet(btn_style)
        btn_ok.setStyleSheet(btn_style)

        btns_layout.addWidget(btn_cancel)
        btns_layout.addWidget(btn_ok)
        layout.addLayout(btns_layout)

    def _on_from_changed(self, val: int) -> None:
        if self.spin_to.value() < val:
            self.spin_to.setValue(val)

    def _on_to_changed(self, val: int) -> None:
        if self.spin_from.value() > val:
            self.spin_from.setValue(val)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = (
                event.globalPosition().toPoint()
                - self.frameGeometry().topLeft()
            )
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if (
            self._drag_pos is not None
            and event.buttons() & Qt.MouseButton.LeftButton
        ):
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        self._drag_pos = None
        super().mouseReleaseEvent(event)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)

        w = self.width()
        h = self.height()
        c = self._chamfer
        so = self._shadow_offset

        bw = max(1, w - so)
        bh = max(1, h - so)

        path = QPainterPath()
        path.moveTo(0, 0)
        path.lineTo(bw - c, 0)
        path.lineTo(bw, c)
        path.lineTo(bw, bh)
        path.lineTo(0, bh)
        path.closeSubpath()

        shadow_path = path.translated(so, so)
        painter.fillPath(shadow_path, QColor(246, 2, 63, 85))

        painter.fillPath(path, QColor(2, 1, 6, 248))

        painter.save()
        painter.setClipPath(path)
        scanline_pen = QPen(QColor(246, 2, 63, 14), 1)
        painter.setPen(scanline_pen)
        for y in range(0, bh, 3):
            painter.drawLine(0, y, bw, y)
        painter.restore()

        crimson_pen = QPen(QColor(NEON_CRIMSON), 2)
        painter.strokePath(path, crimson_pen)

        accent_pen = QPen(QColor(ACID_GREEN), 2)
        painter.setPen(accent_pen)
        painter.drawLine(bw - c, 0, bw, c)

        painter.drawLine(0, 0, 10, 0)
        painter.drawLine(0, 0, 0, 10)
        painter.drawLine(0, bh - 10, 0, bh)
        painter.drawLine(0, bh, 10, bh)
        painter.drawLine(bw - 10, bh, bw, bh)
        painter.drawLine(bw, bh - 10, bw, bh)

        badge_rect = QRect(14, 6, max(10, bw - c - 20), 16)
        painter.fillRect(QRect(12, 6, 175, 16), QColor(246, 2, 63, 40))
        painter.setPen(QColor(ACID_GREEN))
        painter.setFont(get_hud_font(10, bold=True))
        painter.drawText(
            badge_rect,
            Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
            "[CAPRI://AUTONOMY_RANGE]",
        )

        painter.fillRect(QRect(bw - 26, 7, 10, 2), QColor(ACID_GREEN))
        painter.fillRect(QRect(bw - 13, 7, 6, 2), QColor(ELECTRIC_BLUE))


class ContextMenuBuilder:
    """Конструктор контекстного меню управления питомцем и системного трея."""

    def __init__(self, window: Any) -> None:
        self.window = window

    def build(self, for_tray: bool = False) -> QMenu:

        menu = CyberMenu(
            self.window if isinstance(self.window, QWidget) else None
        )

        hdr = menu.addAction("▶ CAPRI//NEURAL_LINK [ONLINE]")
        hdr.setEnabled(False)
        menu.addSeparator()

        if for_tray:
            call_act = menu.addAction("▲  [SUMMON] Позвать Капри")
            trigger_fn = getattr(
                self.window,
                "activate_command_mode",
                getattr(self.window, "show", None),
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
        self._add_game_mode_toggle(parent_menu)

    def _add_game_mode_toggle(self, parent_menu: QMenu) -> None:
        game_enabled = getattr(
            self.window, "game_suppression_enabled", True
        )
        game_act = parent_menu.addAction(
            "▶  [GAME] Игровой режим (тишина)"
        )
        game_act.setCheckable(True)
        game_act.setChecked(game_enabled)
        game_act.triggered.connect(
            lambda checked: (
                self.window.set_game_suppression_enabled(checked)
                if hasattr(self.window, "set_game_suppression_enabled")
                else None
            )
        )

    def _add_quick_actions(self, parent_menu: QMenu) -> None:
        orchestrator = getattr(self.window, "_orchestrator", None)
        rpc_enabled = (
            getattr(orchestrator, "_discord_enabled", True)
            if orchestrator
            else True
        )

        rpc_act = parent_menu.addAction(
            "▶  [DISCORD] Discord Rich Presence"
        )
        rpc_act.setCheckable(True)
        rpc_act.setChecked(rpc_enabled)
        rpc_act.triggered.connect(
            lambda checked: self.window.set_discord_enabled(checked)
        )

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
        mic_menu = self._add_submenu(
            parent_menu, "◇  [AUDIO.IN] Входной микрофон"
        )
        mic_group = QActionGroup(mic_menu)
        mic_group.setExclusive(True)

        current_mic = getattr(self.window, "selected_microphone", None)
        if current_mic is None and hasattr(
            self.window, "voice_coordinator"
        ):
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
        model_menu = self._add_submenu(
            parent_menu, "◇  [ASR.CORE] Модель распознавания"
        )
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
        sound_menu = self._add_submenu(
            parent_menu, "◇  [AUDIO.FX] Звуковые эффекты"
        )
        speech_sfx = get_speech_sfx()

        msg_sound_act = sound_menu.addAction(
            "▶  [SYNTH] Синтез речи (SFX)"
        )
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
        volume_menu = self._add_submenu(
            parent_menu, "◇  [VOL] Громкость SFX"
        )
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
        size_menu = self._add_submenu(
            parent_menu, "◇  [SCALE] Масштаб проекции"
        )
        size_group = QActionGroup(size_menu)
        size_group.setExclusive(True)

        current_scale = getattr(
            self.window,
            "scale_percent",
            getattr(self.window, "_scale_percent", 100),
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
        intensity_menu = self._add_submenu(
            parent_menu, "◇  [FX.RATE] Интенсивность глитчей"
        )
        group = QActionGroup(intensity_menu)
        group.setExclusive(True)

        current_intensity = getattr(
            self.window, "glitch_intensity", "weak"
        )
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
        timeout_menu = self._add_submenu(
            parent_menu, "◇  [STANDBY] Таймаут ухода в сон"
        )
        timeout_group = QActionGroup(timeout_menu)
        timeout_group.setExclusive(True)

        current_seconds = getattr(
            self.window,
            "activity_timeout_seconds",
            ACTIVITY_TIMEOUT_OPTIONS_MS[0] // 1000,
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
        remind_menu = parent_menu.addMenu(
            "▶  [AUTONOMY] Автономные реплики"
        )
        remind_act = remind_menu.addAction("Включить реплики")
        remind_act.setCheckable(True)
        remind_act.setChecked(
            bool(getattr(self.window, "reminders_enabled", True))
        )
        remind_act.triggered.connect(
            lambda checked: self.window.set_reminders_enabled(checked)
        )

        remind_menu.addSeparator()
        range_menu = remind_menu.addMenu("Частота напоминаний")
        range_group = QActionGroup(range_menu)

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
            if (
                abs(curr_range[0] - min_ms) < 1000
                and abs(curr_range[1] - max_ms) < 1000
            ):
                act.setChecked(True)
                is_preset_matched = True
            act.triggered.connect(
                lambda *_, mn=min_ms, mx=max_ms: (
                    self.window.set_reminder_interval_range(mn, mx)
                )
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
        parent_widget = (
            self.window if isinstance(self.window, QWidget) else None
        )
        curr_range = getattr(
            self.window, "reminder_interval_range", (600_000, 3_600_000)
        )
        init_min = max(1, round(curr_range[0] / 60_000))
        init_max = max(init_min, round(curr_range[1] / 60_000))

        dlg = ReminderRangeDialog(init_min, init_max, parent_widget)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            min_m = dlg.spin_from.value()
            max_m = max(min_m, dlg.spin_to.value())
            min_ms = min_m * 60_000
            max_ms = max_m * 60_000
            self.window.set_reminder_interval_range(min_ms, max_ms)
            if hasattr(self.window, "speak"):
                self.window.speak(
                    f"Частота напоминаний: {min_m}–{max_m} мин."
                )


def build_pet_context_menu(
    window: Any, _pos: QPoint | None = None
) -> QMenu:
    builder = ContextMenuBuilder(window)
    return builder.build(for_tray=False)


def build_tray_context_menu(window: Any) -> QMenu:
    builder = ContextMenuBuilder(window)
    return builder.build(for_tray=True)


class TrayManager:
    """Менеджер интеграции с системным треем операционной системы."""

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
            pix = (
                self._window.pixmap
                if hasattr(self._window, "pixmap")
                and not self._window.pixmap.isNull()
                else QPixmap(32, 32)
            )
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

    def _on_tray_activated(
        self, reason: QSystemTrayIcon.ActivationReason
    ) -> None:
        if reason in (
            QSystemTrayIcon.ActivationReason.Trigger,
            QSystemTrayIcon.ActivationReason.DoubleClick,
        ):
            self._window.activate_command_mode()

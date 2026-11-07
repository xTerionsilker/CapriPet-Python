"""Цветовая палитра, типографика и стили интерфейса в эстетике киберпанк.

Определяет корпоративную 6-цветовую палитру проекта, загрузку шрифтов
семейства Exo 2 и каскадные таблицы стилей (QSS) для элементов управления.
"""

from __future__ import annotations

import logging
from pathlib import Path

from PySide6.QtGui import QFont, QFontDatabase

logger = logging.getLogger(__name__)

FONT_FAMILY = "Exo 2"
CSS_FONT = f'"{FONT_FAMILY}", sans-serif'

FONT_CYBER_TERMINAL = FONT_FAMILY
FONT_CYBER_HUD = FONT_FAMILY
FONT_CYBER_UI = FONT_FAMILY

CSS_CYBER_TERMINAL = CSS_FONT
CSS_CYBER_HUD = CSS_FONT
CSS_CYBER_UI = CSS_FONT

_FONTS_LOADED = False


def init_fonts() -> None:
    global _FONTS_LOADED
    if _FONTS_LOADED:
        return

    fonts_dir = Path(__file__).resolve().parents[2] / "assets" / "fonts"
    if not fonts_dir.is_dir():
        logger.warning("Fonts directory not found at: %s", fonts_dir)
        return

    for font_file in fonts_dir.glob("*.ttf"):
        font_id = QFontDatabase.addApplicationFont(str(font_file))
        if font_id == -1:
            logger.warning("Failed to load font from: %s", font_file)
        else:
            families = QFontDatabase.applicationFontFamilies(font_id)
            logger.debug("Loaded font %s -> %s", font_file.name, families)

    _FONTS_LOADED = True


def get_font(
    pixel_size: int = 12,
    bold: bool = False,
    weight: QFont.Weight | None = None,
) -> QFont:
    init_fonts()
    font = QFont(FONT_FAMILY)
    font.setStyleHint(QFont.StyleHint.SansSerif)
    font.setPixelSize(pixel_size)
    if weight is not None:
        font.setWeight(weight)
    elif bold:
        font.setBold(True)
    return font


def get_terminal_font(pixel_size: int = 13, bold: bool = False) -> QFont:
    return get_font(pixel_size=pixel_size, bold=bold)


def get_hud_font(pixel_size: int = 11, bold: bool = False) -> QFont:
    return get_font(pixel_size=pixel_size, bold=bold)


def get_ui_font(pixel_size: int = 12, bold: bool = False) -> QFont:
    return get_font(pixel_size=pixel_size, bold=bold)


PIXEL_FONT = CSS_CYBER_TERMINAL

NEON_CRIMSON = "#F6023F"
OBSIDIAN_BLACK = "#020106"
ACID_GREEN = "#06F868"
PURE_WHITE = "#F9F9F9"
ELECTRIC_BLUE = "#126EE9"
NEON_VIOLET = "#9E1FDE"

_MENU_ARROW = (
    Path(__file__).resolve().parents[2] / "assets" / "menu_arrow.svg"
).as_posix()

CYBER_MENU_STYLE = f"""
QMenu {{
    background-color: {OBSIDIAN_BLACK};
    border: 1px solid {NEON_CRIMSON};
    padding: 6px 4px 6px 4px;
    color: {PURE_WHITE};
    font-family: {CSS_CYBER_UI};
    font-size: 13px;
    letter-spacing: 0.5px;
}}
QMenu::item {{
    background: transparent;
    padding: 6px 26px 6px 24px;
    margin: 1px 2px;
    border-left: 2px solid transparent;
    color: {PURE_WHITE};
}}
QMenu::item:selected {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 rgba(246, 2, 63, 0.9),
        stop:0.65 rgba(246, 2, 63, 0.4),
        stop:1 rgba(2, 1, 6, 0.2));
    color: {PURE_WHITE};
    border-left: 2px solid {ACID_GREEN};
}}
QMenu::item:disabled {{
    color: rgba(246, 2, 63, 0.7);
    background: rgba(246, 2, 63, 0.08);
    font-weight: bold;
    border-left: 2px solid {NEON_CRIMSON};
}}
QMenu::separator {{
    height: 1px;
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 {NEON_CRIMSON},
        stop:0.4 {NEON_VIOLET},
        stop:0.8 {ELECTRIC_BLUE},
        stop:1 transparent);
    margin: 5px 6px;
}}
QMenu::indicator {{
    width: 8px;
    height: 8px;
    margin-left: 8px;
}}
QMenu::indicator:checked {{
    background-color: {ACID_GREEN};
    border: 1px solid {PURE_WHITE};
}}
QMenu::indicator:unchecked {{
    background-color: {OBSIDIAN_BLACK};
    border: 1px solid {NEON_VIOLET};
}}
QMenu::right-arrow {{
    image: url("{_MENU_ARROW}");
    width: 9px;
    height: 9px;
    margin-right: 8px;
}}
QMenu::scroller {{
    height: 16px;
    background: {OBSIDIAN_BLACK};
    border: 1px solid {NEON_CRIMSON};
}}
"""

APP_STYLE = f"""
QWidget {{
    background: {OBSIDIAN_BLACK};
    color: {PURE_WHITE};
    font-family: {PIXEL_FONT};
    font-size: 13px;
}}
QVideoWidget {{
    background: {OBSIDIAN_BLACK};
    border: none;
    border-bottom: 2px solid {NEON_CRIMSON};
}}
#panel {{
    background: {OBSIDIAN_BLACK};
    border-top: 2px solid {NEON_CRIMSON};
}}
#panel QLabel {{ background: transparent; }}
#accent {{
    border: none;
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 {NEON_CRIMSON},
        stop:0.45 {NEON_CRIMSON},
        stop:0.7 {NEON_VIOLET},
        stop:0.85 {ELECTRIC_BLUE},
        stop:1 {ACID_GREEN});
}}
#prompt {{
    color: {NEON_CRIMSON};
    font-weight: 700;
    font-size: 15px;
    letter-spacing: 1px;
}}
#status {{
    color: {ACID_GREEN};
    font-size: 11px;
    letter-spacing: 2px;
}}
QLineEdit {{
    background: {OBSIDIAN_BLACK};
    border: 1px solid {NEON_CRIMSON};
    border-radius: 0;
    padding: 8px 10px;
    color: {PURE_WHITE};
    placeholder-text-color: rgba(246, 2, 63, 0.4);
    selection-background-color: {NEON_CRIMSON};
    selection-color: {OBSIDIAN_BLACK};
}}
QLineEdit:focus {{
    border: 1px solid {ACID_GREEN};
    background: {OBSIDIAN_BLACK};
}}
QPushButton {{
    background: {NEON_CRIMSON};
    color: {PURE_WHITE};
    border: 1px solid {NEON_CRIMSON};
    border-radius: 0;
    padding: 8px 20px;
    font-weight: 800;
    letter-spacing: 2px;
}}
QPushButton:hover {{
    background: {ACID_GREEN};
    color: {OBSIDIAN_BLACK};
    border-color: {ACID_GREEN};
}}
QPushButton:pressed {{
    background: {ELECTRIC_BLUE};
    color: {PURE_WHITE};
    border-color: {ELECTRIC_BLUE};
    padding: 9px 20px 7px;
}}
QMenu {{
    background-color: {OBSIDIAN_BLACK};
    border: 1px solid {NEON_CRIMSON};
    padding: 6px 4px 6px 4px;
    color: {PURE_WHITE};
    font-family: {CSS_CYBER_UI};
    font-size: 13px;
    letter-spacing: 0.5px;
}}
QMenu::item {{
    background: transparent;
    padding: 6px 26px 6px 24px;
    margin: 1px 2px;
    border-left: 2px solid transparent;
    color: {PURE_WHITE};
}}
QMenu::item:selected {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 rgba(246, 2, 63, 0.9),
        stop:0.65 rgba(246, 2, 63, 0.4),
        stop:1 rgba(2, 1, 6, 0.2));
    color: {PURE_WHITE};
    border-left: 2px solid {ACID_GREEN};
}}
QMenu::item:disabled {{
    color: rgba(246, 2, 63, 0.7);
    background: rgba(246, 2, 63, 0.08);
    font-weight: bold;
    border-left: 2px solid {NEON_CRIMSON};
}}
QMenu::separator {{
    height: 1px;
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 {NEON_CRIMSON},
        stop:0.4 {NEON_VIOLET},
        stop:0.8 {ELECTRIC_BLUE},
        stop:1 transparent);
    margin: 5px 6px;
}}
QMenu::indicator {{
    width: 8px;
    height: 8px;
    margin-left: 8px;
}}
QMenu::indicator:checked {{
    background-color: {ACID_GREEN};
    border: 1px solid {PURE_WHITE};
}}
QMenu::indicator:unchecked {{
    background-color: {OBSIDIAN_BLACK};
    border: 1px solid {NEON_VIOLET};
}}
"""

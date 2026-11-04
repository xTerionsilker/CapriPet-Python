from __future__ import annotations

import logging
from pathlib import Path
from PySide6.QtGui import QFont, QFontDatabase

logger = logging.getLogger(__name__)

# Fallback families mapped to loaded fonts
FONT_CYBER_TERMINAL = "VT323"
FONT_CYBER_HUD = "Share Tech Mono"
FONT_CYBER_UI = "Exo 2"

# CSS strings for stylesheets
CSS_CYBER_TERMINAL = f'"{FONT_CYBER_TERMINAL}", monospace'
CSS_CYBER_HUD = f'"{FONT_CYBER_HUD}", monospace'
CSS_CYBER_UI = f'"{FONT_CYBER_UI}", sans-serif'

_FONTS_LOADED = False


def init_fonts() -> None:
    """Load application fonts from assets/fonts into QFontDatabase."""
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


def get_terminal_font(pixel_size: int = 14, bold: bool = False) -> QFont:
    """Font for pet dialogues, speech bubbles, and retro-terminal text (VT323)."""
    init_fonts()
    font = QFont(FONT_CYBER_TERMINAL)
    font.setStyleHint(QFont.StyleHint.Monospace)
    font.setPixelSize(pixel_size)
    if bold:
        font.setBold(True)
    return font


def get_hud_font(pixel_size: int = 12, bold: bool = False) -> QFont:
    """Font for HUD, audio recognizer status, logs and telemetry (Share Tech Mono)."""
    init_fonts()
    font = QFont(FONT_CYBER_HUD)
    font.setStyleHint(QFont.StyleHint.Monospace)
    font.setPixelSize(pixel_size)
    if bold:
        font.setBold(True)
    return font


def get_ui_font(pixel_size: int = 11, bold: bool = False) -> QFont:
    """Font for general UI, context menus, buttons (Exo 2)."""
    init_fonts()
    font = QFont(FONT_CYBER_UI)
    font.setStyleHint(QFont.StyleHint.SansSerif)
    font.setPixelSize(pixel_size)
    if bold:
        font.setBold(True)
    return font

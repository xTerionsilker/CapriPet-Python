from __future__ import annotations

import logging
from pathlib import Path
from PySide6.QtGui import QFont, QFontDatabase

logger = logging.getLogger(__name__)

# Single unified cyberpunk font across the entire project
FONT_FAMILY = "Exo 2"
CSS_FONT = f'"{FONT_FAMILY}", sans-serif'

# Backward compatibility aliases
FONT_CYBER_TERMINAL = FONT_FAMILY
FONT_CYBER_HUD = FONT_FAMILY
FONT_CYBER_UI = FONT_FAMILY

CSS_CYBER_TERMINAL = CSS_FONT
CSS_CYBER_HUD = CSS_FONT
CSS_CYBER_UI = CSS_FONT

_FONTS_LOADED = False


def init_fonts() -> None:
    """Load Exo 2 fonts from assets/fonts into QFontDatabase."""
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


def get_font(pixel_size: int = 12, bold: bool = False, weight: QFont.Weight | None = None) -> QFont:
    """Unified font getter using Exo 2 with full Latin and Cyrillic support."""
    init_fonts()
    font = QFont(FONT_FAMILY)
    font.setStyleHint(QFont.StyleHint.SansSerif)
    font.setPixelSize(pixel_size)
    if weight is not None:
        font.setWeight(weight)
    elif bold:
        font.setBold(True)
    return font


# Semantic aliases for easy usage across modules
def get_terminal_font(pixel_size: int = 13, bold: bool = False) -> QFont:
    return get_font(pixel_size=pixel_size, bold=bold)


def get_hud_font(pixel_size: int = 11, bold: bool = False) -> QFont:
    return get_font(pixel_size=pixel_size, bold=bold)


def get_ui_font(pixel_size: int = 12, bold: bool = False) -> QFont:
    return get_font(pixel_size=pixel_size, bold=bold)

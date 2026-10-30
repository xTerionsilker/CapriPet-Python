from pathlib import Path

PIXEL_FONT = (
    '"Press Start 2P", "Pixelify Sans", "VT323", "Terminus", '
    '"DejaVu Sans Mono", monospace'
)

# Строгая палитра персонажа.
NEON_CRIMSON = "#F20D2E"
OBSIDIAN_BLACK = "#0B0B0B"
ACID_GREEN = "#3CF12B"
PURE_WHITE = "#FFFFFF"
ELECTRIC_BLUE = "#1E70F0"
NEON_VIOLET = "#9922EE"

_MENU_ARROW = (Path(__file__).resolve().parents[2] / "assets" / "menu_arrow.svg").as_posix()

CYBER_MENU_STYLE = f"""
QMenu {{
    background-color: {OBSIDIAN_BLACK};
    border: 1px solid {NEON_CRIMSON};
    padding: 6px 4px 6px 4px;
    color: {PURE_WHITE};
    font-family: {PIXEL_FONT};
    font-size: 11px;
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
        stop:0 rgba(242, 13, 46, 0.9),
        stop:0.65 rgba(242, 13, 46, 0.4),
        stop:1 rgba(11, 11, 11, 0.2));
    color: {PURE_WHITE};
    border-left: 2px solid {ACID_GREEN};
}}
QMenu::item:disabled {{
    color: rgba(153, 34, 238, 0.7);
    background: transparent;
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
    background: #07060b;
    color: #e7f9ea;
    font-family: {PIXEL_FONT};
    font-size: 13px;
}}
QVideoWidget {{
    background: #000;
    border: none;
    border-bottom: 3px solid #1c2a20;
}}
#panel {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #0d0a14, stop:0.49 #0d0a14,
        stop:0.5 #0a0810, stop:0.99 #0a0810,
        stop:1 #0d0a14);
    border-top: 3px solid #1a2a1f;
}}
#panel QLabel {{ background: transparent; }}
#accent {{
    border: none;
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #39ff6a, stop:0.19 #39ff6a,
        stop:0.2 #a259ff, stop:0.39 #a259ff,
        stop:0.4 #ff1e46, stop:0.59 #ff1e46,
        stop:0.6 #ffb000, stop:0.79 #ffb000,
        stop:0.8 #39ff6a, stop:1 #39ff6a);
}}
#prompt {{
    color: #39ff6a;
    font-weight: 700;
    font-size: 16px;
}}
#status {{
    color: #6f9479;
    font-size: 11px;
    letter-spacing: 2px;
}}
QLineEdit {{
    background: #0c0a12;
    border: 3px solid #2a2140;
    border-radius: 0;
    padding: 8px 10px;
    color: #eaffef;
    placeholder-text-color: #5f6b62;
    selection-background-color: #ff1e46;
    selection-color: #07060b;
}}
QLineEdit:focus {{
    border: 3px solid #39ff6a;
    background: #121019;
}}
QPushButton {{
    background: #39ff6a;
    color: #05070a;
    border: 3px solid #39ff6a;
    border-top-color: #a6ffbe;
    border-left-color: #a6ffbe;
    border-right-color: #0f8f33;
    border-bottom-color: #0f8f33;
    border-radius: 0;
    padding: 8px 20px;
    font-weight: 800;
    letter-spacing: 3px;
}}
QPushButton:hover {{
    background: #7dffa0;
    border-color: #7dffa0;
    border-top-color: #d2ffe0;
    border-left-color: #d2ffe0;
    border-right-color: #1fa94a;
    border-bottom-color: #1fa94a;
}}
QPushButton:pressed {{
    background: #12c744;
    border-color: #12c744;
    border-top-color: #0f8f33;
    border-left-color: #0f8f33;
    border-right-color: #a6ffbe;
    border-bottom-color: #a6ffbe;
    padding: 10px 20px 6px;
}}
QMenu {{
    background-color: #0d0a14;
    border: 2px solid #39ff6a;
    padding: 6px;
    color: #e7f9ea;
    font-family: {PIXEL_FONT};
    font-size: 11px;
}}
QMenu::item {{
    background: transparent;
    padding: 6px 28px 6px 20px;
    border: 1px solid transparent;
}}
QMenu::item:selected {{
    background-color: #1a1628;
    color: #39ff6a;
    border: 1px solid #39ff6a;
}}
QMenu::item:disabled {{
    color: #555268;
}}
QMenu::separator {{
    height: 2px;
    background: #2a2140;
    margin: 6px 2px;
}}
QMenu::indicator {{
    width: 12px;
    height: 12px;
}}
QMenu::indicator:checked {{
    background-color: #39ff6a;
    border: 1px solid #a6ffbe;
}}
QMenu::indicator:unchecked {{
    background-color: #0c0a12;
    border: 1px solid #4a3e6a;
}}
"""

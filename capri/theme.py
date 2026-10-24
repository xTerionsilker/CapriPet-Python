"""Shared pixel-art stylesheet for Capri's main interface.

The look is deliberately blocky: no rounded corners, chunky bevel borders,
hard-edged striped backgrounds and a pixel/monospace font stack. Install a
bitmap font such as "Press Start 2P" or "VT323" for the full effect; the
fallbacks keep the layout intact otherwise.
"""

PIXEL_FONT = (
    '"Press Start 2P", "Pixelify Sans", "VT323", "Terminus", '
    '"DejaVu Sans Mono", monospace'
)

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
    /* 4 px hard stripes read as a low-res dither pattern. */
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #0d0a14, stop:0.49 #0d0a14,
        stop:0.5 #0a0810, stop:0.99 #0a0810,
        stop:1 #0d0a14);
    border-top: 3px solid #1a2a1f;
}}
#panel QLabel {{ background: transparent; }}
#accent {{
    border: none;
    /* Stepped stops create a chunky, pixel-by-pixel rainbow. */
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
"""

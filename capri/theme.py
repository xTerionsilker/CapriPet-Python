"""Shared stylesheet for Capri's main interface."""

APP_STYLE = """
QWidget {
    background: #050408;
    color: #e7f9ea;
    font-family: "JetBrains Mono", "DejaVu Sans Mono", monospace;
    font-size: 13px;
}
QVideoWidget { background: #000; border: none; }
#accent {
    border: none;
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #39ff6a, stop:0.5 #a259ff, stop:1 #ff1e46);
}
#panel { background: #0b0a10; }
#panel QLabel { background: transparent; }
#prompt { color: #39ff6a; font-weight: 700; font-size: 16px; }
#status { color: #7f8f83; font-size: 12px; }
QLineEdit {
    background: #0f0e15;
    border: 1px solid #342a44;
    border-radius: 8px;
    padding: 9px 12px;
    color: #eaffef;
    placeholder-text-color: #5f6b62;
    selection-background-color: #ff1e46;
    selection-color: #050408;
}
QLineEdit:focus { border: 1px solid #39ff6a; background: #121019; }
QPushButton {
    background: #39ff6a;
    color: #05070a;
    border: none;
    border-radius: 8px;
    padding: 9px 22px;
    font-weight: 800;
    letter-spacing: 2px;
}
QPushButton:hover { background: #7dffa0; }
QPushButton:pressed { background: #12c744; }
"""

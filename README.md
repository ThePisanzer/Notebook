# Notebook

A lightweight note-taking app built with Python and CustomTkinter.

## Features

- SQLite storage (fast, safe, no file corruption)
- Permanent / temporary notes
- Import / Export (JSON, CSV)
- Keyboard-driven UI
- Dark theme

## Shortcuts

| Key | Action |
|-----|--------|
| Ctrl+N | New note |
| Enter | View |
| F2 | Edit |
| Del | Delete |
| Ctrl+O | Change folder |
| Ctrl+D | Clean temp notes |
| Ctrl+0~9 | Select note 1-10 |
| Ctrl+G | Goto note by ID |
| Ctrl+E | Export |
| Ctrl+I | Import |
| Esc | Exit |

## Requirements

- Python 3.10+
- customtkinter

## Install

pip install customtkinter

## Run

python "Notebook.py"

## Build exe

pyinstaller --onefile --noconsole --icon="icon.ico" --add-data "icon.ico;." --collect-all customtkinter "Notebook.py"

## License

MIT
# Mayhem Companion

A lightweight, unofficial League of Legends ARAM Mayhem companion for Windows.

Automatically detects your champion using the local League Client API and opens build and augment guides from Blitz and OP.GG.

## Features

- Automatically detects your selected champion.
- Waits until champion select finishes before opening guides.
- Opens guides in your default browser.
- Monitors League without requiring manual champion input.
- Lightweight Python application.

## Installation (Windows)

1. Go to the repository's **Releases** page.
2. Download `MayhemCompanion.exe` from the latest release.
3. Launch League of Legends.
4. Run `MayhemCompanion.exe` before entering champion select.
5. Play normally! The guide pages will open when your match starts.

Keep the application running to detect future games. Close the terminal to stop it.

## Running from source

Install Python and the dependencies:

```powershell
python -m pip install -r requirements.txt
python mayhem.py
```

## Notes

- League of Legends must be installed.
- The application uses the local League Client API and does not automate gameplay.
- Build-guide tabs must be closed manually.
- This is an unofficial community project and is not affiliated with or endorsed by Riot Games.

import json
import re
import time
from pathlib import Path
import sys

import requests
import urllib3
import webbrowser

from lcu import get_lcu_connection

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

POLL_INTERVAL = 2
APP_DIR = (
    Path(sys.executable).parent
    if getattr(sys, "frozen", False)
    else Path(__file__).parent
)

CACHE_FILE = APP_DIR / "champions.json"


def load_champions():
    """Map numerical champion IDs to champion names."""
    try:
        versions = requests.get(
            "https://ddragon.leagueoflegends.com/api/versions.json",
            timeout=10
        ).json()

        url = (
            "https://ddragon.leagueoflegends.com/cdn/"
            f"{versions[0]}/data/en_US/champion.json"
        )

        response = requests.get(url, timeout=10)
        response.raise_for_status()

        data = response.json()["data"]

        champions = {
            int(info["key"]): info["name"]
            for info in data.values()
        }

        CACHE_FILE.write_text(json.dumps(champions))
        return champions

    except (requests.RequestException, ValueError, KeyError, IndexError):
        if CACHE_FILE.exists():
            data = json.loads(CACHE_FILE.read_text())
            return {int(k): v for k, v in data.items()}

        raise RuntimeError("Could not load champion data.")


def get_league_state():
    """Read the current phase and selected champion."""
    port, token = get_lcu_connection()

    if not port or not token:
        return "Disconnected", None

    base_url = f"https://127.0.0.1:{port}"
    auth = ("riot", token)

    response = requests.get(
        f"{base_url}/lol-gameflow/v1/gameflow-phase",
        auth=auth,
        verify=False,
        timeout=5
    )
    response.raise_for_status()
    phase = response.json()

    champion_id = None

    if phase == "ChampSelect":
        response = requests.get(
            f"{base_url}/lol-champ-select/v1/session",
            auth=auth,
            verify=False,
            timeout=5
        )
        response.raise_for_status()

        session = response.json()
        my_cell = session.get("localPlayerCellId")

        player = next(
            (
                p for p in session.get("myTeam", [])
                if p.get("cellId") == my_cell
            ),
            None
        )

        if player:
            champion_id = player.get("championId")

    return phase, champion_id


def get_urls(champion):
    words = re.findall(r"[A-Za-z0-9]+", champion)

    blitz_name = "".join(w.capitalize() for w in words)
    opgg_name = "".join(w.lower() for w in words)

    # Add site-specific exceptions here if needed
    if champion == "Wukong":
        blitz_name = "Wukong"
        opgg_name = "wukong"

    if champion == "Nunu & Willump":
        blitz_name = "Nunu"
        opgg_name = "nunu"

    blitz_url = (
        f"https://blitz.gg/lol/champions/"
        f"{blitz_name}/aram-mayhem"
    )
    opgg_url = (
        f"https://op.gg/lol/modes/aram-mayhem/"
        f"{opgg_name}/augments"
    )

    return blitz_url, opgg_url



class BrowserManager:
    def __init__(self):
        self.opened_urls = set()

    def open_champion(self, champion):
        blitz_url, opgg_url = get_urls(champion)

        webbrowser.open_new_tab(blitz_url)
        webbrowser.open_new_tab(opgg_url)

        print(f"Opened pages for {champion}!")

    def close(self):
        pass



def main():
    print("Loading champion data...")
    champions = load_champions()
    print(f"Loaded {len(champions)} champions.")
    print("Monitoring League... Press Ctrl+C to quit.\n")

    browser = BrowserManager()

    previous_phase = None
    selected_champion = None
    pending_game = False
    opened_for_game = False

    try:
        while True:
            try:
                phase, champion_id = get_league_state()

            except requests.RequestException as error:
                print(f"Connection issue: {error}")
                time.sleep(POLL_INTERVAL)
                continue

            if phase != previous_phase:
                print(f"Game phase: {phase}")
                previous_phase = phase

            if phase == "ChampSelect":
                if not pending_game:
                    pending_game = True
                    opened_for_game = False
                    selected_champion = None

                if champion_id and champion_id != selected_champion:
                    selected_champion = champion_id
                    name = champions.get(champion_id, "Unknown")
                    print(f"Selected champion: {name}")

            elif phase in ("GameStart", "InProgress"):
                if pending_game and not opened_for_game:
                    if selected_champion:
                        name = champions.get(selected_champion)

                        if name:
                            print(f"Game starting! Champion: {name}")
                            try:
                                browser.open_champion(name)
                                opened_for_game = True
                            except Exception as error:
                                print(f"Browser error: {error}")
                                # Avoid repeatedly launching Chrome
                                opened_for_game = True

            elif phase in (
                "Lobby", "Matchmaking", "ReadyCheck", "None"
            ):
                # Reset if champion select was cancelled
                pending_game = False
                selected_champion = None
                opened_for_game = False

            time.sleep(POLL_INTERVAL)

    except KeyboardInterrupt:
        print("\nStopping Mayhem Companion...")

    finally:
        browser.close()


if __name__ == "__main__":
    main()

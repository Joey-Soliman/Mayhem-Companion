
import psutil
import requests
import urllib3
import time

# The League client uses a local HTTPS certificate.
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def get_lcu_connection():
    for proc in psutil.process_iter(["name", "cmdline"]):
        try:
            if proc.info["name"] != "LeagueClientUx.exe":
                continue

            args = proc.info["cmdline"] or []

            port = None
            token = None

            for arg in args:
                if arg.startswith("--app-port="):
                    port = arg.split("=", 1)[1]
                elif arg.startswith("--remoting-auth-token="):
                    token = arg.split("=", 1)[1]

            if port and token:
                return port, token

        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    return None, None


def test_connection():
    port, token = get_lcu_connection()

    if not port or not token:
        print("League Client not detected.")
        print("Make sure the League client is running.")
        return

    url = f"https://127.0.0.1:{port}/lol-gameflow/v1/gameflow-phase"

    try:
        response = requests.get(
            url,
            auth=("riot", token),
            verify=False,
            timeout=5
        )
        response.raise_for_status()

        print("Connected to League Client!")
        print("Current game phase:", response.json())

    except requests.RequestException as error:
        print("Connection failed:", error)



def test_champion_select():
    port, token = get_lcu_connection()

    if not port or not token:
        print("League Client not detected.")
        return

    base_url = f"https://127.0.0.1:{port}"
    auth = ("riot", token)

    try:
        # Find our summoner ID
        response = requests.get(
            f"{base_url}/lol-summoner/v1/current-summoner",
            auth=auth, verify=False, timeout=5
        )
        response.raise_for_status()
        summoner = response.json()
        summoner_id = summoner["summonerId"]

        # Get champion select information
        response = requests.get(
            f"{base_url}/lol-champ-select/v1/session",
            auth=auth, verify=False, timeout=5
        )
        response.raise_for_status()
        session = response.json()

        # Find our champion select slot
        my_cell = session["localPlayerCellId"]

        player = next(
            (p for p in session["myTeam"]
             if p["cellId"] == my_cell),
            None
        )

        print("Your champion ID:",
              player.get("championId") if player else None)

        # Inspect our champion-select actions
        for action_group in session.get("actions", []):
            for action in action_group:
                if action.get("actorCellId") == my_cell:
                    print(
                        "Action:",
                        action.get("type"),
                        "| Completed:",
                        action.get("completed"),
                        "| Champion ID:",
                        action.get("championId")
                    )

    except requests.RequestException as error:
        print("LCU request failed:", error)


def monitor_champion_select():
    print("Monitoring League champion select... (Ctrl+C to stop)")

    previous_state = None

    while True:
        port, token = get_lcu_connection()

        if not port or not token:
            state = ("Disconnected", None, None)
        else:
            base_url = f"https://127.0.0.1:{port}"
            auth = ("riot", token)

            try:
                phase_response = requests.get(
                    f"{base_url}/lol-gameflow/v1/gameflow-phase",
                    auth=auth, verify=False, timeout=5
                )
                phase_response.raise_for_status()
                phase = phase_response.json()

                champion_id = None
                completed = False

                if phase == "ChampSelect":
                    response = requests.get(
                        f"{base_url}/lol-champ-select/v1/session",
                        auth=auth, verify=False, timeout=5
                    )
                    response.raise_for_status()
                    session = response.json()

                    my_cell = session["localPlayerCellId"]
                    player = next(
                        (p for p in session.get("myTeam", [])
                         if p.get("cellId") == my_cell),
                        None
                    )

                    if player:
                        champion_id = player.get("championId")

                    for group in session.get("actions", []):
                        for action in group:
                            if (
                                action.get("actorCellId") == my_cell
                                and action.get("type") == "pick"
                                and action.get("completed")
                            ):
                                completed = True

                state = (phase, champion_id, completed)

            except requests.RequestException as error:
                print("LCU request failed:", error)
                time.sleep(2)
                continue

        if state != previous_state:
            print(
                f"Phase: {state[0]} | "
                f"Champion ID: {state[1]} | "
                f"Pick completed: {state[2]}"
            )
            previous_state = state

        time.sleep(2)


if __name__ == "__main__":
    try:
        monitor_champion_select()
    except KeyboardInterrupt:
        print("\nMonitoring stopped.")

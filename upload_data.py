import json
import math
from pathlib import Path

import gspread
from google.oauth2.service_account import Credentials


# ----------------- CONFIG -----------------
SERVICE_ACCOUNT_FILE = "service_account_credentials.json"
SPREADSHEET_NAME = "linkedinTest"
JSON_FILE = "results\\16-01-2026_084757.json"
target_date_str = "05-Jan"   # date that this JSON's data belongs to
# -----------------------------------------


def secs_to_m_ss(seconds: int | float) -> float:
    """
    Convert e.g. 94 -> 1.34 (1 minute 34 seconds).
    Returns a float that will look like M.SS in Sheets.
    """
    m = int(seconds // 60)
    s = int(seconds % 60)
    return float(f"{m}.{s:02d}")


def main():
    # Authorize
    # scopes = ["https://www.googleapis.com/auth/spreadsheets"]
    # creds = Credentials.from_service_account_file(
    #     SERVICE_ACCOUNT_FILE, scopes=scopes
    # )
    gc = gspread.service_account(filename=SERVICE_ACCOUNT_FILE)

    # Open spreadsheet
    sh = gc.open(SPREADSHEET_NAME)

    # Load JSON
    data = json.loads(Path(JSON_FILE).read_text())

    # For each game (sheet)
    for game_name, players in data.items():
        try:
            ws = sh.worksheet(game_name.capitalize())  # or exactly game_name
        except gspread.WorksheetNotFound:
            # if sheet names are lowercase, use game_name
            ws = sh.worksheet(game_name)

        # Find row for the given date (in column A)
        dates_col = ws.col_values(1)  # list including header (if any)
        try:
            row_index = dates_col.index(target_date_str) + 1
        except ValueError:
            print(f"Date {target_date_str} not found in sheet {game_name}")
            continue

        # Get header row to map player -> column
        headers = ws.row_values(1)  # row 1 has ANSP, SEM, ...
        header_to_col = {h: i + 1 for i, h in enumerate(headers) if h}

        # Insert each player's time
        for player_name, result in players.items():
            if result["time"] is None:
                continue

            # Map JSON player name to sheet column header if needed
            # Example: "Sebastian" -> "SEM"
            name_map = {
                "Sebastian": "SEM",
                "Mads": "MRMA",
                "Malaika Din": "MDIH",
                "Anders": "ANSP",
                "Søsser": "SOSS",
                # add others...
            }
            header_name = name_map.get(player_name, player_name)

            col_index = header_to_col.get(header_name)
            if not col_index:
                print(f"No column for player {player_name} in sheet {game_name}")
                continue

            value = secs_to_m_ss(result["time"])
            ws.update_cell(row_index, col_index, value)

        print(f"Updated sheet {game_name} for date {target_date_str}")


if __name__ == "__main__":
    main()

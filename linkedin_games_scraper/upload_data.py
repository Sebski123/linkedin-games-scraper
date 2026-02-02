import datetime
import json
from pathlib import Path
from .solver import logger

import gspread

# ----------------- CONFIG -----------------
SPREADSHEET_NAME = "LinkedIn_Leaderboard"
# -----------------------------------------

# Map JSON player name to sheet column header if needed
# Example: "Sebastian" -> "SEM"
NAME_MAP = {
    "Sebastian": "SEM",
    "Mads": "MRMA",
    "Malaika Din": "MDIH",
    "Anders": "ANSP",
    "Søsser": "SOSS",
    "Leon Philipson": "LPA",
    "Camilla": "CMFR"
    # add others...
}

ID_TO_SHEET_NAME = {
    "zip": "Zip",
    "queens": "Queens",
    "tango": "Tango",
    "pinpoint": "PinPoint",
    "crossclimb": "CrossClimb",
    "mini_sudoku": "Sudoku",
}


def secs_to_m_ss(seconds: int | float) -> float:
    """
    Convert e.g. 94 -> 1.34 (1 minute 34 seconds).
    Returns a float that will look like M.SS in Sheets.
    """
    m = int(seconds // 60)
    s = int(seconds % 60)
    return float(f"{m}.{s:02d}")


def main(file_json: str, credentials_file: str):
    gc = gspread.service_account(filename=credentials_file)

    # Open spreadsheet
    sh = gc.open(SPREADSHEET_NAME)

    # Load JSON
    data: dict[str, dict[str, dict[str, int | None]]] = json.loads(Path(file_json).read_text())

    # For each game (sheet)
    for game_name, players in data.items():
        try:
            ws = sh.worksheet(ID_TO_SHEET_NAME.get(game_name, game_name))
        except gspread.WorksheetNotFound:
            # if sheet names are lowercase, use game_name
            ws = sh.worksheet(game_name)

        # Find row for the given date (in column A)
        dates_col = ws.col_values(1)  # list including header (if any)
        # extract date from filename, assuming format 'DD-MM-YYYY_hhmmss.json'
        filename = Path(file_json).name
        date_part = filename.split("_")[0].split(".")[0]  # '17-01-2026'
        dt = datetime.datetime.strptime(date_part, "%d-%m-%Y")
        target_date_str = dt.strftime("%d-%b").lstrip("0")

        try:
            row_index = dates_col.index(target_date_str) + 1
        except ValueError:
            logger.info(f"Date {target_date_str} not found in sheet {game_name}")
            continue

        # Get header row to map player -> column
        headers = ws.row_values(1)  # row 1 has ANSP, SEM, ...
        header_to_col = {h: i + 1 for i, h in enumerate(headers) if h}

        # Insert each player's time
        for player_name, result in players.items():
            if (game_name == "pinpoint" and result["guessCount"] is None) or (game_name != "pinpoint" and result["time"] is None):
                continue

            header_name = NAME_MAP.get(player_name, player_name)

            col_index = header_to_col.get(header_name)
            if not col_index:
                # logger.info(f"No column for player {player_name} in sheet {game_name}")
                continue

            if game_name == "pinpoint":
                value = result["guessCount"]
            else:
                value = secs_to_m_ss(result["time"])

            ws.update_cell(row_index, col_index, value)

        logger.info(f"Updated sheet {game_name} for date {target_date_str}")


if __name__ == "__main__":
    main()

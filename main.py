from pathlib import Path
import json
from linkedin_games_scraper import GameSolver, logger
from linkedin_games_scraper.upload_data import main as upload_data_main

# Fetch data from LinkedIn
solver = GameSolver(headless=True, user="default")

try:
    solver.driver.get("https://www.linkedin.com/")
    solver.wait_for_page_load(timeout=30)

    csrf_token = solver.extract_csrf_token()

    leaderboard = {}

    for game_name in GameSolver.GAMES:
        for i in range(4):
          logger.info(f"Getting leaderboard for {game_name}...")
          solver.get_leaderboard_via_fetch(game_name, csrf_token)
          leaderboard_local = solver.find_leaderboard_data()
          if len(leaderboard_local) > 0:
              leaderboard[game_name] = leaderboard_local
              logger.info(f"Got {len(leaderboard_local)} entries for {game_name} leaderboard")
              break
          else:
              logger.info(f"Got 0 entries for {game_name} leaderboard, retrying")

    logger.info("\nLeaderboard Results:")
    logger.info(json.dumps(leaderboard, indent=2))
    solver.results = leaderboard
finally:
    results_file = solver.cleanup()

# results_file = "results\\17-01-2026_165859.json"
credentials_file = Path("service_account_credentials.json")
upload_data_main(results_file, str(credentials_file.absolute()))

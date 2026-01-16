"""Solver module."""

import json
import logging
import os
import time
from datetime import datetime

from selenium.webdriver.firefox.options import Options
from selenium.webdriver.support.wait import WebDriverWait
from seleniumwire import webdriver

# Set up logging
# First, disable all loggers
for name, _ in logging.Logger.manager.loggerDict:
    logging.getLogger(name).disabled = True

# Then set up our logger
logger = logging.getLogger(__name__)
logger.disabled = False
logger.setLevel(logging.INFO)

# Create console handler with formatting
console_handler = logging.StreamHandler()
console_handler.setFormatter(logging.Formatter(
    fmt="%(asctime)s - %(levelname)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S"))
logger.addHandler(console_handler)


class GameSolver:
    """GameSolver class."""

    # Game URLs
    GAMES = {
        "zip": {
            "url": "https://www.linkedin.com/games/zip", 
            "ID": 6, 
            "start_date": "2025-03-17"
        },
        "tango": {
            "url": "https://www.linkedin.com/games/tango", 
            "ID": 5, 
            "start_date": "2024-10-07"
        },
        "queens": {
            "url": "https://www.linkedin.com/games/queens", 
            "ID": 3, 
            "start_date": "2024-04-30"
        },
        "pinpoint": {
            "url": "https://www.linkedin.com/games/pinpoint", 
            "ID": 1, 
            "start_date": "2024-04-30"
        },
        "crossclimb": {
            "url": "https://www.linkedin.com/games/crossclimb", 
            "ID": 2, 
            "start_date": "2024-04-30"
        },
        "mini_sudoku": {
            "url": "https://www.linkedin.com/games/mini-sudoku", 
            "ID": 7, 
            "start_date": "2025-08-11"
        },
    }

    def __init__(self, headless=True, results_dir=None):
        """Initialise the GameSolver."""
        # Configure Selenium-wire to capture all requests
        self.seleniumwire_options = {
            "disable_encoding": True,
            "verify_ssl": False,
            # "proxy": {
            #     "http": "http://squid1.localdom.net:3128",
            #     "https": "http://squid1.localdom.net:3128"
            # },
        }

        firefox_options = Options()
        if headless:
            firefox_options.add_argument("--headless")

        firefox_options.add_argument("--disable-content-sandbox")

        firefox_options.add_argument("-profile")
        firefox_options.add_argument(
            "C:/Users/sem/AppData/Roaming/Mozilla/Firefox/Profiles/1k1o0g08.default-release-1/")

        # Initialise the driver
        self.driver = webdriver.Firefox(
            seleniumwire_options=self.seleniumwire_options, options=firefox_options)

        # Initialise results dictionary
        self.results = {"data": {}}

        # Create results directory if it doesn't exist
        self.results_dir = results_dir or "results"
        os.makedirs(self.results_dir, exist_ok=True)

    def extract_csrf_token(self):
        """Extract CSRF token from cookies."""
        for cookie in self.driver.get_cookies():
            if cookie['name'] == 'JSESSIONID':
                csrf_token = cookie['value'].strip('"')
                logger.info(f"Extracted CSRF token: {csrf_token}")
                return csrf_token
        logger.warning("CSRF token not found in cookies.")
        return None

    def wait_for_page_load(self, timeout=30):
        """Wait for the page to load completely."""
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                WebDriverWait(self.driver, 5).until(lambda d: d.execute_script(
                    "return document.readyState") == "complete")
                logger.info("Page loaded successfully")
                break
            except (TimeoutError, RuntimeError) as e:
                if time.time() - start_time >= timeout:
                    logger.error(
                        f"Page load timed out after {timeout} seconds")
                    return None
                else:
                    logger.info(f"Waiting for page load... ({str(e)})")
                time.sleep(1)
                continue

    def get_leaderboard_via_fetch(self, game, csrf_token):
        """Get the leaderboard for a game using fetch API."""
        # Clear existing requests
        del self.driver.requests

        url_start = "https://www.linkedin.com/voyager/api/graphql?includeWebMetadata=true&variables=(gameUrn:urn%3Ali%3Afsd_game%3A%28ACoAAB2OIy0BU3BCAj3aSGwYj-CXoaCWMMVl0s0%2C"
        url_end = "%29,start:0,count:15)&queryId=voyagerIdentityDashGameConnectionsEntities.370a22a07dce5feba0a603ed03e4c908"

        # Calculated days since game start
        start_date_str = self.GAMES[game]["start_date"]
        if not start_date_str:
            logger.error(f"Start date not found for game: {game}")
            return None
        start_date = datetime.strptime(start_date_str, "%Y-%m-%d")
        days_since_start = (datetime.now() - start_date).days

        # Use fetch API to get leaderboard data directly
        try:
            logger.info("Fetching leaderboard data via fetch API")
            fetch_script = f"""
            fetch('{url_start}{self.GAMES[game]["ID"]}%2C{days_since_start}{url_end}', {{
                headers: {{"csrf-token": "{csrf_token}"}},
            }});
            """
            self.driver.execute_script(fetch_script)
            # Wait for the request to complete
            time.sleep(1.5)

            logger.info("Successfully fetched leaderboard data")
        except (RuntimeError, ValueError, KeyError) as e:
            logger.error(f"Failed to fetch leaderboard data: {str(e)}")
            return None

    def find_leaderboard_data(self):
        """Find leaderboard data in requests."""
        leaderboard_data = {}
        filtered_requests = [request for request in self.driver.requests if ("voyager/api/graphql" in request.url and "voyagerIdentityDashGameConnectionsEntities" in request.url and (
            "c37afe5a2cada33789b5a636e62147ae" in request.url or "370a22a07dce5feba0a603ed03e4c908" in request.url))]
        for request in filtered_requests:
            if not request.response:
                continue

            try:
                body = request.response.body.decode("utf-8")
                data = json.loads(body)
                entries_temp = data.get("data", {})
                if "identityDashGameConnectionsEntitiesByOptedInToLeaderboardAndPlayed" in entries_temp:
                    entries = entries_temp.get(
                        "identityDashGameConnectionsEntitiesByOptedInToLeaderboardAndPlayed", {}).get("elements", [])
                else:
                    entries = entries_temp.get(
                        "identityDashGameConnectionsEntitiesByLeaderboardSnapshotV2", {}).get("elements", [])
                logger.info(
                    f"Found {len(entries)} leaderboard entries in response")

                for entry in entries:
                    player_name = entry.get("playerDetails").get(
                        "player").get("profile").get("firstName")
                    player_score = {
                        "time": entry.get("gameScore").get("timeElapsed"),
                        "guessCount": entry.get("gameScore").get("totalGuessCount"),
                        "flawless": entry.get("isFlawless"),
                    }
                    leaderboard_data[player_name] = player_score
                logger.info(
                    f"Extracted {len(leaderboard_data)} leaderboard entries")
            except (json.JSONDecodeError, KeyError, AttributeError, TypeError) as e:
                logger.error(f"Error parsing leaderboard response: {str(e)}")
        return leaderboard_data

    def save_results(self, filename=None):
        """Save results to a JSON file."""
        if not filename:
            filename = f"{self.results_dir}/{datetime.now().strftime('%d-%m-%Y_%H%M%S')}.json"
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(self.results, f, indent=2)
        logger.info(f"Results saved to {filename}")
        return filename

    def cleanup(self):
        """Close the browser and save results."""
        if self.driver:
            self.driver.quit()
        return self.save_results()

# Main function
def main():
    """Run the LinkedIn Games Solver."""
    solver = GameSolver(headless=True)

    try:
        # Solve all games
        solver.driver.get("https://www.linkedin.com/")
        solver.wait_for_page_load(timeout=30)
        csrf_token = solver.extract_csrf_token()

        # solver.get_leaderboard(solver.GAME_URLS["zip"], timeout_seconds=30)
        # solver.get_leaderboard(solver.GAME_URLS["tango"], timeout_seconds=30)

        leaderboard = {}

        for game_name, _ in GameSolver.GAMES:
            logger.info(f"Getting leaderboard for {game_name}...")
            solver.get_leaderboard_via_fetch(game_name, csrf_token)
            leaderboard_local = solver.find_leaderboard_data()
            leaderboard[game_name] = leaderboard_local
            print(
                f"Got {len(leaderboard_local)} entries for {game_name} leaderboard")

        print("\nLeaderboard Results:")
        print(leaderboard)
        solver.results = leaderboard
    finally:
        solver.cleanup()


if __name__ == "__main__":
    main()

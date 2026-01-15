"""Solver module."""

import json
import logging
import os
import time
from datetime import datetime

from selenium.webdriver.firefox.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions
from selenium.webdriver.support.ui import WebDriverWait
from seleniumwire import webdriver
from selenium.common.exceptions import NoSuchElementException

# Set up logging
# First, disable all loggers
for name in logging.Logger.manager.loggerDict.keys():
    logging.getLogger(name).disabled = True

# Then set up our logger
logger = logging.getLogger(__name__)
logger.disabled = False
logger.setLevel(logging.INFO)

# Create console handler with formatting
console_handler = logging.StreamHandler()
console_handler.setFormatter(logging.Formatter(fmt="%(asctime)s - %(levelname)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S"))
logger.addHandler(console_handler)


class GameSolver:
    """GameSolver class."""

    # Game URLs
    GAME_URLS = {
        "pinpoint": "https://www.linkedin.com/games/pinpoint",
        "crossclimb": "https://www.linkedin.com/games/crossclimb",
        "zip": "https://www.linkedin.com/games/zip",
        "queens": "https://www.linkedin.com/games/queens",
        "tango": "https://www.linkedin.com/games/tango",
        "mini_sudoku": "https://www.linkedin.com/games/mini-sudoku",
    }

    # Game type IDs
    GAME_TYPE_IDS = {
        "pinpoint": 1,
        "crossclimb": 2,
        "queens": 3,
        "tango": 5,
        "zip": 6,
        "mini_sudoku": 7,
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
        firefox_options.add_argument("C:/Users/sem/AppData/Roaming/Mozilla/Firefox/Profiles/1k1o0g08.default-release-1/")        

        # Initialise the driver
        self.driver = webdriver.Firefox(seleniumwire_options=self.seleniumwire_options, options=firefox_options)
        self.wait = WebDriverWait(self.driver, 30)

        # Initialise results dictionary
        self.results = {"data": {}}

        # Create results directory if it doesn't exist
        self.results_dir = results_dir or "results"
        os.makedirs(self.results_dir, exist_ok=True)
        
    def login(self, email, password):
        """Login to LinkedIn."""
        logger.info("Logging in to LinkedIn...")
        self.driver.get("https://www.linkedin.com/checkpoint/lg/sign-in-another-account")

        # wait for email input to be present
        email_input = self.wait.until(expected_conditions.presence_of_element_located((By.ID, "username")))
        email_input.send_keys(email)
        
        password_input = self.driver.find_element(By.ID, "password")
        password_input.send_keys(password)
        
        sign_in_button = self.driver.find_element(By.XPATH, "//button[@type='submit']")
        sign_in_button.click()
        
        # Wait for login to complete
        self.wait.until(expected_conditions.url_contains("linkedin.com/feed"))
        # Then wait a bit more to ensure all requests are captured
        time.sleep(5)
        logger.info("Logged in to LinkedIn successfully.")

    def extract_csrf_token(self):
        """Extract CSRF token from cookies."""
        for cookie in self.driver.get_cookies():
            if cookie['name'] == 'JSESSIONID':
                csrf_token = cookie['value'].strip('"')
                logger.info(f"Extracted CSRF token: {csrf_token}")
                return csrf_token
        logger.warning("CSRF token not found in cookies.")
        return None

    def _find_game_response(self, game_type_id):
        """Find game response in requests."""
        total_requests = 0
        matched_requests = 0
        for request in self.driver.requests:
            total_requests += 1
            if not request.response:
                continue

            url = request.url
            if (
                "voyager/api/graphql" in url
                and f"gameTypeId:{game_type_id}" in url
                and "voyagerIdentityDashGames" in url
                and "voyagerIdentityDashGamesPages" not in url
            ):
                matched_requests += 1
                logger.info(f"Found candidate GraphQL response for gameTypeId {game_type_id}: {url}")
                try:
                    body = request.response.body.decode("utf-8")
                    return json.loads(body)
                except Exception as e:
                    logger.error(f"Error parsing response: {str(e)}")
        if total_requests:
            logger.info(f"Scanned {total_requests} requests; matched {matched_requests} for gameTypeId {game_type_id}")
        else:
            logger.info("No network requests captured yet")
        return None

    def _find_pinpoint_solution(self):
        """Find the solution in the Pinpoint GraphQL response."""
        data = self._find_game_response(self.GAME_TYPE_IDS["pinpoint"])
        if data:
            try:
                solution = data["included"][0]["gamePuzzle"]["blueprintGamePuzzle"]["solutions"][0]
                logger.info(f"Pinpoint solution: {solution}")
                self.results["data"]["pinpoint"] = solution
                return solution
            except Exception as e:
                logger.error(f"Error extracting Pinpoint solution: {str(e)}")
        return None

    def _find_crossclimb_solution(self):
        """Find the solution in the CrossClimb GraphQL response."""
        data = self._find_game_response(self.GAME_TYPE_IDS["crossclimb"])
        if data:
            try:
                rungs = data["included"][0]["gamePuzzle"]["crossClimbGamePuzzle"]["rungs"]

                # Sort rungs by solutionRungIndex and format solution
                sorted_rungs = sorted(rungs, key=lambda x: x["solutionRungIndex"])
                solution = [(rung["solutionRungIndex"], rung["word"]) for rung in sorted_rungs]

                logger.info("CrossClimb solution:")
                for index, word in solution:
                    logger.info(f"Position {index}: {word}")

                self.results["data"]["crossclimb"] = solution
                return solution
            except Exception as e:
                logger.error(f"Error extracting CrossClimb solution: {str(e)}")
        return None

    def _find_zip_solution(self):
        """Find the solution in the Zip GraphQL response."""
        data = self._find_game_response(self.GAME_TYPE_IDS["zip"])
        if data:
            try:
                logger.info(f"Zip response keys: {list(data.keys()) if isinstance(data, dict) else type(data)}")
                sequence = data["included"][0]["gamePuzzle"]["trailGamePuzzle"]["orderedSequence"]
                solution = data["included"][0]["gamePuzzle"]["trailGamePuzzle"]["solution"]
                grid = data["included"][0]["gamePuzzle"]["trailGamePuzzle"]["gridSize"]

                logger.info("Zip solution sequence:")
                logger.info(f"Order: {sequence}")

                self.results["data"]["zip"] = solution
                self.results["data"]["zip_sequence"] = sequence
                self.results["data"]["zip_grid"] = grid

                return sequence
            except Exception as e:
                logger.error(f"Error extracting Zip solution: {str(e)}")
        return None

    def _find_queens_solution(self):
        """Find the solution in the Queens GraphQL response."""
        data = self._find_game_response(self.GAME_TYPE_IDS["queens"])
        if data:
            try:
                queens = data["included"][0]["gamePuzzle"]["queensGamePuzzle"]["solution"]
                board = data["included"][0]["gamePuzzle"]["queensGamePuzzle"]["colorGrid"]
                grid = data["included"][0]["gamePuzzle"]["queensGamePuzzle"]["gridSize"]

                logger.info("Queens solution coordinates:")
                solution = []
                for queen in queens:
                    row, col = queen["row"], queen["col"]
                    solution.append((row, col))
                    logger.info(f"Queen at row {row}, column {col}")
                board_setup = []
                for row in board:
                    board_setup.append(row["colors"])
                    logger.info(f"Row: {row['colors']}")

                self.results["data"]["queens"] = solution
                self.results["data"]["queens_board"] = board_setup
                self.results["data"]["queens_grid"] = grid
                return solution
            except Exception as e:
                logger.error(f"Error extracting Queens solution: {str(e)}")
        return None

    def _find_tango_solution(self):
        """Find the solution in the Tango GraphQL response."""
        data = self._find_game_response(self.GAME_TYPE_IDS["tango"])
        if data:
            try:
                solution_array = data["included"][0]["gamePuzzle"]["lotkaGamePuzzle"]["solution"]

                logger.info("Tango solution sequence:")
                solution = ""
                for item in solution_array:
                    if item == "ONE":
                        solution += "1"
                    else:
                        solution += "0"

                logger.info(f"Tango solution: {solution}")

                self.results["data"]["tango"] = solution
                return solution
            except Exception as e:
                logger.error(f"Error extracting Tango solution: {str(e)}")
        return None

    def _find_mini_sudoku_solution(self):
        """Find the solution in the Mini Sudoku GraphQL response."""
        logger.info("Starting Mini Sudoku solution extraction...")
        data = self._find_game_response(self.GAME_TYPE_IDS["mini_sudoku"])
        if data:
            logger.info("Found Mini Sudoku data, extracting solution...")
            try:
                mini_sudoku_puzzle = None
                if "included" in data and data["included"]:
                    for item in data["included"]:
                        game_puzzle = item.get("gamePuzzle")
                        if game_puzzle and game_puzzle.get("miniSudokuGamePuzzle"):
                            mini_sudoku_puzzle = game_puzzle["miniSudokuGamePuzzle"]
                            logger.info("Found Mini Sudoku puzzle in included item")
                            break

                    if not mini_sudoku_puzzle:
                        logger.error("No Mini Sudoku puzzle found in included array")
                        for i, item in enumerate(data["included"]):
                            logger.error(f"Included item {i} keys: {list(item.keys())}")
                            if "gamePuzzle" in item:
                                game_puzzle = item["gamePuzzle"]
                                logger.error(
                                    f"GamePuzzle types in item {i}: {[k for k in game_puzzle.keys() if game_puzzle[k] is not None]}"
                                )
                        return None
                else:
                    logger.error("No 'included' array found in response")
                    logger.error(f"Available keys: {list(data.keys())}")
                    return None

                solution = mini_sudoku_puzzle["solution"]
                grid_size = mini_sudoku_puzzle.get("gridRowSize", 6)
                preset_cells = mini_sudoku_puzzle.get("presetCellIdxes", [])
                title = mini_sudoku_puzzle.get("name", "Unknown")

                logger.info(f"Mini Sudoku solution for '{title}':")
                logger.info(f"Grid size: {grid_size}x{grid_size}")
                logger.info(f"Preset cells: {preset_cells}")
                logger.info(f"Solution: {solution}")

                for i in range(grid_size):
                    start_idx = i * grid_size
                    end_idx = start_idx + grid_size
                    row = solution[start_idx:end_idx]
                    logger.info(f"Row {i + 1}: {row}")

                self.results["data"]["mini_sudoku"] = {
                    "solution": solution,
                    "grid_size": grid_size,
                    "preset_cells": preset_cells,
                    "title": title,
                }
                return solution
            except Exception as e:
                logger.error(f"Error extracting Mini Sudoku solution: {str(e)}")
                logger.error(f"Response structure: {data.keys() if isinstance(data, dict) else 'Not a dict'}")
        else:
            logger.error("No Mini Sudoku data found")
        return None

    def wait_for_page_load(self, timeout=30):
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                WebDriverWait(self.driver, 5).until(lambda d: d.execute_script("return document.readyState") == "complete")
                logger.info("Page loaded successfully")
                break
            except Exception as e:
                if time.time() - start_time >= timeout:
                    logger.error(f"Page load timed out after {timeout} seconds")
                    return None
                else:
                    logger.info(f"Waiting for page load... ({str(e)})")
                time.sleep(1)
                continue
     
     
    GAME_START_DATES = {
        "pinpoint":     "2024-04-30",
        "crossclimb":   "2024-04-30",
        "zip":          "2025-03-17",
        "tango":        "2024-10-07",
        "queens":       "2024-04-30",
        "mini_sudoku":  "2025-08-11",
    }
    
    GAME_IDS = {
        "pinpoint":     "1",
        "crossclimb":   "2",
        "zip":          "6",
        "tango":        "5",
        "queens":       "3",
        "mini_sudoku":  "7",
    }
          
    def get_leaderboard_via_fetch(self, game, csrf_token):
        """Get the leaderboard for a game using fetch API."""
        # Clear existing requests
        del self.driver.requests
        
        url_start = "https://www.linkedin.com/voyager/api/graphql?includeWebMetadata=true&variables=(gameUrn:urn%3Ali%3Afsd_game%3A%28ACoAAB2OIy0BU3BCAj3aSGwYj-CXoaCWMMVl0s0%2C"
        url_end = "%29,start:0,count:15)&queryId=voyagerIdentityDashGameConnectionsEntities.370a22a07dce5feba0a603ed03e4c908"
        
        # Calculated days since game start
        start_date_str = self.GAME_START_DATES.get(game)
        if not start_date_str:
            logger.error(f"Start date not found for game: {game}")
            return None
        start_date = datetime.strptime(start_date_str, "%Y-%m-%d")
        days_since_start = (datetime.now() - start_date).days
        
        # Use fetch API to get leaderboard data directly
        try:
            logger.info("Fetching leaderboard data via fetch API")
            fetch_script = f"""
            fetch('{url_start}{self.GAME_IDS[game]}%2C{days_since_start}{url_end}', {{
                headers: {{"csrf-token": "{csrf_token}"}},
            }});
            """
            self.driver.execute_script(fetch_script)
            # Wait for the request to complete
            time.sleep(1.5)
            
            logger.info("Successfully fetched leaderboard data")
        except Exception as e:
            logger.error(f"Failed to fetch leaderboard data: {str(e)}")
            return None
    
    def get_leaderboard(self, game_url, timeout_seconds=30):
        """Get the leaderboard for a game."""
        # Clear existing requests
        del self.driver.requests

        # Navigate to game
        logger.info(f"Navigating to game URL: {game_url}")
        self.driver.get(game_url)
        
        # Wait for the page to load completely with a timeout
        self.wait_for_page_load(timeout=timeout_seconds)
        
        # Find "See results" button and click it
        try:
            logger.info("Looking for 'See results' button")
            results_button = WebDriverWait(self.driver, 10).until(
                expected_conditions.element_to_be_clickable((By.XPATH, "//*[@class='games-share-footer']/button"))
            )
            logger.info("Found 'See results' button, clicking")
            results_button.click()
            logger.info("Successfully clicked 'See results' button")           
        except Exception:
            try:
                logger.info("Trying second method to find 'See results' button")
                see_more_button = WebDriverWait(self.driver, 5).until(
                    expected_conditions.element_to_be_clickable((By.XPATH, "//span[span[contains(text(),'See results')]]"))
                )
                logger.info("Found 'See results' button, clicking")
                see_more_button.click()
                logger.info("Successfully clicked 'See results' button")
            except Exception as e2:
                logger.error(f"Failed to click 'See results' button: {str(e2)}")
                return None
        
        # Navigate to leaderboard tab
        self.driver.get(f"{game_url}/results/leaderboard/connections/")
        self.wait_for_page_load(timeout=timeout_seconds)
        
        # Check if "See more" button exists and click it if so
        try:
            logger.info("Looking for 'See more' button")
            see_more_button = WebDriverWait(self.driver, 10).until(
                expected_conditions.element_to_be_clickable((By.XPATH, "//*[contains(@aria-label,'See more')]"))
            )
            logger.info("Found 'See more' button, clicking")
            see_more_button.click()
            logger.info("Successfully clicked 'See more' button")
        except Exception as e:
            
            logger.info(f"No 'See more' button found or failed to click: {str(e)}") 
            
        # Wait for leaderboard data to load
        logger.info("Waiting briefly for leaderboard network requests to populate...")
        time.sleep(5)
        
        
    def find_leaderboard_data(self):
        """Find leaderboard data in requests."""
        leaderboard_data = {}
        filtered_requests = [request for request in self.driver.requests if ("voyager/api/graphql" in request.url and "voyagerIdentityDashGameConnectionsEntities" in request.url and ("c37afe5a2cada33789b5a636e62147ae" in request.url or "370a22a07dce5feba0a603ed03e4c908" in request.url))]
        for request in filtered_requests:
            if not request.response:
                continue

            try:
                body = request.response.body.decode("utf-8")
                data = json.loads(body)
                entries_temp = data.get("data", {})
                if "identityDashGameConnectionsEntitiesByOptedInToLeaderboardAndPlayed" in entries_temp:
                    entries = entries_temp.get("identityDashGameConnectionsEntitiesByOptedInToLeaderboardAndPlayed", {}).get("elements", [])
                else:
                    entries = entries_temp.get("identityDashGameConnectionsEntitiesByLeaderboardSnapshotV2", {}).get("elements", [])
                logger.info(f"Found {len(entries)} leaderboard entries in response")
                
                for entry in entries:
                    player_name = entry.get("playerDetails").get("player").get("profile").get("firstName") 
                    player_score = {
                        "time": entry.get("gameScore").get("timeElapsed"),
                        "guessCount": entry.get("gameScore").get("totalGuessCount"),
                        "flawless": entry.get("isFlawless"),
                    }
                    leaderboard_data[player_name] = player_score
                logger.info(f"Extracted {len(leaderboard_data)} leaderboard entries")
            except Exception as e:
                logger.error(f"Error parsing leaderboard response: {str(e)}")
        return leaderboard_data
       
    def _start_game(self, game_url, navigation_timeout=30):
        """Start a game and find its solution."""
        # Clear existing requests
        del self.driver.requests

        # Navigate to game
        logger.info(f"Navigating to game URL: {game_url}")
        self.driver.get(game_url)

        # Wait for the page to load completely with a timeout
        self.wait_for_page_load(timeout=navigation_timeout)

        # Wait for and switch to the iframe
        try:
            logger.info("Waiting for iframe to be present")
            iframe = WebDriverWait(self.driver, 10).until(
                expected_conditions.presence_of_element_located((By.CSS_SELECTOR, "iframe[title='games']"))
            )
            logger.info("Found iframe, switching to it")
            self.driver.switch_to.frame(iframe)
            logger.info("Successfully switched to iframe")
        except Exception as e:
            logger.error(f"Failed to switch to iframe: {str(e)}")
            return None

        # Find and click start button
        try:
            logger.info("Looking for start button")
            start_button = WebDriverWait(self.driver, 5).until(
                expected_conditions.element_to_be_clickable((By.ID, "launch-footer-start-button"))
            )
            logger.info("Found start button, clicking")
            start_button.click()
            logger.info("Successfully clicked start button")
        except Exception as e:
            logger.error(f"Failed to click start button: {str(e)}")
            # return None

        # Wait for game data to load
        logger.info("Waiting briefly for network requests to populate...")
        time.sleep(3)

    def solve_pinpoint(self, timeout_seconds: int = 30):
        """Solve the Pinpoint game."""
        logger.info("Solving Pinpoint...")
        self._start_game(self.GAME_URLS["pinpoint"], navigation_timeout=timeout_seconds)
        end_time = time.time() + timeout_seconds
        solution = None
        while time.time() < end_time and not solution:
            solution = self._find_pinpoint_solution()
            if solution:
                break
            logger.info("Waiting for Pinpoint solution...")
            time.sleep(1)

        if solution:
            logger.info("SUCCESS - Pinpoint solution found!")
        else:
            logger.warning("ERROR - No Pinpoint solution found (timeout)")

        return solution

    def solve_crossclimb(self, timeout_seconds: int = 30):
        """Solve the CrossClimb game."""
        logger.info("Solving CrossClimb...")
        self._start_game(self.GAME_URLS["crossclimb"], navigation_timeout=timeout_seconds)
        end_time = time.time() + timeout_seconds
        solution = None
        while time.time() < end_time and not solution:
            solution = self._find_crossclimb_solution()
            if solution:
                break
            logger.info("Waiting for CrossClimb solution...")
            time.sleep(1)

        if solution:
            logger.info("SUCCESS - CrossClimb solution found!")
        else:
            logger.warning("ERROR - No CrossClimb solution found (timeout)")

        return solution

    def solve_zip(self, timeout_seconds: int = 30):
        """Solve the Zip game."""
        logger.info("Solving Zip...")
        self._start_game(self.GAME_URLS["zip"], navigation_timeout=timeout_seconds)
        end_time = time.time() + timeout_seconds
        solution = None
        while time.time() < end_time and not solution:
            solution = self._find_zip_solution()
            if solution:
                break
            logger.info("Waiting for Zip solution...")
            time.sleep(1)

        if solution:
            logger.info("SUCCESS - Zip solution found!")
        else:
            logger.warning("ERROR - No Zip solution found (timeout)")

        return solution

    def solve_queens(self, timeout_seconds: int = 30):
        """Solve the Queens game."""
        logger.info("Solving Queens...")
        self._start_game(self.GAME_URLS["queens"], navigation_timeout=timeout_seconds)
        end_time = time.time() + timeout_seconds
        solution = None
        while time.time() < end_time and not solution:
            solution = self._find_queens_solution()
            if solution:
                break
            logger.info("Waiting for Queens solution...")
            time.sleep(1)

        if solution:
            logger.info("SUCCESS - Queens solution found!")
        else:
            logger.warning("ERROR - No Queens solution found (timeout)")

        return solution

    def solve_tango(self, timeout_seconds: int = 30):
        """Solve the Tango game."""
        logger.info("Solving Tango...")
        self._start_game(self.GAME_URLS["tango"], navigation_timeout=timeout_seconds)
        end_time = time.time() + timeout_seconds
        solution = None
        while time.time() < end_time and not solution:
            solution = self._find_tango_solution()
            if solution:
                break
            logger.info("Waiting for Tango solution...")
            time.sleep(1)

        if solution:
            logger.info("SUCCESS - Tango solution found!")
        else:
            logger.warning("ERROR - No Tango solution found (timeout)")

        return solution

    def solve_mini_sudoku(self, timeout_seconds: int = 30):
        """Solve the Mini Sudoku game."""
        logger.info("Solving Mini Sudoku...")
        self._start_game(self.GAME_URLS["mini_sudoku"], navigation_timeout=timeout_seconds)
        end_time = time.time() + timeout_seconds
        solution = None
        while time.time() < end_time and not solution:
            solution = self._find_mini_sudoku_solution()
            if solution:
                break
            logger.info("Waiting for Mini Sudoku solution...")
            time.sleep(1)

        if solution:
            logger.info("SUCCESS - Mini Sudoku solution found!")
        else:
            logger.warning("ERROR - No Mini Sudoku solution found (timeout)")

        return solution

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

    def solve_all_games(self):
        """Solve all LinkedIn games."""
        results = {}

        try:
            # Solve Pinpoint
            pinpoint_solution = self.solve_pinpoint()
            if pinpoint_solution:
                results["pinpoint"] = pinpoint_solution

            # Solve CrossClimb
            crossclimb_solution = self.solve_crossclimb()
            if crossclimb_solution:
                results["crossclimb"] = crossclimb_solution

            # Solve Zip
            zip_solution = self.solve_zip()
            if zip_solution:
                results["zip"] = zip_solution

            # Solve Queens
            queens_solution = self.solve_queens()
            if queens_solution:
                results["queens"] = queens_solution

            # Solve Tango
            tango_solution = self.solve_tango()
            if tango_solution:
                results["tango"] = tango_solution

            # Solve Mini Sudoku
            mini_sudoku_solution = self.solve_mini_sudoku()
            if mini_sudoku_solution:
                results["mini_sudoku"] = mini_sudoku_solution

        finally:
            self.cleanup()

        return results


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
        
        for game_name in GameSolver.GAME_URLS.keys():
            logger.info(f"Getting leaderboard for {game_name}...")
            solver.get_leaderboard_via_fetch(game_name, csrf_token)
            leaderboard_local = solver.find_leaderboard_data()
            leaderboard[game_name] = leaderboard_local
            print(f"Got {len(leaderboard_local)} entries for {game_name} leaderboard")
            
        print("\nLeaderboard Results:")
        print(leaderboard)
        solver.results = leaderboard
    finally:
        solver.cleanup()


if __name__ == "__main__":
    main()

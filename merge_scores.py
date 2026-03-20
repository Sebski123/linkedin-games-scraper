#!/usr/bin/env python3
"""
Merge individual player JSON files into date-based output files.

Usage:
    python merge_scores.py sem.json mads.json [more files...] -o results/
"""

import json
from pathlib import Path
from datetime import datetime
import argparse

# Import NAME_MAP from upload_data
from linkedin_games_scraper.upload_data import NAME_MAP

# Create reverse mapping: short code -> full name
CODE_TO_NAME = {v: k for k, v in NAME_MAP.items()}


def merge_json_files(input_files: list[str], output_dir: str = "results"):
    """
    Merge multiple player JSON files into date-based JSON files.

    Input format (e.g., sem.json):
        {
            "2026-03-09": {
                "zip": {
                    "Sebastian": {"time": 7, "guessCount": null, "flawless": true}
                }
            }
        }

    Output format (e.g., 09-03-2026.json):
        {
            "zip": {
                "Sebastian": {"time": 7, "guessCount": null, "flawless": true}
            }
        }

    Args:
        input_files: List of paths to JSON files (e.g., ["sem.json", "mads.json"])
        output_dir: Directory to write output files to
    """
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)

    # Dictionary to accumulate data by date
    # Structure: {date: {game: {player: {time, guessCount, flawless}}}}
    date_data = {}

    for file_path in input_files:
        path = Path(file_path)

        # Extract player code from filename (e.g., "sem" from "sem.json")
        player_code = path.stem.upper()

        # Look up full player name
        player_name = CODE_TO_NAME.get(player_code)
        if not player_name:
            print(
                f"Warning: No name mapping found for code '{player_code}' from file '{path.name}'")
            print(f"Available codes: {list(CODE_TO_NAME.keys())}")
            continue

        # Load the JSON file
        try:
            data = json.loads(path.read_text(encoding='utf-8'))
        except Exception as e:
            print(f"Error reading {path}: {e}")
            continue

        print(f"Processing {path.name} for player '{player_name}'...")

        # Process each date in the file
        for date_str, games in data.items():
            # Ensure date is in date_data
            if date_str not in date_data:
                date_data[date_str] = {}

            # Process each game
            for game_name, players in games.items():
                # Ensure game is in date_data[date_str]
                if game_name not in date_data[date_str]:
                    date_data[date_str][game_name] = {}

                # Extract only this player's data
                if player_name in players:
                    date_data[date_str][game_name][player_name] = players[player_name]

    # Write output files, one per date
    for date_str, games in date_data.items():
        output_file = output_path / date_str
        output_file = output_file.with_suffix(".json")
        # Write the JSON file
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(games, f, indent=2, ensure_ascii=False)

        print(f"Created {output_file} with {len(games)} games")


def main():
    parser = argparse.ArgumentParser(
        description="Merge player JSON files into date-based files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python merge_scores.py sem.json mads.json
    python merge_scores.py results/sem.json results/mads.json -o merged/
        """
    )
    parser.add_argument("files", nargs="+", help="Input JSON files to merge")
    parser.add_argument("--output-dir", "-o", default="results",
                        help="Output directory (default: results)")

    args = parser.parse_args()

    merge_json_files(args.files, args.output_dir)
    print("\nMerge complete!")


if __name__ == "__main__":
    main()

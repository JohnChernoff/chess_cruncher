
import chess.pgn
import json
from pathlib import Path
import chess.engine

from config import *
from analyzer import analyze_game
from blunder_analysis import analyze_blunders

def analyze_collection():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    pgn_files = sorted(INPUT_DIR.glob("*.pgn"))

    if not pgn_files:
        print(f"No PGN files found in {INPUT_DIR}")
        return

    engine = chess.engine.SimpleEngine.popen_uci(STOCKFISH_PATH)

    engine.configure({
        "Threads": ENGINE_THREADS,
        "Hash": ENGINE_HASH_MB,
    })

    total_games = 0
    successful_games = 0
    failed_games = 0

    try:
        for pgn_path in pgn_files:
            print(f"\nReading {pgn_path.name}")

            games = []

            with open(pgn_path, encoding="utf-8-sig") as pgn_file:
                game_number = 0

                while True:
                    game = chess.pgn.read_game(pgn_file)

                    if game is None:
                        break

                    print(f"    PGN length: {game.end().ply()} plies")

                    game_number += 1
                    total_games += 1

                    white = game.headers.get("White", "White")
                    black = game.headers.get("Black", "Black")

                    try:
                        print(
                            f"  Game {game_number}: "
                            f"{white} vs {black}",
                            end=" ... ",
                            flush=True,
                        )

                        analysis = analyze_game(
                            engine,
                            game,
                            ANALYSIS_DEPTH,
                            MAX_PLIES,
                        )

                        analysis["positions"] = analyze_blunders(analysis["positions"])

                        result = {
                            "event": game.headers.get("Event", ""),
                            "round": game.headers.get("Round", str(game_number)),
                            "white": white,
                            "black": black,
                            "result": game.headers.get("Result", "*"),
                            "date": game.headers.get("Date", ""),
                            "source": pgn_path.name,
                            "analyzedPlies": analysis["analyzedPlies"],
                            "positions": analysis["positions"],
                            "analysisSettings": {"depth": ANALYSIS_DEPTH, "shallowDepth": SHALLOW_DEPTH}
                        }

                        games.append(result)

                        successful_games += 1
                        print(f"OK ({len(analysis['positions'])} positions)")

                    except Exception as e:
                        failed_games += 1
                        print(f"FAILED: {e}")

            # Write one JSON file containing all successfully analyzed games.
            output_path = OUTPUT_DIR / f"{pgn_path.stem}.xpgn.json"

            collection = {
                "format": "XPGN",
                "version": 1,
                "source": pgn_path.name,
                "gameCount": len(games),
                "games": games,
            }

            with open(output_path, "w", encoding="utf-8") as out:
                json.dump(collection, out)

            print(f"  Wrote {len(games)} games to {output_path}")

    finally:
        engine.quit()

    print("\nCollection analysis complete")
    print(f"PGN files:       {len(pgn_files)}")
    print(f"Games found:     {total_games}")
    print(f"Successful:      {successful_games}")
    print(f"Failed:          {failed_games}")
    print(f"Output folder:   {OUTPUT_DIR}")


if __name__ == "__main__":
    analyze_collection()

import json

import chess.engine
import chess.pgn

from config import (
    ANALYSIS_DEPTH, SHALLOW_DEPTH, MATE_SCORE, FORMAT_VERSION,
    ENGINE_THREADS, ENGINE_HASH_MB, STOCKFISH_PATH,
    INPUT_DIR, OUTPUT_DIR, GAME_LIMIT, MAX_PLIES,
)
from analyzer import analyze_game


def analyze_collection(engine_path=STOCKFISH_PATH):
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    pgn_files = sorted(INPUT_DIR.glob("*.pgn"))
    if not pgn_files:
        print(f"No PGN files found in {INPUT_DIR}")
        return

    engine = chess.engine.SimpleEngine.popen_uci(str(engine_path))
    engine.configure({"Threads": ENGINE_THREADS, "Hash": ENGINE_HASH_MB})

    engine_info = {
        "name": engine.id.get("name", "unknown"),
        "depth": ANALYSIS_DEPTH,
        "shallowDepth": SHALLOW_DEPTH,
        "mateScore": MATE_SCORE,
    }

    total = ok = failed = 0

    try:
        for pgn_path in pgn_files:
            print(f"\nReading {pgn_path.name}")
            games = []

            with open(pgn_path, encoding="utf-8-sig") as f:
                number = 0
                while True:
                    game = chess.pgn.read_game(f)
                    if game is None:
                        break
                    if GAME_LIMIT is not None and number >= GAME_LIMIT:
                        break

                    number += 1
                    total += 1
                    white = game.headers.get("White", "White")
                    black = game.headers.get("Black", "Black")
                    print(f"  Game {number}: {white} vs {black}", end=" ... ", flush=True)

                    try:
                        games.append(analyze_game(engine, game, MAX_PLIES))
                        ok += 1
                        print(f"OK ({len(games[-1]['plies']) - 1} plies)")
                    except Exception as e:
                        failed += 1
                        print(f"FAILED: {e}")

            collection = {
                "format": "XPGN",
                "version": FORMAT_VERSION,
                "source": pgn_path.name,
                "engine": engine_info,
                "gameCount": len(games),
                "games": games,
            }

            out_path = OUTPUT_DIR / f"{pgn_path.stem}.xpgn.json"
            with open(out_path, "w", encoding="utf-8") as out:
                json.dump(collection, out, separators=(",", ":"))

            print(f"  Wrote {len(games)} games to {out_path}")
    finally:
        engine.quit()

    print(f"\nGames found: {total}   Successful: {ok}   Failed: {failed}")


if __name__ == "__main__":
    analyze_collection()

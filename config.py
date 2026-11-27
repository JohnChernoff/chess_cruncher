from pathlib import Path

PROJECT_DIR = Path(__file__).parent
INPUT_DIR = PROJECT_DIR / "input"
OUTPUT_DIR = PROJECT_DIR / "output"
STOCKFISH_PATH = PROJECT_DIR / "engine" / "stockfish.exe"

ENGINE_THREADS = 4
ENGINE_HASH_MB = 256

# Deep search used for evaluations and for judging the played move.
ANALYSIS_DEPTH = 8
# Shallow search; how much it disagrees with the deep one is a proxy for
# tactical complexity.
SHALLOW_DEPTH = 2

# Mate in n is stored as +/-(MATE_SCORE - n) centipawns. Written into the
# file so the Dart reader always agrees with whatever was used here.
MATE_SCORE = 10000

FORMAT_VERSION = 2

# Set to an int to analyze only the first N games of each file; None = all.
GAME_LIMIT = None
# Set to an int to stop each game after N plies; None = the whole game.
MAX_PLIES = None

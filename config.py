from pathlib import Path

PROJECT_DIR = Path(__file__).parent
INPUT_DIR = Path("input")

PGN_FILE = PROJECT_DIR / "input" / "wc.pgn"
OUTPUT_DIR = PROJECT_DIR / "output"
STOCKFISH_PATH = PROJECT_DIR / "engine" / "stockfish.exe"

ENGINE_THREADS = 4
ENGINE_HASH_MB = 256

ANALYSIS_DEPTH = 8
SHALLOW_DEPTH = 2

INACCURACY_THRESHOLD = 50
MISTAKE_THRESHOLD = 100
BLUNDER_THRESHOLD = 250

BLUNDER_WINDOW_PLIES = 8

TEST_GAME_INDEX = 0

STORE_PV = False
PV_LENGTH = 8

# Set to None to analyze the entire game.
MAX_PLIES = None
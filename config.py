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

MATE_SCORE = 10000   # mate in n scores as ±(MATE_SCORE - n)
CP_CLAMP = 1000      # stored/graphed centipawns are clamped to ±this

# Move-quality thresholds: mover's loss in win percentage points (0-100 scale).
INACCURACY_WIN = 5
MISTAKE_WIN = 10
BLUNDER_WIN = 15
BLUNDER_WINDOW_PLIES = 8

TEST_GAME_INDEX = 0

STORE_PV = False
PV_LENGTH = 8

# Set to None to analyze the entire game.
MAX_PLIES = None
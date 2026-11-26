import chess
import math


# Material values in centipawns
PIECE_VALUES = {
    chess.PAWN: 100,
    chess.KNIGHT: 320,
    chess.BISHOP: 330,
    chess.ROOK: 500,
    chess.QUEEN: 900,
    chess.KING: 0,
}

# Initial non-pawn material (both sides)
INITIAL_NON_PAWN_MATERIAL = 2 * (
        2 * PIECE_VALUES[chess.KNIGHT]
        + 2 * PIECE_VALUES[chess.BISHOP]
        + 2 * PIECE_VALUES[chess.ROOK]
        + PIECE_VALUES[chess.QUEEN]
)

PIECE_NAMES = {
    chess.QUEEN: "queen",
    chess.ROOK: "rook",
    chess.BISHOP: "bishop",
    chess.KNIGHT: "knight",
    chess.PAWN: "pawn",
}


def count_pieces(board, color):
    """
    Return piece counts for one side.
    """

    counts = {}

    for piece_type, name in PIECE_NAMES.items():
        counts[name] = len(board.pieces(piece_type, color))

    return counts


def material_value(counts):
    """
    Calculate material value in centipawns.
    """

    total = 0

    for piece_type, name in PIECE_NAMES.items():
        total += counts[name] * PIECE_VALUES[piece_type]

    return total


def material_balance(white, black):
    """
    Positive = White has more material.
    Negative = Black has more material.
    """

    return material_value(white) - material_value(black)


def composition_distance(white, black):
    """
    Measure difference in material composition.

    A pawn-for-pawn exchange produces no imbalance.
    A rook-for-two-minor-pieces produces a significant imbalance.

    Raw value = Manhattan distance between piece-count vectors.
    """

    difference = {}

    total = 0

    for name in PIECE_NAMES.values():
        d = white[name] - black[name]
        difference[name] = d
        total += abs(d)

    # Normalize to approximately 0..1
    normalized = total / 16.0

    return {
        "raw": total,
        "normalized": normalized,
        "difference": difference,
    }


def material_phase(board):
    """
    Remaining non-pawn material relative to the starting position.

    1.0 = starting material
    0.0 = no non-pawn material remaining
    """

    white = count_pieces(board, chess.WHITE)
    black = count_pieces(board, chess.BLACK)

    remaining = (
            white["queen"] * PIECE_VALUES[chess.QUEEN]
            + black["queen"] * PIECE_VALUES[chess.QUEEN]
            + white["rook"] * PIECE_VALUES[chess.ROOK]
            + black["rook"] * PIECE_VALUES[chess.ROOK]
            + white["bishop"] * PIECE_VALUES[chess.BISHOP]
            + black["bishop"] * PIECE_VALUES[chess.BISHOP]
            + white["knight"] * PIECE_VALUES[chess.KNIGHT]
            + black["knight"] * PIECE_VALUES[chess.KNIGHT]
    )

    return remaining / INITIAL_NON_PAWN_MATERIAL


def analyze_material(board, stockfish_cp=None):
    """
    Analyze material in a chess position.

    stockfish_cp:
        Stockfish evaluation in centipawns from White's perspective.

    If supplied, calculate the discrepancy between conventional
    material evaluation and Stockfish's evaluation.
    """

    white = count_pieces(board, chess.WHITE)
    black = count_pieces(board, chess.BLACK)

    balance = material_balance(white, black)

    composition = composition_distance(white, black)

    result = {
        "white": white,
        "black": black,

        "balanceCp": balance,

        "compositionDistance": composition,

        "phase": material_phase(board),
    }

    if stockfish_cp is not None:

        discrepancy = stockfish_cp - balance

        normalized = 1.0 - math.exp(
            -abs(discrepancy) / 400.0
        )

        result["discrepancyCp"] = discrepancy
        result["discrepancyNormalized"] = normalized

    return result

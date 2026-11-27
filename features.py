"""Raw, engine-free position measurements.

Nothing here is interpreted: weights, thresholds and normalisation all live
in the Dart reader so they can be tuned without re-running the analysis.
"""

import chess

# Order of every five-element array in the output file.
PIECE_ORDER = (chess.QUEEN, chess.ROOK, chess.BISHOP, chess.KNIGHT, chess.PAWN)


def piece_counts(board, color):
    """[queens, rooks, bishops, knights, pawns] for one side."""
    return [len(board.pieces(pt, color)) for pt in PIECE_ORDER]


def king_features(board, color):
    """Raw king-exposure facts for one side (None if there is no king)."""
    king_sq = board.king(color)
    if king_sq is None:
        return None

    kf = chess.square_file(king_sq)
    kr = chess.square_rank(king_sq)
    forward = 1 if color == chess.WHITE else -1

    # The king's file and its neighbours.
    files = [f for f in range(kf - 1, kf + 2) if 0 <= f <= 7]

    pawns = board.pieces(chess.PAWN, color)

    # Friendly pawns directly in front of the king.
    shield = 0
    shield_rank = kr + forward
    if 0 <= shield_rank <= 7:
        shield = sum(1 for f in files if chess.square(f, shield_rank) in pawns)

    # Files (of those three) with no friendly pawn anywhere.
    pawn_files = {chess.square_file(s) for s in pawns}
    open_files = sum(1 for f in files if f not in pawn_files)

    # Enemy pieces within two squares, by type. Kings are excluded: a king
    # approaching the other king in an endgame is not an attack.
    near = [0] * len(PIECE_ORDER)
    for sq, piece in board.piece_map().items():
        if piece.color == color or piece.piece_type == chess.KING:
            continue
        dist = max(abs(chess.square_file(sq) - kf), abs(chess.square_rank(sq) - kr))
        if dist <= 2:
            near[PIECE_ORDER.index(piece.piece_type)] += 1

    return {
        "rank": kr + 1 if color == chess.WHITE else 8 - kr,  # from the king's own side
        "shield": shield,
        "open": open_files,
        "near": near,
    }

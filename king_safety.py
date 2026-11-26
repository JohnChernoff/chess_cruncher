
import chess


def analyze_king(board, color):
    king_square = board.king(color)

    if king_square is None:
        return {
            "kingRank": None,
            "shieldPawns": None,
            "openAdjacentFiles": None,
            "enemyPiecesNear": None,
            "inCheck": False,
        }

    king_file = chess.square_file(king_square)
    king_rank = chess.square_rank(king_square)

    # Direction toward the opponent's side.
    forward = 1 if color == chess.WHITE else -1

    # The king's file and its two neighboring files.
    adjacent_files = [
        f for f in range(king_file - 1, king_file + 2)
        if 0 <= f <= 7
    ]

    friendly_pawns = board.pieces(chess.PAWN, color)

    # Friendly pawns immediately in front of the king.
    shield_rank = king_rank + forward
    shield_pawns = 0

    if 0 <= shield_rank <= 7:
        for file in adjacent_files:
            square = chess.square(file, shield_rank)
            if square in friendly_pawns:
                shield_pawns += 1

    # Files with no friendly pawn anywhere on them.
    open_files = 0

    for file in adjacent_files:
        has_pawn = any(
            chess.square_file(square) == file
            for square in friendly_pawns
        )
        if not has_pawn:
            open_files += 1

    # Count enemy pieces within two squares (Chebyshev distance).
    enemy_pieces_near = 0

    for square, piece in board.piece_map().items():
        if piece.color == color:
            continue

        file_distance = abs(
            chess.square_file(square) - king_file
        )
        rank_distance = abs(
            chess.square_rank(square) - king_rank
        )

        if max(file_distance, rank_distance) <= 2:
            enemy_pieces_near += 1

    # Only the side to move can legally be in check.
    in_check = (
            board.turn == color and board.is_check()
    )

    # Rank measured from the king's own perspective.
    king_rank_relative = (
        king_rank + 1
        if color == chess.WHITE
        else 8 - king_rank
    )

    return {
        "kingRank": king_rank_relative,
        "shieldPawns": shield_pawns,
        "openAdjacentFiles": open_files,
        "enemyPiecesNear": enemy_pieces_near,
        "inCheck": in_check,
    }


def analyze_king_safety(board):
    return {
        "white": analyze_king(board, chess.WHITE),
        "black": analyze_king(board, chess.BLACK),
    }

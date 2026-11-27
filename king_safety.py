
import chess
from material import material_phase

# Kings are deliberately absent: a king approaching the other king in an
# endgame is not an attack.
ATTACKER_WEIGHT = {
    chess.QUEEN: 4,
    chess.ROOK: 3,
    chess.BISHOP: 2,
    chess.KNIGHT: 2,
    chess.PAWN: 1,
}

def analyze_king(board, color, phase):
    king_square = board.king(color)

    if king_square is None:
        return {
            "kingRank": None, "shieldPawns": None, "openAdjacentFiles": None,
            "enemyPiecesNear": None, "attackWeight": None, "dangerScore": None,
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
    attack_weight = 0

    for square, piece in board.piece_map().items():
        if piece.color == color:
            continue

        weight = ATTACKER_WEIGHT.get(piece.piece_type, 0)
        if weight == 0:
            continue

        file_distance = abs(chess.square_file(square) - king_file)
        rank_distance = abs(chess.square_rank(square) - king_rank)

        if max(file_distance, rank_distance) <= 2:
            enemy_pieces_near += 1
            attack_weight += weight

    # About 10 weight units (queen + rook + minor) saturates. Endgame kings
    # keep a floor of 0.3 so queen endings can still feel dangerous.
    danger = min(1.0, attack_weight / 10.0) * (0.3 + 0.7 * phase)

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
        "attackWeight": attack_weight,
        "dangerScore": danger,
        "inCheck": in_check,
    }


def analyze_king_safety(board):
    phase = material_phase(board)
    return {
        "white": analyze_king(board, chess.WHITE, phase),
        "black": analyze_king(board, chess.BLACK, phase),
    }

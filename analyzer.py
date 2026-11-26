
import chess
import chess.engine
import math

from king_safety import analyze_king_safety
from config import STORE_PV, PV_LENGTH, SHALLOW_DEPTH, ANALYSIS_DEPTH
from material import analyze_material


def win_percent(cp):
    """
    Lichess-style win percentage approximation.

    Always represents White's expected result.
    This is not a literal probability of winning,
    since it does not separately model draws.
    """
    return 100.0 / (1.0 + math.exp(-0.00368208 * cp))


def pv_to_san(board, pv):
    """Convert a principal variation into SAN notation."""
    temp = board.copy()
    moves = []

    for move in pv:
        moves.append(temp.san(move))
        temp.push(move)

    return moves


def evaluate_position(engine, board, depth):
    """Evaluate one position using Stockfish."""

    info = engine.analyse(
        board,
        chess.engine.Limit(depth=depth)
    )

    score = info["score"].pov(chess.WHITE)

    mate = score.mate()
    cp = score.score(mate_score=100000)

    pv = info.get("pv", [])
    best_move = pv[0] if pv else None

    best_move_uci = best_move.uci() if best_move else None
    best_move_san = board.san(best_move) if best_move else None

    result = {
        "cp": cp,
        "winPercent": win_percent(cp),
        "mate": mate,
        "bestMoveUci": best_move_uci,
        "bestMoveSan": best_move_san,
    }

    if STORE_PV:
        short_pv = pv[:PV_LENGTH]

        result["pvUci"] = [
            move.uci() for move in short_pv
        ]
        result["pvSan"] = pv_to_san(board, short_pv)

    return result



def evaluate_depth_gap(engine, board, deep_cp, deep_mate,
                       deep_best_move_uci):
    """Compare shallow and deep searches, including move quality."""

    info = engine.analyse(
        board,
        chess.engine.Limit(depth=SHALLOW_DEPTH)
    )

    shallow_score = info["score"].pov(chess.WHITE)
    shallow_mate = shallow_score.mate()
    shallow_cp = shallow_score.score(mate_score=100000)

    # Shallow search's preferred move.
    pv = info.get("pv", [])
    shallow_move = pv[0] if pv else None

    # Deep search's preferred move, obtained from the earlier search.
    deep_move = (
        chess.Move.from_uci(deep_best_move_uci)
        if deep_best_move_uci else None
    )

    result = {
        "shallowCp": shallow_cp,
        "shallowMate": shallow_mate,
        "shallowBestMoveUci": (
            shallow_move.uci() if shallow_move else None
        ),
        "shallowBestMoveSan": (
            board.san(shallow_move) if shallow_move else None
        ),
        "deepBestMoveUci": (
            deep_move.uci() if deep_move else None
        ),
        "deepBestMoveSan": (
            board.san(deep_move) if deep_move else None
        ),
        "bestMoveChanged": (
            shallow_move != deep_move
            if shallow_move and deep_move else None
        ),
        "depthShiftCp": None,
        "depthGapCp": None,
        "shallowMoveRegretCp": None,
    }

    # Evaluation gap.
    if deep_mate is None and shallow_mate is None:
        shift = deep_cp - shallow_cp
        result["depthShiftCp"] = shift
        result["depthGapCp"] = abs(shift)

    # If both searches recommend the same move, its regret is zero.
    if shallow_move and deep_move:
        if shallow_move == deep_move:
            result["shallowMoveRegretCp"] = 0
        else:
            # Evaluate the shallow recommendation at deep depth.
            restricted_info = engine.analyse(
                board,
                chess.engine.Limit(depth=ANALYSIS_DEPTH),
                root_moves=[shallow_move]
            )

            deep_best_mover_cp = deep_cp if board.turn == chess.WHITE else -deep_cp

            shallow_move_score = restricted_info["score"].pov(board.turn)
            shallow_move_cp = shallow_move_score.score(
                mate_score=100000
            )

            result["shallowMoveRegretCp"] = (
                max(0, deep_best_mover_cp - shallow_move_cp)
                if shallow_move_cp is not None
                else None
            )

    return result



def analyze_game(engine, game, depth, max_plies=None):
    """
    Analyze a game position by position.

    Position zero is the initial position.
    Every subsequent position follows one half-move.
    """

    board = game.board()
    positions = []

    previous_cp = None
    previous_mate = None
    ply = 0

    def record_position(move_data=None):
        nonlocal previous_cp, previous_mate

        evaluation = evaluate_position(
            engine,
            board,
            depth
        )

        material = analyze_material(
            board,
            evaluation["cp"]
            if evaluation["mate"] is None
            else None
        )

        depth_analysis = evaluate_depth_gap(
            engine,
            board,
            evaluation["cp"],
            evaluation["mate"],
            evaluation["bestMoveUci"],
        )

        current_cp = evaluation["cp"]
        current_mate = evaluation["mate"]

        position = {
            "ply": ply,
            "fen": board.fen(),
            "evaluation": evaluation,
            "material": material,
            "kingSafety": analyze_king_safety(board),
            "depthAnalysis": depth_analysis,
        }

        if move_data is not None:
            position["move"] = move_data

            # Only compare ordinary evaluations.
            # Mate-score transitions are not meaningful
            # as centipawn changes.
            if current_mate is None and previous_mate is None:

                position["evalChangeCp"] = (
                        current_cp - previous_cp
                )

                if move_data["side"] == "white":
                    loss = previous_cp - current_cp
                else:
                    loss = current_cp - previous_cp

                position["moverEvalLossCp"] = loss

        positions.append(position)

        previous_cp = current_cp
        previous_mate = current_mate

    # Analyze the starting position.
    record_position()

    # Analyze each subsequent position.
    for move in game.mainline_moves():

        if max_plies is not None and ply >= max_plies:
            break

        san = board.san(move)
        uci = move.uci()

        side = (
            "white" if board.turn == chess.WHITE
            else "black"
        )

        regret = evaluate_move_regret(
            engine, board, move, depth
        )

        board.push(move)
        ply += 1

        record_position({
            "side": side,
            "san": san,
            "uci": uci,
            **regret,
        })

    return {
        "headers": dict(game.headers),
        "analyzedPlies": ply,
        "positions": positions,
    }

def evaluate_move_regret(engine, board, move, depth):
    """Compare a played move with Stockfish's best move."""

    mover = board.turn
    limit = chess.engine.Limit(depth=depth)

    # Stockfish's best move, with no restrictions.
    best_info = engine.analyse(board, limit)
    best_score = best_info["score"].pov(mover)
    best_move = best_info["pv"][0]

    # Evaluate the actual move, restricting Stockfish to that move.
    played_info = engine.analyse(
        board,
        limit,
        root_moves=[move]
    )
    played_score = played_info["score"].pov(mover)

    best_cp = best_score.score()
    played_cp = played_score.score()

    return {
        "bestMoveUci": best_move.uci(),
        "bestMoveSan": board.san(best_move),
        "bestMoveEvalCp": best_cp,
        "playedMoveEvalCp": played_cp,

        # Only calculate centipawn regret when neither
        # evaluation is a mate score.
        "moveRegretCp": (
            max(0, best_cp - played_cp)
            if best_cp is not None and played_cp is not None
            else None
        ),

        "bestMoveMate": best_score.mate(),
        "playedMoveMate": played_score.mate(),
    }

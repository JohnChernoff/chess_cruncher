
import chess
import chess.engine
import math

from king_safety import analyze_king_safety
from material import analyze_material
from config import STORE_PV, PV_LENGTH, SHALLOW_DEPTH, ANALYSIS_DEPTH, MATE_SCORE, CP_CLAMP

def clamp_cp(cp):
    return max(-CP_CLAMP, min(CP_CLAMP, cp))

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
    raw_cp = score.score(mate_score=MATE_SCORE)

    pv = info.get("pv", [])
    best_move = pv[0] if pv else None

    best_move_uci = best_move.uci() if best_move else None
    best_move_san = board.san(best_move) if best_move else None

    result = {
        "cp": clamp_cp(raw_cp),
        "rawCp": raw_cp,                    # unclamped; equals real cp when mate is None
        "winPercent": win_percent(raw_cp),
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
    shallow_cp = shallow_score.score(mate_score=MATE_SCORE)

    # Shallow search's preferred move.
    pv = info.get("pv", [])
    shallow_move = pv[0] if pv else None

    # Deep search's preferred move, obtained from the earlier search.
    deep_move = (
        chess.Move.from_uci(deep_best_move_uci)
        if deep_best_move_uci else None
    )

    result = {
        "shallowCp": clamp_cp(shallow_cp),
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

    # Evaluation gap (only meaningful when neither search sees a mate,
    # in which case both values are real centipawns).
    if deep_mate is None and shallow_mate is None:
        shift = deep_cp - shallow_cp
        result["depthShiftCp"] = shift
        result["depthGapCp"] = min(abs(shift), CP_CLAMP)

    # How bad is the shallow search's favourite move, judged at full depth?
    if shallow_move and deep_move:
        if shallow_move == deep_move:
            result["shallowMoveRegretCp"] = 0
        else:
            restricted_info = engine.analyse(
                board,
                chess.engine.Limit(depth=ANALYSIS_DEPTH),
                root_moves=[shallow_move]
            )

            deep_best_mover_cp = clamp_cp(
                deep_cp if board.turn == chess.WHITE else -deep_cp
            )
            shallow_move_cp = clamp_cp(
                restricted_info["score"]
                .pov(board.turn)
                .score(mate_score=MATE_SCORE)
            )

            result["shallowMoveRegretCp"] = max(
                0, deep_best_mover_cp - shallow_move_cp
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
    previous_win = None
    ply = 0

    def record_position(move_data=None):
        nonlocal previous_cp, previous_win

        evaluation = evaluate_position(
            engine,
            board,
            depth
        )

        # rawCp is the real centipawn value whenever there is no mate.
        material = analyze_material(
            board,
            None if evaluation["mate"] is not None else evaluation["rawCp"],
        )

        depth_analysis = evaluate_depth_gap(
            engine, board,
            evaluation["rawCp"],
            evaluation["mate"],
            evaluation["bestMoveUci"],
        )

        current_cp = evaluation["cp"]           # clamped
        current_win = evaluation["winPercent"] # White's perspective, 0-100

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

            white_moved = move_data["side"] == "white"
            win_change = current_win - previous_win
            cp_change = current_cp - previous_cp

            position["winChange"] = win_change                                   # White's view
            position["moverWinLoss"] = -win_change if white_moved else win_change
            position["evalChangeCp"] = cp_change
            position["moverEvalLossCp"] = -cp_change if white_moved else cp_change

        positions.append(position)

        previous_cp = current_cp
        previous_win = current_win

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

    best_info = engine.analyse(board, limit)
    best_score = best_info["score"].pov(mover)
    best_move = best_info["pv"][0]

    played_info = engine.analyse(board, limit, root_moves=[move])
    played_score = played_info["score"].pov(mover)

    best_cp = best_score.score(mate_score=MATE_SCORE)
    played_cp = played_score.score(mate_score=MATE_SCORE)

    return {
        "bestMoveUci": best_move.uci(),
        "bestMoveSan": board.san(best_move),
        "bestMoveEvalCp": clamp_cp(best_cp),
        "playedMoveEvalCp": clamp_cp(played_cp),
        "moveRegretCp": max(0, clamp_cp(best_cp) - clamp_cp(played_cp)),
        "moveRegretWin": max(0.0, win_percent(best_cp) - win_percent(played_cp)),
        "bestMoveMate": best_score.mate(),
        "playedMoveMate": played_score.mate(),
    }

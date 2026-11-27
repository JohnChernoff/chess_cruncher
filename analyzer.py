import chess
import chess.engine

from config import ANALYSIS_DEPTH, SHALLOW_DEPTH, MATE_SCORE
from features import piece_counts, king_features


def _limit(depth):
    return chess.engine.Limit(depth=depth)


def _cp(score, pov):
    """Centipawns from [pov]'s side; mate in n -> +/-(MATE_SCORE - n)."""
    return score.pov(pov).score(mate_score=MATE_SCORE)


def search_position(engine, board):
    """Deep + shallow search of one position.

    Returns (fields, best_move). Scores in [fields] are White's point of
    view; shallowRegretCp is from the side to move.
    """
    if board.is_game_over():
        # No engine call needed (and none is reliable) on terminal positions.
        if board.is_checkmate():
            cp = -MATE_SCORE if board.turn == chess.WHITE else MATE_SCORE
            mate = 0
        else:
            cp, mate = 0, None
        return {
            "cp": cp, "mate": mate, "best": None,
            "shallowCp": cp, "shallowBest": None, "shallowRegretCp": 0,
        }, None

    deep = engine.analyse(board, _limit(ANALYSIS_DEPTH))
    best = deep["pv"][0] if deep.get("pv") else None

    shallow = engine.analyse(board, _limit(SHALLOW_DEPTH))
    shallow_best = shallow["pv"][0] if shallow.get("pv") else None

    # How much worse is the shallow search's favourite move, judged at full
    # depth? High values mark positions with a tempting but bad move.
    regret = 0
    if best is not None and shallow_best is not None and shallow_best != best:
        restricted = engine.analyse(
            board, _limit(ANALYSIS_DEPTH), root_moves=[shallow_best]
        )
        regret = max(
            0,
            _cp(deep["score"], board.turn) - _cp(restricted["score"], board.turn),
        )

    return {
        "cp": _cp(deep["score"], chess.WHITE),
        "mate": deep["score"].white().mate(),
        "best": best.uci() if best else None,
        "shallowCp": _cp(shallow["score"], chess.WHITE),
        "shallowBest": shallow_best.uci() if shallow_best else None,
        "shallowRegretCp": regret,
    }, best


def position_record(engine, board):
    fields, best = search_position(engine, board)
    record = {
        "fen": board.fen(),
        "check": board.is_check(),
        **fields,
        "mat": {
            "w": piece_counts(board, chess.WHITE),
            "b": piece_counts(board, chess.BLACK),
        },
        "wk": king_features(board, chess.WHITE),
        "bk": king_features(board, chess.BLACK),
    }
    return record, best


def played_move_cp(engine, board, move, best_move, prev_cp_white):
    """Deep evaluation of the move actually played, from the mover's side."""
    mover = board.turn

    # If the mover found the engine's choice, its value is already known.
    if best_move is not None and move == best_move:
        return prev_cp_white if mover == chess.WHITE else -prev_cp_white

    info = engine.analyse(board, _limit(ANALYSIS_DEPTH), root_moves=[move])
    return _cp(info["score"], mover)


def analyze_game(engine, game, max_plies=None):
    """Analyse a game. plies[0] is the start; plies[i] follows the i-th half-move."""
    board = game.board()

    record, best = position_record(engine, board)
    plies = [record]

    for move in game.mainline_moves():
        if max_plies is not None and len(plies) - 1 >= max_plies:
            break

        mover = board.turn
        san = board.san(move)
        played_cp = played_move_cp(engine, board, move, best, plies[-1]["cp"])

        board.push(move)
        record, best = position_record(engine, board)
        record.update({
            "san": san,
            "uci": move.uci(),
            "side": "w" if mover == chess.WHITE else "b",
            "playedCp": played_cp,
        })
        plies.append(record)

    return {"headers": dict(game.headers), "plies": plies}

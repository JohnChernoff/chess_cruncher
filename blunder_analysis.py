
import math

from config import INACCURACY_WIN, MISTAKE_WIN, BLUNDER_WIN, BLUNDER_WINDOW_PLIES

def classify_regret(regret):          # win% points
    if regret is None:
        return None
    if regret >= BLUNDER_WIN:
        return "blunder"
    if regret >= MISTAKE_WIN:
        return "mistake"
    if regret >= INACCURACY_WIN:
        return "inaccuracy"
    return "minor"

def regret_activity(regret):
    """Convert win%-point regret into a continuous 0-1 measure."""
    if regret is None:
        return 0.0
    return 1.0 - math.exp(-regret / 10.0)


def analyze_blunders(positions):
    """
    Add move classifications and rolling blunder activity
    to each position.

    The rolling window includes the current move and the
    preceding BLUNDER_WINDOW_PLIES - 1 moves.
    """

    analyzed = []
    move_history = []

    for position in positions:
        result = dict(position)

        # Move information is nested inside position["move"].
        move = position.get("move")

        if move is None:
            result["blunderAnalysis"] = {
                "classification": None,
                "activity": {
                    "overall": 0.0,
                    "white": 0.0,
                    "black": 0.0,
                },
                "window": {
                    "plies": 0,
                    "whiteMoves": 0,
                    "blackMoves": 0,
                    "blunders": 0,
                    "mistakes": 0,
                    "inaccuracies": 0,
                },
            }
            analyzed.append(result)
            continue

        regret = move.get("moveRegretWin")
        mover = move.get("side")

        classification = classify_regret(regret)

        if mover not in ("white", "black"):
            mover = None

        if regret is not None:
            move_history.append({
                "side": mover,
                "regret": regret,
                "classification": classification,
                "activity": regret_activity(regret),
            })

        window = move_history[-BLUNDER_WINDOW_PLIES:]

        def side_activity(side):
            values = [
                item["activity"]
                for item in window
                if item["side"] == side
            ]

            return sum(values) / len(values) if values else 0.0

        overall_values = [
            item["activity"] for item in window
        ]

        overall_activity = (
            sum(overall_values) / len(overall_values)
            if overall_values else 0.0
        )

        result["blunderAnalysis"] = {
            "classification": classification,
            "activity": {
                "overall": overall_activity,
                "white": side_activity("white"),
                "black": side_activity("black"),
            },
            "window": {
                "plies": len(window),
                "whiteMoves": sum(
                    1 for item in window
                    if item["side"] == "white"
                ),
                "blackMoves": sum(
                    1 for item in window
                    if item["side"] == "black"
                ),
                "blunders": sum(
                    1 for item in window
                    if item["classification"] == "blunder"
                ),
                "mistakes": sum(
                    1 for item in window
                    if item["classification"] == "mistake"
                ),
                "inaccuracies": sum(
                    1 for item in window
                    if item["classification"] == "inaccuracy"
                ),
            },
        }

        analyzed.append(result)

    return analyzed

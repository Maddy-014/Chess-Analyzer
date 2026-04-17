import chess
import chess.engine
import chess.pgn
import io

ENGINE_PATH = "engine/stockfish.exe"
engine = chess.engine.SimpleEngine.popen_uci(ENGINE_PATH)


# ---------------- EXPLANATION GENERATOR ---------------- #
def generate_explanation(move, classification):

    # ---------- piece detection (SAN based) ----------
    if move[0].islower():
        piece_name = "Pawn"
    elif move[0] == "N":
        piece_name = "Knight"
    elif move[0] == "B":
        piece_name = "Bishop"
    elif move[0] == "R":
        piece_name = "Rook"
    elif move[0] == "Q":
        piece_name = "Queen"
    elif move[0] == "K":
        piece_name = "King"
    elif move.startswith("O-O"):
        piece_name = "King"
    else:
        piece_name = "Piece"

    # ---------- idea detection ----------
    if move in ["e4", "d4", "e5", "d5"]:
        idea = "controlling the center"
    elif move.startswith("N"):
        idea = "developing a knight"
    elif move.startswith("B"):
        idea = "developing a bishop"
    elif move.startswith("O-O"):
        idea = "castling for king safety"
    else:
        idea = "improving the position"

    # ---------- explanation ----------
    if classification == "Best":
        return f"{piece_name} move {move} is the best move, {idea}."

    elif classification == "Good":
        return f"{piece_name} move {move} is a good move, {idea}."

    elif classification == "Inaccuracy":
        return f"{piece_name} move {move} is slightly inaccurate and could be improved."

    elif classification == "Mistake":
        return f"{piece_name} move {move} is a mistake that weakens your position."

    elif classification == "Blunder":
        return f"{piece_name} move {move} is a blunder losing significant advantage."

    elif classification == "Checkmate":
        return "Checkmate! The game is over."

    else:
        return f"{move} is played."


# ---------------- MAIN ANALYSIS FUNCTION ---------------- #
def analyze_game(pgn_text):

    game = chess.pgn.read_game(io.StringIO(pgn_text))
    board = game.board()

    results = []

    for move in game.mainline_moves():

        # -------- engine analysis BEFORE move -------- #
        info = engine.analyse(board, chess.engine.Limit(depth=15), multipv=3)

        best_move = info[0]["pv"][0]

        score_obj = info[0]["score"].white()
        best_eval = score_obj.score(mate_score=10000) if score_obj else 0

        top_moves = [entry["pv"][0] for entry in info]

        played_move = move

        # ---------- SAN conversion BEFORE push ----------
        played_str = board.san(played_move)
        best_str = board.san(best_move)
        top_strs = [board.san(m) for m in top_moves]

        # ---------- play move ----------
        board.push(played_move)

        # ---------- checkmate ----------
        if board.is_checkmate():
            classification = "Checkmate"
            explanation = generate_explanation(played_str, classification)

            results.append({
                "move": played_str,
                "best_move": best_str,
                "classification": classification,
                "explanation": explanation
            })
            break

        # -------- engine analysis AFTER move -------- #
        info_after = engine.analyse(board, chess.engine.Limit(depth=15))
        score = info_after["score"].white()

        if score.is_mate():
            mate = score.mate()
            played_eval = 10000 if mate and mate > 0 else -10000
        else:
            cp = score.score()
            played_eval = max(-1000, min(1000, cp)) if cp is not None else 0

        # ---------- classification ----------
        if played_str == best_str:
            classification = "Best"

        elif played_str in top_strs:
            classification = "Good"

        else:
            if best_eval is None or played_eval is None:
                classification = "Unknown"
            else:
                relative_loss = abs(best_eval - played_eval)
                scale = abs(best_eval) + 1
                normalized_loss = relative_loss / scale

                if normalized_loss < 0.1:
                    classification = "Good"
                elif normalized_loss < 0.3:
                    classification = "Inaccuracy"
                elif normalized_loss < 0.6:
                    classification = "Mistake"
                else:
                    classification = "Blunder"

        # ---------- explanation ----------
        explanation = generate_explanation(played_str, classification)

        # ---------- store result ----------
        results.append({
            "move": played_str,
            "best_move": best_str,
            "classification": classification,
            "explanation": explanation,
            "eval": played_eval
        })

    return results
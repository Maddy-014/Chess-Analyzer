import chess
import chess.engine
import chess.pgn
import io

ENGINE_PATH = "engine/stockfish.exe"
engine = chess.engine.SimpleEngine.popen_uci(ENGINE_PATH)

PIECE_VALUES = {
    chess.PAWN: 100,
    chess.KNIGHT: 320,
    chess.BISHOP: 330,
    chess.ROOK: 500,
    chess.QUEEN: 900,
}

ATTACK_WEIGHTS = {
    chess.PAWN: 1,
    chess.KNIGHT: 2,
    chess.BISHOP: 2,
    chess.ROOK: 3,
    chess.QUEEN: 5
}


def get_material_balance(board):
    white_score = 0
    black_score = 0

    for piece in board.piece_map().values():
        value = PIECE_VALUES.get(piece.piece_type, 0)

        if piece.color == chess.WHITE:
            white_score += value
        else:
            black_score += value

    diff = white_score - black_score

    if diff > 0:
        balance = f"White +{diff}"
    elif diff < 0:
        balance = f"Black +{abs(diff)}"
    else:
        balance = "Equal"

    return diff, balance


def analyze_game(pgn_text):
    game = chess.pgn.read_game(io.StringIO(pgn_text))
    board = game.board()
    results = []

    for move in game.mainline_moves():
        # Engine analysis BEFORE move
        info = engine.analyse(
            board,
            chess.engine.Limit(depth=15),
            multipv=3,
        )

        best_move = info[0]["pv"][0]
        score_obj = info[0]["score"].white()
        best_eval = score_obj.score(mate_score=10000) if score_obj else 0
        top_moves = [entry["pv"][0] for entry in info]
        played_move = move

        # SAN conversion BEFORE push
        played_str = board.san(played_move)
        best_str = board.san(best_move)
        top_strs = [board.san(m) for m in top_moves]

        # Play move
        board.push(played_move)

        # Material analysis
        material_score, material_balance = get_material_balance(board)
        center_score, center_control = get_center_control(board)
        piece_activity_score, piece_activity = get_piece_activity(board)
        (
            white_king_safety,
            black_king_safety,
            king_safety_score,
            king_safety
        ) = get_king_safety(board)
        pawn_data = get_pawn_structure(board)
        position_explanation = generate_chess_commentary(
            material_balance,
            center_control,
            piece_activity,
            king_safety,
            pawn_data["pawn_structure"]
        )

        # Checkmate detection
        if board.is_checkmate():
            results.append({
                "move": played_str,
                "best_move": best_str,
                "classification": "Checkmate",
                "eval": 10000,
                "material_score": material_score,
                "material_balance": material_balance,
                "center_score": center_score,
                "center_control": center_control,
                "piece_activity_score": piece_activity_score,
                "piece_activity": piece_activity,
                "white_king_safety": white_king_safety,
                "black_king_safety": black_king_safety,
                "king_safety_score": king_safety_score,
                "king_safety": king_safety,
                "pawn_structure": pawn_data["pawn_structure"],
                "pawn_structure_score": pawn_data["pawn_structure_score"],

                "white_doubled": pawn_data["white_doubled"],
                "black_doubled": pawn_data["black_doubled"],

                "white_isolated": pawn_data["white_isolated"],
                "black_isolated": pawn_data["black_isolated"],

                "white_passed": pawn_data["white_passed"],
                "black_passed": pawn_data["black_passed"],

                "position_explanation": position_explanation,
            })
            break

        # Engine analysis AFTER move
        info_after = engine.analyse(
            board,
            chess.engine.Limit(depth=15),
        )

        score = info_after["score"].white()

        if score.is_mate():
            mate = score.mate()
            played_eval = 10000 if mate and mate > 0 else -10000
        else:
            cp = score.score()
            played_eval = max(-1000, min(1000, cp)) if cp is not None else 0

        # Classification
        if played_str == best_str:
            classification = "Best"
        elif played_str in top_strs:
            classification = "Good"
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

        results.append({
            "move": played_str,
            "best_move": best_str,
            "classification": classification,
            "eval": played_eval,
            "material_score": material_score,
            "material_balance": material_balance,
            "center_score": center_score,
            "center_control": center_control,
            "piece_activity_score": piece_activity_score,
            "piece_activity": piece_activity,
            "white_king_safety": white_king_safety,
            "black_king_safety": black_king_safety,
            "king_safety_score": king_safety_score,
            "king_safety": king_safety,
            "pawn_structure": pawn_data["pawn_structure"],
            "pawn_structure_score": pawn_data["pawn_structure_score"],

            "white_doubled": pawn_data["white_doubled"],
            "black_doubled": pawn_data["black_doubled"],

            "white_isolated": pawn_data["white_isolated"],
            "black_isolated": pawn_data["black_isolated"],

            "white_passed": pawn_data["white_passed"],
            "black_passed": pawn_data["black_passed"],

            "position_explanation": position_explanation,
        })

    return results

def get_center_control(board):

    # Core center
    center_squares = [
        chess.D4, chess.E4,
        chess.D5, chess.E5
    ]

    # Extended center
    extended_center = [
        chess.C3, chess.C4, chess.C5, chess.C6,
        chess.D3, chess.D4, chess.D5, chess.D6,
        chess.E3, chess.E4, chess.E5, chess.E6,
        chess.F3, chess.F4, chess.F5, chess.F6
    ]

    white_score = 0
    black_score = 0

    # -------- Occupancy Bonus --------
    for square in center_squares:

        piece = board.piece_at(square)

        if piece:
            if piece.color == chess.WHITE:
                white_score += 3
            else:
                black_score += 3

    # -------- Attack Control --------
    for square in center_squares:

        white_score += len(
            board.attackers(chess.WHITE, square)
        )

        black_score += len(
            board.attackers(chess.BLACK, square)
        )

    # -------- Extended Influence --------
    for square in extended_center:

        white_score += len(
            board.attackers(chess.WHITE, square)
        ) * 0.5

        black_score += len(
            board.attackers(chess.BLACK, square)
        ) * 0.5

    score = white_score - black_score

    if score > 0:
        control = "White"
    elif score < 0:
        control = "Black"
    else:
        control = "Equal"

    return score, control

def get_piece_activity(board):

    white_activity = 0
    black_activity = 0

    for square, piece in board.piece_map().items():

        activity = len(board.attacks(square))

        if piece.color == chess.WHITE:
            white_activity += activity
        else:
            black_activity += activity

    score = white_activity - black_activity

    if score > 0:
        side = "White"
    elif score < 0:
        side = "Black"
    else:
        side = "Equal"

    return score, side

def get_king_zone(king_square):

    zone = []

    king_file = chess.square_file(king_square)
    king_rank = chess.square_rank(king_square)

    for df in [-1, 0, 1]:
        for dr in [-1, 0, 1]:

            f = king_file + df
            r = king_rank + dr

            if 0 <= f <= 7 and 0 <= r <= 7:
                zone.append(chess.square(f, r))

    return zone

def get_king_safety(board):

    white_score = 0
    black_score = 0

    white_king = board.king(chess.WHITE)
    black_king = board.king(chess.BLACK)

    # ------------------------
    # Castling Bonus
    # ------------------------

    if white_king == chess.G1:
        white_score += 5
        white_shield = [chess.F2, chess.G2, chess.H2]

    elif white_king == chess.C1:
        white_score += 4
        white_shield = [chess.A2, chess.B2, chess.C2]

    else:
        white_shield = []

    if black_king == chess.G8:
        black_score += 5
        black_shield = [chess.F7, chess.G7, chess.H7]

    elif black_king == chess.C8:
        black_score += 4
        black_shield = [chess.A7, chess.B7, chess.C7]

    else:
        black_shield = []

    # ------------------------
    # Pawn Shield
    # ------------------------

    for sq in white_shield:

        piece = board.piece_at(sq)

        if (
            piece
            and piece.color == chess.WHITE
            and piece.piece_type == chess.PAWN
        ):
            white_score += 2

    for sq in black_shield:

        piece = board.piece_at(sq)

        if (
            piece
            and piece.color == chess.BLACK
            and piece.piece_type == chess.PAWN
        ):
            black_score += 2

    # ------------------------
    # Friendly Defenders
    # ------------------------

    white_score += len(
        board.attackers(chess.WHITE, white_king)
    )

    black_score += len(
        board.attackers(chess.BLACK, black_king)
    )

    # ------------------------
    # Enemy Pressure
    # ------------------------

    white_zone = get_king_zone(white_king)
    black_zone = get_king_zone(black_king)

    for square in white_zone:

        attackers = board.attackers(chess.BLACK, square)

        for attacker_square in attackers:

            piece = board.piece_at(attacker_square)

            if piece:
                white_score -= ATTACK_WEIGHTS.get(
                    piece.piece_type,
                    0
                )

    for square in black_zone:

        attackers = board.attackers(chess.WHITE, square)

        for attacker_square in attackers:

            piece = board.piece_at(attacker_square)

            if piece:
                black_score -= ATTACK_WEIGHTS.get(
                    piece.piece_type,
                    0
                )

    # ------------------------
    # Open File Penalty
    # ------------------------

    def file_has_friendly_pawn(file_idx, color):

        for rank in range(8):

            piece = board.piece_at(
                chess.square(file_idx, rank)
            )

            if (
                piece
                and piece.color == color
                and piece.piece_type == chess.PAWN
            ):
                return True

        return False

    if white_king == chess.G1:

        for f in [5, 6, 7]:

            if not file_has_friendly_pawn(f, chess.WHITE):
                white_score -= 3

    elif white_king == chess.C1:

        for f in [0, 1, 2]:

            if not file_has_friendly_pawn(f, chess.WHITE):
                white_score -= 3

    if black_king == chess.G8:

        for f in [5, 6, 7]:

            if not file_has_friendly_pawn(f, chess.BLACK):
                black_score -= 3

    elif black_king == chess.C8:

        for f in [0, 1, 2]:

            if not file_has_friendly_pawn(f, chess.BLACK):
                black_score -= 3

    # ------------------------
    # Final Result
    # ------------------------

    score = white_score - black_score

    if score > 0:
        side = "White"
    elif score < 0:
        side = "Black"
    else:
        side = "Equal"

    return (
        white_score,
        black_score,
        score,
        side
    )

def get_pawn_files(board, color):

    files = {}

    for square in chess.SQUARES:

        piece = board.piece_at(square)

        if (
            piece
            and piece.color == color
            and piece.piece_type == chess.PAWN
        ):

            file_idx = chess.square_file(square)

            if file_idx not in files:
                files[file_idx] = []

            files[file_idx].append(square)

    return files

def get_pawn_structure(board):

    white_score = 0
    black_score = 0

    white_files = get_pawn_files(board, chess.WHITE)
    black_files = get_pawn_files(board, chess.BLACK)

    # --------------------
    # Doubled Pawns
    # --------------------

    white_doubled = 0
    black_doubled = 0

    for pawns in white_files.values():

        if len(pawns) > 1:
            white_doubled += len(pawns) - 1
            white_score -= (len(pawns) - 1)

    for pawns in black_files.values():

        if len(pawns) > 1:
            black_doubled += len(pawns) - 1
            black_score -= (len(pawns) - 1)

    # --------------------
    # Isolated Pawns
    # --------------------

    white_isolated = 0
    black_isolated = 0

    for file_idx in white_files:

        left_exists = (file_idx - 1) in white_files
        right_exists = (file_idx + 1) in white_files

        if not left_exists and not right_exists:

            white_isolated += len(white_files[file_idx])
            white_score -= len(white_files[file_idx])

    for file_idx in black_files:

        left_exists = (file_idx - 1) in black_files
        right_exists = (file_idx + 1) in black_files

        if not left_exists and not right_exists:

            black_isolated += len(black_files[file_idx])
            black_score -= len(black_files[file_idx])

    # --------------------
    # Passed Pawns
    # --------------------

    white_passed = 0
    black_passed = 0

    for square in board.pieces(chess.PAWN, chess.WHITE):

        file_idx = chess.square_file(square)
        rank_idx = chess.square_rank(square)

        passed = True

        for enemy_pawn in board.pieces(chess.PAWN, chess.BLACK):

            ef = chess.square_file(enemy_pawn)
            er = chess.square_rank(enemy_pawn)

            if abs(ef - file_idx) <= 1 and er > rank_idx:
                passed = False
                break

        if passed:
            white_passed += 1
            white_score += 2

    for square in board.pieces(chess.PAWN, chess.BLACK):

        file_idx = chess.square_file(square)
        rank_idx = chess.square_rank(square)

        passed = True

        for enemy_pawn in board.pieces(chess.PAWN, chess.WHITE):

            ef = chess.square_file(enemy_pawn)
            er = chess.square_rank(enemy_pawn)

            if abs(ef - file_idx) <= 1 and er < rank_idx:
                passed = False
                break

        if passed:
            black_passed += 1
            black_score += 2

    # --------------------
    # Final
    # --------------------

    score = white_score - black_score

    if score > 0:
        side = "White"
    elif score < 0:
        side = "Black"
    else:
        side = "Equal"

    return {
        "pawn_structure": side,
        "pawn_structure_score": score,
        "white_doubled": white_doubled,
        "black_doubled": black_doubled,
        "white_isolated": white_isolated,
        "black_isolated": black_isolated,
        "white_passed": white_passed,
        "black_passed": black_passed
    }

def generate_chess_commentary(
    material_balance,
    center_control,
    piece_activity,
    king_safety,
    pawn_structure
):

    white_advantages = []
    black_advantages = []

    # Material
    if material_balance.startswith("White"):
        white_advantages.append("a material advantage")

    elif material_balance.startswith("Black"):
        black_advantages.append("a material advantage")

    # Center Control
    if center_control == "White":
        white_advantages.append("better central control")

    elif center_control == "Black":
        black_advantages.append("better central control")

    # Piece Activity
    if piece_activity == "White":
        white_advantages.append("more active pieces")

    elif piece_activity == "Black":
        black_advantages.append("more active pieces")

    # King Safety
    if king_safety == "White":
        white_advantages.append("the safer king")

    elif king_safety == "Black":
        black_advantages.append("the safer king")

    # Pawn Structure
    if pawn_structure == "White":
        white_advantages.append("the healthier pawn structure")

    elif pawn_structure == "Black":
        black_advantages.append("the healthier pawn structure")

    commentary = []

    if white_advantages:
        if len(white_advantages) == 1:
            commentary.append(
                f"White has {white_advantages[0]}."
            )
        else:
            commentary.append(
                "White has "
                + ", ".join(white_advantages[:-1])
                + " and "
                + white_advantages[-1]
                + "."
            )

    if black_advantages:
        if len(black_advantages) == 1:
            commentary.append(
                f"Black has {black_advantages[0]}."
            )
        else:
            commentary.append(
                "Black has "
                + ", ".join(black_advantages[:-1])
                + " and "
                + black_advantages[-1]
                + "."
            )

    if white_advantages and black_advantages:
        commentary.append(
            "The position contains dynamic imbalances for both sides."
        )
    elif white_advantages:
        commentary.append(
            "White appears to have the more comfortable position."
        )
    elif black_advantages:
        commentary.append(
            "Black appears to have the more comfortable position."
        )
    else:
        commentary.append(
            "The position is roughly balanced."
        )

    return " ".join(commentary)
PIECE_VALUES = {
    1: 1.0,
    2: 3.0,
    3: 3.15,
    4: 5.0,
    5: 9.0,
    6: 0.0,
}

CENTER_SQUARES = {(3, 3), (3, 4), (4, 3), (4, 4)}
EXTENDED_CENTER = {
    (2, 2), (2, 3), (2, 4), (2, 5),
    (3, 2), (3, 3), (3, 4), (3, 5),
    (4, 2), (4, 3), (4, 4), (4, 5),
    (5, 2), (5, 3), (5, 4), (5, 5),
}

PAWN_TABLE = [
    [0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00],
    [0.50, 0.50, 0.50, 0.50, 0.50, 0.50, 0.50, 0.50],
    [0.10, 0.10, 0.20, 0.30, 0.30, 0.20, 0.10, 0.10],
    [0.05, 0.05, 0.10, 0.25, 0.25, 0.10, 0.05, 0.05],
    [0.00, 0.00, 0.00, 0.20, 0.20, 0.00, 0.00, 0.00],
    [0.05, -0.05, -0.10, 0.00, 0.00, -0.10, -0.05, 0.05],
    [0.05, 0.10, 0.10, -0.20, -0.20, 0.10, 0.10, 0.05],
    [0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00],
]

KNIGHT_TABLE = [
    [-0.50, -0.40, -0.30, -0.30, -0.30, -0.30, -0.40, -0.50],
    [-0.40, -0.20, 0.00, 0.05, 0.05, 0.00, -0.20, -0.40],
    [-0.30, 0.05, 0.10, 0.15, 0.15, 0.10, 0.05, -0.30],
    [-0.30, 0.00, 0.15, 0.25, 0.25, 0.15, 0.00, -0.30],
    [-0.30, 0.05, 0.15, 0.25, 0.25, 0.15, 0.05, -0.30],
    [-0.30, 0.00, 0.10, 0.15, 0.15, 0.10, 0.00, -0.30],
    [-0.40, -0.20, 0.00, 0.00, 0.00, 0.00, -0.20, -0.40],
    [-0.50, -0.40, -0.30, -0.30, -0.30, -0.30, -0.40, -0.50],
]

BISHOP_TABLE = [
    [-0.20, -0.10, -0.10, -0.10, -0.10, -0.10, -0.10, -0.20],
    [-0.10, 0.05, 0.00, 0.00, 0.00, 0.00, 0.05, -0.10],
    [-0.10, 0.10, 0.10, 0.10, 0.10, 0.10, 0.10, -0.10],
    [-0.10, 0.00, 0.10, 0.15, 0.15, 0.10, 0.00, -0.10],
    [-0.10, 0.05, 0.05, 0.15, 0.15, 0.05, 0.05, -0.10],
    [-0.10, 0.00, 0.05, 0.10, 0.10, 0.05, 0.00, -0.10],
    [-0.10, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, -0.10],
    [-0.20, -0.10, -0.10, -0.10, -0.10, -0.10, -0.10, -0.20],
]

ROOK_TABLE = [
    [0.00, 0.00, 0.00, 0.05, 0.05, 0.00, 0.00, 0.00],
    [0.05, 0.10, 0.10, 0.10, 0.10, 0.10, 0.10, 0.05],
    [-0.05, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, -0.05],
    [-0.05, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, -0.05],
    [-0.05, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, -0.05],
    [-0.05, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, -0.05],
    [-0.05, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, -0.05],
    [0.00, 0.00, 0.00, 0.05, 0.05, 0.00, 0.00, 0.00],
]

QUEEN_TABLE = [
    [-0.20, -0.10, -0.10, -0.05, -0.05, -0.10, -0.10, -0.20],
    [-0.10, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, -0.10],
    [-0.10, 0.00, 0.05, 0.05, 0.05, 0.05, 0.00, -0.10],
    [-0.05, 0.00, 0.05, 0.05, 0.05, 0.05, 0.00, -0.05],
    [0.00, 0.00, 0.05, 0.05, 0.05, 0.05, 0.00, -0.05],
    [-0.10, 0.05, 0.05, 0.05, 0.05, 0.05, 0.00, -0.10],
    [-0.10, 0.00, 0.05, 0.00, 0.00, 0.00, 0.00, -0.10],
    [-0.20, -0.10, -0.10, -0.05, -0.05, -0.10, -0.10, -0.20],
]

KING_MIDDLE_TABLE = [
    [-0.30, -0.40, -0.40, -0.50, -0.50, -0.40, -0.40, -0.30],
    [-0.30, -0.40, -0.40, -0.50, -0.50, -0.40, -0.40, -0.30],
    [-0.30, -0.40, -0.40, -0.50, -0.50, -0.40, -0.40, -0.30],
    [-0.30, -0.40, -0.40, -0.50, -0.50, -0.40, -0.40, -0.30],
    [-0.20, -0.30, -0.30, -0.40, -0.40, -0.30, -0.30, -0.20],
    [-0.10, -0.20, -0.20, -0.20, -0.20, -0.20, -0.20, -0.10],
    [0.20, 0.20, 0.00, 0.00, 0.00, 0.00, 0.20, 0.20],
    [0.20, 0.30, 0.10, 0.00, 0.00, 0.10, 0.30, 0.20],
]

PIECE_TABLES = {
    1: PAWN_TABLE,
    2: KNIGHT_TABLE,
    3: BISHOP_TABLE,
    4: ROOK_TABLE,
    5: QUEEN_TABLE,
    6: KING_MIDDLE_TABLE,
}


class Evaluate:
    def evaluate(self, board, side_to_move=0):
        score = 0.0
        pieces = self.collect_pieces(board)
        attacks = {
            1: self.attack_map(board, 1),
            -1: self.attack_map(board, -1),
        }

        for row, col, piece in pieces:
            team = self.team(piece)
            piece_type = abs(piece)
            score += team * PIECE_VALUES[piece_type]
            score += team * self.piece_square_value(piece_type, team, row, col)

        score += self.mobility_score(board)
        score += self.center_control_score(attacks)
        score += self.pawn_structure_score(board)
        score += self.rook_file_score(board)
        score += self.bishop_pair_score(pieces)
        score += self.knight_outpost_score(board, attacks)
        score += self.king_safety_score(board, attacks)
        score += self.development_score(board)
        score += self.hanging_and_defended_score(board, pieces, attacks)
        score += self.pin_score(board)
        score += self.check_score(board)

        if side_to_move in (1, -1):
            score += 0.05 * side_to_move

        return score

    def collect_pieces(self, board):
        pieces = []
        for row in range(8):
            for col in range(8):
                piece = board.state[row][col]
                if abs(piece) in PIECE_VALUES:
                    pieces.append((row, col, piece))
        return pieces

    def team(self, piece):
        if piece > 0:
            return 1
        if piece < 0:
            return -1
        return 0

    def in_bounds(self, row, col):
        return 0 <= row <= 7 and 0 <= col <= 7

    def piece_square_value(self, piece_type, team, row, col):
        table = PIECE_TABLES[piece_type]
        table_row = row if team == 1 else 7 - row
        return table[table_row][col]

    def mobility_score(self, board):
        white_mobility = self.pseudo_mobility(board, 1)
        black_mobility = self.pseudo_mobility(board, -1)
        return 0.025 * (white_mobility - black_mobility)

    def center_control_score(self, attacks):
        white_center = len(attacks[1] & CENTER_SQUARES)
        black_center = len(attacks[-1] & CENTER_SQUARES)
        white_extended = len(attacks[1] & EXTENDED_CENTER)
        black_extended = len(attacks[-1] & EXTENDED_CENTER)
        return 0.05 * (white_center - black_center) + 0.015 * (white_extended - black_extended)

    def pseudo_mobility(self, board, team):
        count = 0
        for row, col, piece in self.collect_pieces(board):
            if self.team(piece) == team:
                count += len(self.pseudo_moves(board, row, col))
        return count

    def pawn_structure_score(self, board):
        score = 0.0
        for team in (1, -1):
            pawns = self.pawns_for_team(board, team)
            enemy_pawns = self.pawns_for_team(board, -team)
            files = [col for row, col in pawns]

            for file in range(8):
                count = files.count(file)
                if count > 1:
                    score -= team * 0.18 * (count - 1)

            for row, col in pawns:
                if self.is_isolated_pawn(pawns, col):
                    score -= team * 0.15

                if self.is_passed_pawn(row, col, team, enemy_pawns):
                    advance = self.pawn_advance(row, team)
                    score += team * (0.25 + 0.12 * advance)

                if self.is_backward_pawn(board, row, col, team, pawns):
                    score -= team * 0.12

                if self.is_pawn_chain_member(board, row, col, team):
                    score += team * 0.08

                if (row, col) in CENTER_SQUARES:
                    score += team * 0.18

                center_attacks = set(self.pawn_attacks(row, col, team)) & CENTER_SQUARES
                score += team * 0.08 * len(center_attacks)

        return score

    def pawns_for_team(self, board, team):
        pawn = team
        return [
            (row, col)
            for row in range(8)
            for col in range(8)
            if board.state[row][col] == pawn
        ]

    def is_isolated_pawn(self, pawns, col):
        return not any(abs(other_col - col) == 1 for row, other_col in pawns)

    def is_passed_pawn(self, row, col, team, enemy_pawns):
        for enemy_row, enemy_col in enemy_pawns:
            if abs(enemy_col - col) > 1:
                continue
            if team == 1 and enemy_row < row:
                return False
            if team == -1 and enemy_row > row:
                return False
        return True

    def pawn_advance(self, row, team):
        return 6 - row if team == 1 else row - 1

    def is_backward_pawn(self, board, row, col, team, pawns):
        front_row = row - team
        if not self.in_bounds(front_row, col) or board.state[front_row][col] != 0:
            return False

        has_friendly_help = any(
            abs(other_col - col) == 1 and self.pawn_advance(other_row, team) >= self.pawn_advance(row, team)
            for other_row, other_col in pawns
        )
        if has_friendly_help:
            return False

        return any((front_row, col) == square for square in self.enemy_pawn_attacks(board, -team))

    def is_pawn_chain_member(self, board, row, col, team):
        defender_row = row + team
        for defender_col in (col - 1, col + 1):
            if self.in_bounds(defender_row, defender_col) and board.state[defender_row][defender_col] == team:
                return True
        return False

    def rook_file_score(self, board):
        score = 0.0
        for row, col, piece in self.collect_pieces(board):
            if abs(piece) != 4:
                continue

            team = self.team(piece)
            file_pieces = [board.state[r][col] for r in range(8)]
            friendly_pawns = file_pieces.count(team)
            enemy_pawns = file_pieces.count(-team)

            if friendly_pawns == 0 and enemy_pawns == 0:
                score += team * 0.30
            elif friendly_pawns == 0 and enemy_pawns > 0:
                score += team * 0.18

            if (team == 1 and row == 1) or (team == -1 and row == 6):
                score += team * 0.30

        return score

    def bishop_pair_score(self, pieces):
        white_bishops = sum(1 for row, col, piece in pieces if piece == 3)
        black_bishops = sum(1 for row, col, piece in pieces if piece == -3)
        score = 0.0
        if white_bishops >= 2:
            score += 0.35
        if black_bishops >= 2:
            score -= 0.35
        return score

    def knight_outpost_score(self, board, attacks):
        score = 0.0
        for row, col, piece in self.collect_pieces(board):
            if abs(piece) != 2 or row not in (2, 3, 4, 5):
                continue

            team = self.team(piece)
            defended_by_pawn = (row, col) in self.enemy_pawn_attacks(board, team)
            attackable_by_enemy_pawn = (row, col) in self.enemy_pawn_attacks(board, -team)
            if defended_by_pawn and not attackable_by_enemy_pawn:
                score += team * 0.25

        return score

    def king_safety_score(self, board, attacks):
        score = 0.0
        kings = self.king_positions(board)

        for team, king_pos in kings.items():
            if king_pos is None:
                continue

            row, col = king_pos

            if (team == 1 and row == 7 and col in (2, 6)) or (team == -1 and row == 0 and col in (2, 6)):
                score += team * 0.45

            score += team * self.king_pawn_shield(board, row, col, team)
            score -= team * self.king_exposure(board, col, team)

            enemy_king = kings[-team]
            if enemy_king is not None:
                enemy_zone = set(self.king_zone(*enemy_king))
                pressure = len(attacks[team] & enemy_zone)
                score += team * 0.05 * pressure

        return score

    def king_positions(self, board):
        kings = {1: None, -1: None}
        for row in range(8):
            for col in range(8):
                if board.state[row][col] == 6:
                    kings[1] = (row, col)
                elif board.state[row][col] == -6:
                    kings[-1] = (row, col)
        return kings

    def king_pawn_shield(self, board, row, col, team):
        bonus = 0.0
        front_row = row - team
        second_row = row - (2 * team)
        for shield_col in (col - 1, col, col + 1):
            if self.in_bounds(front_row, shield_col) and board.state[front_row][shield_col] == team:
                bonus += 0.12
            if self.in_bounds(second_row, shield_col) and board.state[second_row][shield_col] == team:
                bonus += 0.05
        return bonus

    def king_exposure(self, board, king_col, team):
        penalty = 0.0
        for file in (king_col - 1, king_col, king_col + 1):
            if not 0 <= file <= 7:
                continue
            file_pieces = [board.state[row][file] for row in range(8)]
            friendly_pawn = team in file_pieces
            enemy_pawn = -team in file_pieces
            if not friendly_pawn:
                penalty += 0.12
            if not friendly_pawn and not enemy_pawn:
                penalty += 0.08
        return penalty

    def development_score(self, board):
        score = 0.0
        if not self.is_opening(board):
            return score

        undeveloped_white = 0
        undeveloped_black = 0

        for row, col, piece in ((7, 1, 2), (7, 6, 2), (7, 2, 3), (7, 5, 3)):
            if board.state[row][col] == piece:
                undeveloped_white += 1
                score -= 0.12

        for row, col, piece in ((0, 1, -2), (0, 6, -2), (0, 2, -3), (0, 5, -3)):
            if board.state[row][col] == piece:
                undeveloped_black += 1
                score += 0.12

        if board.state[7][3] != 5 and undeveloped_white >= 2:
            score -= 0.25
        if board.state[0][3] != -5 and undeveloped_black >= 2:
            score += 0.25

        return score

    def is_opening(self, board):
        non_pawn_material = 0.0
        for row, col, piece in self.collect_pieces(board):
            piece_type = abs(piece)
            if piece_type not in (1, 6):
                non_pawn_material += PIECE_VALUES[piece_type]
        return non_pawn_material > 40

    def hanging_and_defended_score(self, board, pieces, attacks):
        score = 0.0
        defender_counts = {
            1: self.defender_counts(board, 1),
            -1: self.defender_counts(board, -1),
        }
        attackers = {
            1: self.attackers_by_square(board, 1),
            -1: self.attackers_by_square(board, -1),
        }

        for row, col, piece in pieces:
            piece_type = abs(piece)
            if piece_type == 6:
                continue

            team = self.team(piece)
            square = (row, col)
            value = PIECE_VALUES[piece_type]
            is_attacked = square in attacks[-team]
            is_defended = defender_counts[team].get(square, 0) > 0

            if is_attacked and not is_defended:
                score -= team * (0.12 * value)

            enemy_attackers = attackers[-team].get(square, [])
            if enemy_attackers:
                cheapest_attacker = min(PIECE_VALUES[abs(attacker)] for attacker in enemy_attackers)
                if cheapest_attacker < value:
                    score -= team * (0.08 * (value - cheapest_attacker))

            if is_defended:
                score += team * min(0.08, 0.02 * value)

        return score

    def pin_score(self, board):
        score = 0.0
        for team in (1, -1):
            score += team * 0.18 * self.count_pins_against(board, -team)
        return score

    def count_pins_against(self, board, pinned_team):
        count = 0
        targets = []
        for row, col, piece in self.collect_pieces(board):
            if self.team(piece) == pinned_team and abs(piece) in (5, 6):
                targets.append((row, col))

        directions = [
            (-1, 0), (1, 0), (0, -1), (0, 1),
            (-1, -1), (-1, 1), (1, -1), (1, 1),
        ]

        for target_row, target_col in targets:
            for row_dir, col_dir in directions:
                blocker_seen = False
                row = target_row + row_dir
                col = target_col + col_dir

                while self.in_bounds(row, col):
                    piece = board.state[row][col]
                    if piece == 0 or abs(piece) == 7:
                        row += row_dir
                        col += col_dir
                        continue

                    if not blocker_seen:
                        if self.team(piece) == pinned_team and abs(piece) not in (5, 6):
                            blocker_seen = True
                            row += row_dir
                            col += col_dir
                            continue
                        break

                    if self.team(piece) == -pinned_team and self.slider_matches_direction(piece, row_dir, col_dir):
                        count += 1
                    break

        return count

    def slider_matches_direction(self, piece, row_dir, col_dir):
        piece_type = abs(piece)
        diagonal = row_dir != 0 and col_dir != 0
        if diagonal:
            return piece_type in (3, 5)
        return piece_type in (4, 5)

    def check_score(self, board):
        white_in_check, black_in_check, white_king_pos, black_king_pos = board.king_check_check()
        score = 0.0
        if black_in_check:
            score += 0.35
        if white_in_check:
            score -= 0.35
        return score

    def attack_map(self, board, team):
        attacks = set()
        for row, col, piece in self.collect_pieces(board):
            if self.team(piece) == team:
                attacks.update(self.pseudo_attacks(board, row, col))
        return attacks

    def defender_counts(self, board, team):
        counts = {}
        for row, col, piece in self.collect_pieces(board):
            if self.team(piece) != team:
                continue
            for square in self.pseudo_attacks(board, row, col):
                counts[square] = counts.get(square, 0) + 1
        return counts

    def attackers_by_square(self, board, team):
        attackers = {}
        for row, col, piece in self.collect_pieces(board):
            if self.team(piece) != team:
                continue
            for square in self.pseudo_attacks(board, row, col):
                attackers.setdefault(square, []).append(piece)
        return attackers

    def pseudo_moves(self, board, row, col):
        piece = board.state[row][col]
        team = self.team(piece)
        piece_type = abs(piece)

        if piece_type == 1:
            return self.pawn_moves(board, row, col, team)

        moves = []
        for move_row, move_col in self.pseudo_attacks(board, row, col):
            target = board.state[move_row][move_col]
            if target == 0 or abs(target) == 7 or self.team(target) == -team:
                moves.append((move_row, move_col))
        return moves

    def pseudo_attacks(self, board, row, col):
        piece = board.state[row][col]
        team = self.team(piece)
        piece_type = abs(piece)

        if piece_type == 1:
            return self.pawn_attacks(row, col, team)

        if piece_type == 2:
            return [
                (r, c)
                for r, c in (
                    (row + 2, col + 1), (row + 2, col - 1),
                    (row - 2, col + 1), (row - 2, col - 1),
                    (row + 1, col + 2), (row + 1, col - 2),
                    (row - 1, col + 2), (row - 1, col - 2),
                )
                if self.in_bounds(r, c)
            ]

        if piece_type == 6:
            return self.king_zone(row, col)

        directions = []
        if piece_type in (3, 5):
            directions += [(-1, -1), (-1, 1), (1, -1), (1, 1)]
        if piece_type in (4, 5):
            directions += [(-1, 0), (1, 0), (0, -1), (0, 1)]

        attacks = []
        for row_dir, col_dir in directions:
            current_row = row + row_dir
            current_col = col + col_dir
            while self.in_bounds(current_row, current_col):
                attacks.append((current_row, current_col))
                if board.state[current_row][current_col] != 0 and abs(board.state[current_row][current_col]) != 7:
                    break
                current_row += row_dir
                current_col += col_dir
        return attacks

    def pawn_moves(self, board, row, col, team):
        moves = []
        front_row = row - team
        if self.in_bounds(front_row, col) and board.state[front_row][col] == 0:
            moves.append((front_row, col))

            start_row = 6 if team == 1 else 1
            double_row = row - (2 * team)
            if row == start_row and self.in_bounds(double_row, col) and board.state[double_row][col] == 0:
                moves.append((double_row, col))

        for attack_row, attack_col in self.pawn_attacks(row, col, team):
            target = board.state[attack_row][attack_col]
            if self.team(target) == -team or target == -7 * team:
                moves.append((attack_row, attack_col))

        return moves

    def pawn_attacks(self, row, col, team):
        attacks = []
        attack_row = row - team
        for attack_col in (col - 1, col + 1):
            if self.in_bounds(attack_row, attack_col):
                attacks.append((attack_row, attack_col))
        return attacks

    def enemy_pawn_attacks(self, board, team):
        attacks = set()
        for row, col in self.pawns_for_team(board, team):
            attacks.update(self.pawn_attacks(row, col, team))
        return attacks

    def king_zone(self, row, col):
        return [
            (r, c)
            for r in (row - 1, row, row + 1)
            for c in (col - 1, col, col + 1)
            if self.in_bounds(r, c) and (r, c) != (row, col)
        ]

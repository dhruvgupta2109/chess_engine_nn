from board import Board
from evaluate import Evaluate

class Search:
    def __init__(self):
        self.evaluate = Evaluate()
        pass

    def copy_board(self, board):
        new_board = Board()
        new_board.state = [r[:] for r in board.state]
        new_board.white_king_moved = board.white_king_moved
        new_board.black_king_moved = board.black_king_moved
        new_board.white_rook_a_moved = board.white_rook_a_moved
        new_board.white_rook_h_moved = board.white_rook_h_moved
        new_board.black_rook_a_moved = board.black_rook_a_moved
        new_board.black_rook_h_moved = board.black_rook_h_moved
        return new_board

    def move_order_score(self, board, move):
        target_piece = board.state[move[2]][move[3]]

        score = 0

        ## PROMOTIONS FIRST
        if move[4] is not None:
            score += 100

        ## CAPTURES FIRST
        if target_piece != 0 and target_piece != 7 and target_piece != -7:
            score += abs(target_piece) * 10

        return score

    def minmax(self, board, team, depth, alpha=-99999, beta=99999):
        legal_moves = board.get_all_legal_moves(team)

        if len(legal_moves) == 0:
            white_in_check, black_in_check, white_king_pos, black_king_pos = board.king_check_check()

            if team == 1:
                if white_in_check:
                    return -1000 - depth, None
                else:
                    return 0, None

            if team == -1:
                if black_in_check:
                    return 1000 + depth, None
                else:
                    return 0, None

        if depth == 0:
            return self.evaluate.evaluate(board, team), None

        legal_moves.sort(key=lambda move: self.move_order_score(board, move), reverse=True)

        best_eval = None
        best_move = None

        for m in legal_moves:
            child_board = self.copy_board(board)
            child_board.move_piece(m[0], m[1], m[2], m[3], m[4])

            eval, dont_need = self.minmax(child_board, team * -1, depth - 1, alpha, beta)

            match team:
                case 1:
                    if best_eval is None or eval > best_eval:
                        best_eval = eval
                        best_move = m

                    if best_eval > alpha:
                        alpha = best_eval

                case -1:
                    if best_eval is None or eval < best_eval:
                        best_eval = eval
                        best_move = m

                    if best_eval < beta:
                        beta = best_eval

            print('move:', m, 'eval:', eval)

            if beta <= alpha:
                break
        
        return best_eval, best_move

# PIECES

# 0 = empty

# 1 - white pawn
# 2 - white knight
# 3 - white bishop
# 4 - white rook
# 5 - white queen
# 6 - white king

# -1 - black pawn
# -2 - black knight
# -3 - black bishop
# -4 - black rook
# -5 - black queen
# -6 - black king

class Board:
    def __init__(self):
        self.state = [[-4,-2,-3,-5,-6,-3,-2,-4],
                      [-1,-1,-1,-1,-1,-1,-1,-1],
                      [ 0, 0, 0, 0, 0, 0, 0, 0],
                      [ 0, 0, 0, 0, 0, 0, 0, 0],
                      [ 0, 0, 0, 0, 0, 0, 0, 0],
                      [ 0, 0, 0, 0, 0, 0, 0, 0],
                      [ 1, 1, 1, 1, 1, 1, 1, 1],
                      [ 4, 2, 3, 5, 6, 3, 2, 4]]
        
        self.white_king_moved = False
        self.black_king_moved = False
        self.white_rook_a_moved = False
        self.white_rook_h_moved = False
        self.black_rook_a_moved = False
        self.black_rook_h_moved = False
                
    def move_piece(self,row,column,new_row,new_column,promotion_piece=None):
        piece = self.state[row][column]
        team = 1 if self.state[row][column] > 0 else -1
        target_piece = self.state[new_row][new_column]

        if (piece == 6) and (row == 7 and column == 4) and (new_row == 7 and new_column == 6) and self.state[7][7] == 4: ## WHITE KINGSIDE CASTLE
            self.state[row][column] = 0
            self.state[new_row][new_column] = piece
            self.state[7][5] = 4
            self.state[7][7] = 0

        elif (piece == 6) and (row == 7 and column == 4) and (new_row == 7 and new_column == 2) and self.state[7][0] == 4: ## WHITE QUEENSIDE CASTLE
            self.state[row][column] = 0
            self.state[new_row][new_column] = piece
            self.state[7][3] = 4
            self.state[7][0] = 0

        elif (piece == -6) and (row == 0 and column == 4) and (new_row == 0 and new_column == 6) and self.state[0][7] == -4: ## BLACK KINGSIDE CASTLE
            self.state[row][column] = 0
            self.state[new_row][new_column] = piece
            self.state[0][5] = -4
            self.state[0][7] = 0

        elif (piece == -6) and (row == 0 and column == 4) and (new_row == 0 and new_column == 2) and self.state[0][0] == -4: ## BLACK QUEENSIDE CASTLE
            self.state[row][column] = 0
            self.state[new_row][new_column] = piece
            self.state[0][3] = -4
            self.state[0][0] = 0

        elif (piece == 1) and (target_piece == -7): ## CAPTURE ON EN PASSANT SQUARE WHITE
            self.state[row][column] = 0
            if promotion_piece != None:
                self.state[new_row][new_column] = promotion_piece
            else:
                self.state[new_row][new_column] = piece
            self.state[new_row + 1][new_column] = 0

        elif (piece == -1) and (target_piece == 7): ## CAPTURE ON EN PASSANT SQUARE BLACK
            self.state[row][column] = 0
            if promotion_piece != None:
                self.state[new_row][new_column] = -promotion_piece
            else:
                self.state[new_row][new_column] = piece
            self.state[new_row - 1][new_column] = 0

        else:
            self.state[row][column] = 0
            if promotion_piece != None:
                self.state[new_row][new_column] = promotion_piece if team == 1 else -promotion_piece
            else:
                self.state[new_row][new_column] = piece

        for i in range(len(self.state)): ## CLEAR OLD EN PASSANT MARKERS
            for j in range(len(self.state[i])):
                if self.state[i][j] == 7 or self.state[i][j] == -7:
                    self.state[i][j] = 0

        if (piece == 1) and (new_row == row - 2): ## WHITE EN PASSANT MARKER
            self.state[row - 1][column] = 7
        elif (piece == -1) and (new_row == row + 2): ## BLACK EN PASSANT MARKER
            self.state[row + 1][column] = -7

        ## TRACK KING / ROOK MOVES FOR CASTLING
        if piece == 6:
            self.white_king_moved = True
        elif piece == -6:
            self.black_king_moved = True
        elif piece == 4 and row == 7 and column == 0:
            self.white_rook_a_moved = True
        elif piece == 4 and row == 7 and column == 7:
            self.white_rook_h_moved = True
        elif piece == -4 and row == 0 and column == 0:
            self.black_rook_a_moved = True
        elif piece == -4 and row == 0 and column == 7:
            self.black_rook_h_moved = True

        white_in_check, black_in_check, white_king_pos, black_king_pos = self.king_check_check()

    def long_range_recursion(self,row,column,dirx,diry,team):
        c_row = row + dirx
        c_col = column + diry
        legal_moves = []

        if c_row < 0 or c_row > 7 or c_col < 0 or c_col > 7:
            return legal_moves

        c_piece = self.state[c_row][c_col]

        if c_piece == 0:
            legal_moves.append((c_row,c_col,None))
            legal_moves += self.long_range_recursion(c_row,c_col,dirx,diry,team)
            return legal_moves

        if team > 0 and c_piece < 0:
            legal_moves.append((c_row,c_col,None))
        elif team < 0 and c_piece > 0:
            legal_moves.append((c_row,c_col,None))
        return legal_moves
    
    def king_check_check(self):
        white_in_check = False
        black_in_check = False
        white_king_pos = None
        black_king_pos = None

        for row in range(len(self.state)):
            for col in range(len(self.state[row])):
                if self.state[row][col] == 6: ## WHITE KING
                    white_king_pos = (row, col)

                    team = 1

                    ##CHECK FOR PAWNS
                    if row - 1 >= 0:
                        if col + 1 <= 7 and self.state[row - 1][col + 1] == -1:
                            white_in_check = True
                        if col - 1 >= 0 and self.state[row - 1][col - 1] == -1:
                            white_in_check = True

                    ##CHECK FOR KNIGHTS:
                    knight_moves = ((row + 2, col + 1), (row + 2, col - 1), (row - 2, col + 1), (row - 2, col - 1), (row + 1, col + 2), (row + 1, col - 2), (row - 1, col + 2), (row - 1, col -2))
                    for i in knight_moves:
                        if i[0] >= 0 and i[1] >= 0 and i[0] <= 7 and i[1] <= 7:
                            r = i[0]
                            c = i[1]
                            if self.state[r][c] == -2:
                                white_in_check = True
                    
                    ##CHECK FOR BISHOP / QUEEN DIAGONALS
                    legal_moves = []
                    legal_moves += self.long_range_recursion(row,col,-1,-1,team)
                    legal_moves += self.long_range_recursion(row,col,-1,1,team)
                    legal_moves += self.long_range_recursion(row,col,1,-1,team)
                    legal_moves += self.long_range_recursion(row,col,1,1,team)

                    for i in legal_moves:
                        r = i[0]
                        c = i[1]
                        if self.state[r][c] == -3 or self.state[r][c] == -5:
                            white_in_check = True

                    ##CHECK FOR ROOK / QUEEN STRAIGHTS
                    legal_moves = []
                    legal_moves += self.long_range_recursion(row,col,1,0,team)
                    legal_moves += self.long_range_recursion(row,col,-1,0,team)
                    legal_moves += self.long_range_recursion(row,col,0,1,team)
                    legal_moves += self.long_range_recursion(row,col,0,-1,team)

                    for i in legal_moves:
                        r = i[0]
                        c = i[1]
                        if self.state[r][c] == -4 or self.state[r][c] == -5:
                            white_in_check = True

                    ##CHECK FOR KING
                    king_moves = ((row + 1, col - 1),(row + 1, col),(row + 1, col + 1),
                                (row, col - 1),(row, col + 1),
                                (row - 1, col - 1),(row - 1, col),(row - 1, col + 1),)
                    for i in king_moves:
                        if i[0] >= 0 and i[1] >= 0 and i[0] <= 7 and i[1] <= 7:
                            r = i[0]
                            c = i[1]
                            if self.state[r][c] == -6:
                                white_in_check = True

                elif self.state[row][col] == -6: ## BLACK KING
                    black_king_pos = (row, col)

                    team = -1

                    ##CHECK FOR PAWNS
                    if row + 1 <= 7:
                        if col + 1 <= 7 and self.state[row + 1][col + 1] == 1:
                            black_in_check = True
                        if col - 1 >= 0 and self.state[row + 1][col - 1] == 1:
                            black_in_check = True

                    ##CHECK FOR KNIGHTS:
                    knight_moves = ((row + 2, col + 1), (row + 2, col - 1), (row - 2, col + 1), (row - 2, col - 1), (row + 1, col + 2), (row + 1, col - 2), (row - 1, col + 2), (row - 1, col -2))
                    for i in knight_moves:
                        if i[0] >= 0 and i[1] >= 0 and i[0] <= 7 and i[1] <= 7:
                            r = i[0]
                            c = i[1]
                            if self.state[r][c] == 2:
                                black_in_check = True
                    
                    ##CHECK FOR BISHOP / QUEEN DIAGONALS
                    legal_moves = []
                    legal_moves += self.long_range_recursion(row,col,-1,-1,team)
                    legal_moves += self.long_range_recursion(row,col,-1,1,team)
                    legal_moves += self.long_range_recursion(row,col,1,-1,team)
                    legal_moves += self.long_range_recursion(row,col,1,1,team)

                    for i in legal_moves:
                        r = i[0]
                        c = i[1]
                        if self.state[r][c] == 3 or self.state[r][c] == 5:
                            black_in_check = True

                    ##CHECK FOR ROOK / QUEEN STRAIGHTS
                    legal_moves = []
                    legal_moves += self.long_range_recursion(row,col,1,0,team)
                    legal_moves += self.long_range_recursion(row,col,-1,0,team)
                    legal_moves += self.long_range_recursion(row,col,0,1,team)
                    legal_moves += self.long_range_recursion(row,col,0,-1,team)

                    for i in legal_moves:
                        r = i[0]
                        c = i[1]
                        if self.state[r][c] == 4 or self.state[r][c] == 5:
                            black_in_check = True

                    ##CHECK FOR KING
                    king_moves = ((row + 1, col - 1),(row + 1, col),(row + 1, col + 1),
                                (row, col - 1),(row, col + 1),
                                (row - 1, col - 1),(row - 1, col),(row - 1, col + 1),)
                    for i in king_moves:
                        if i[0] >= 0 and i[1] >= 0 and i[0] <= 7 and i[1] <= 7:
                            r = i[0]
                            c = i[1]
                            if self.state[r][c] == 6:
                                black_in_check = True

        if not white_in_check:
            white_king_pos = None

        if not black_in_check:
            black_king_pos = None

        return white_in_check, black_in_check, white_king_pos, black_king_pos

    def get_legal_moves(self, row, column):
        piece = self.state[row][column]
        legal_moves = []
        team = 1 if self.state[row][column] > 0 else -1
        
        if piece == 1: ##WHITE PAWN LOGIC
            pawn_moves = []
            legal_row = row - 1

            if legal_row == 0:
                pawn_moves.append((legal_row,column,2)) ## PASS OPTION TO UPGRADE TO VARIOUS PIECES
                pawn_moves.append((legal_row,column,3))
                pawn_moves.append((legal_row,column,4))
                pawn_moves.append((legal_row,column,5))
            else:
                pawn_moves.append((legal_row,column,None))

            pawn_captures = []
            if legal_row == 0:
                pawn_captures.append((legal_row, column-1,2))
                pawn_captures.append((legal_row, column-1,3))
                pawn_captures.append((legal_row, column-1,4))
                pawn_captures.append((legal_row, column-1,5))
                pawn_captures.append((legal_row, column+1,2))
                pawn_captures.append((legal_row, column+1,3))
                pawn_captures.append((legal_row, column+1,4))
                pawn_captures.append((legal_row, column+1,5))
            else:
                pawn_captures.append((legal_row, column-1,None))
                pawn_captures.append((legal_row, column+1,None))
            
            if row == 6: ## IF ON STARTING SQUARE, ALLOW TWO
                legal_row_2 = row - 2
                pawn_moves.append((legal_row_2,column,None))

            for i in pawn_moves:
                if i[0] >= 0 and i[1] >= 0 and i[0] <= 7 and i[1] <= 7:
                    if self.state[i[0]][i[1]] == 0:
                        legal_moves.append((i))
            
            for i in pawn_captures:
                if i[0] >= 0 and i[1] >= 0 and i[0] <= 7 and i[1] <= 7:
                    if self.state[i[0]][i[1]] < 0:
                        legal_moves.append((i))
        
        if piece == -1: ##BLACK PAWN LOGIC
            pawn_moves = []
            legal_row = row + 1

            if legal_row == 7:
                pawn_moves.append((legal_row,column,2))
                pawn_moves.append((legal_row,column,3))
                pawn_moves.append((legal_row,column,4))
                pawn_moves.append((legal_row,column,5))
            else:
                pawn_moves.append((legal_row,column,None))

            pawn_captures = []
            if legal_row == 7:
                pawn_captures.append((legal_row, column-1,2))
                pawn_captures.append((legal_row, column-1,3))
                pawn_captures.append((legal_row, column-1,4))
                pawn_captures.append((legal_row, column-1,5))
                pawn_captures.append((legal_row, column+1,2))
                pawn_captures.append((legal_row, column+1,3))
                pawn_captures.append((legal_row, column+1,4))
                pawn_captures.append((legal_row, column+1,5))
            else:
                pawn_captures.append((legal_row, column-1,None))
                pawn_captures.append((legal_row, column+1,None))
            
            if row == 1:
                legal_row_2 = row + 2
                pawn_moves.append((legal_row_2,column,None))

            for i in pawn_moves:
                if i[0] >= 0 and i[1] >= 0 and i[0] <= 7 and i[1] <= 7:
                    if self.state[i[0]][i[1]] == 0:
                        legal_moves.append((i))
            
            for i in pawn_captures:
                if i[0] >= 0 and i[1] >= 0 and i[0] <= 7 and i[1] <= 7:
                    if self.state[i[0]][i[1]] > 0:
                        legal_moves.append((i))

        if piece == 2 or piece == -2: ## KNIGHT LOGIC
            knight_moves = ((row + 2, column + 1), (row + 2, column - 1), (row - 2, column + 1), (row - 2, column - 1), (row + 1, column + 2), (row + 1, column - 2), (row - 1, column + 2), (row - 1, column -2))
            for i in knight_moves:
                if i[0] >= 0 and i[1] >= 0 and i[0] <= 7 and i[1] <= 7:
                    match team:
                        case 1:
                            if self.state[i[0]][i[1]] <= 0:
                                legal_moves.append((i[0],i[1],None))
                        case -1:
                            if self.state[i[0]][i[1]] >= 0:
                                legal_moves.append((i[0],i[1],None))

        if piece == 3 or piece == -3: ##BISHOP LOGIC
            legal_moves += self.long_range_recursion(row,column,-1,-1,team)
            legal_moves += self.long_range_recursion(row,column,-1,1,team)
            legal_moves += self.long_range_recursion(row,column,1,-1,team)
            legal_moves += self.long_range_recursion(row,column,1,1,team)

        if piece == 4 or piece == -4: ##ROOK LOGIC
            legal_moves += self.long_range_recursion(row,column,1,0,team)
            legal_moves += self.long_range_recursion(row,column,-1,0,team)
            legal_moves += self.long_range_recursion(row,column,0,1,team)
            legal_moves += self.long_range_recursion(row,column,0,-1,team)

        if piece == 5 or piece == -5: ##QUEEN LOGIC
            legal_moves += self.long_range_recursion(row,column,1,0,team)
            legal_moves += self.long_range_recursion(row,column,-1,0,team)
            legal_moves += self.long_range_recursion(row,column,0,1,team)
            legal_moves += self.long_range_recursion(row,column,0,-1,team)
            legal_moves += self.long_range_recursion(row,column,-1,-1,team)
            legal_moves += self.long_range_recursion(row,column,-1,1,team)
            legal_moves += self.long_range_recursion(row,column,1,-1,team)
            legal_moves += self.long_range_recursion(row,column,1,1,team)
        
        if piece == 6 or piece == -6: ## KING LOGIC
            king_moves = ((row + 1, column - 1),(row + 1, column),(row + 1, column +1),
                          (row, column - 1),(row, column +1),
                          (row - 1, column - 1),(row - 1, column),(row - 1, column + 1),)
            for i in king_moves:
                if i[0] >= 0 and i[1] >= 0 and i[0] <= 7 and i[1] <= 7:
                    match team:
                        case 1:
                            if self.state[i[0]][i[1]] <= 0:
                                legal_moves.append((i[0],i[1],None))
                        case -1:
                            if self.state[i[0]][i[1]] >= 0:
                                legal_moves.append((i[0],i[1],None))

            if piece == 6 and row == 7 and column == 4 and not self.white_king_moved:
                if not self.white_rook_h_moved and self.state[7][7] == 4:
                    if self.state[7][5] == 0 and self.state[7][6] == 0:
                        legal_moves.append((7, 6, None))

                if not self.white_rook_a_moved and self.state[7][0] == 4:
                    if self.state[7][1] == 0 and self.state[7][2] == 0 and self.state[7][3] == 0:
                        legal_moves.append((7, 2, None))

            if piece == -6 and row == 0 and column == 4 and not self.black_king_moved:
                if not self.black_rook_h_moved and self.state[0][7] == -4:
                    if self.state[0][5] == 0 and self.state[0][6] == 0:
                        legal_moves.append((0, 6, None))

                if not self.black_rook_a_moved and self.state[0][0] == -4:
                    if self.state[0][1] == 0 and self.state[0][2] == 0 and self.state[0][3] == 0:
                        legal_moves.append((0, 2, None))

        saved_board_state = [r[:] for r in self.state]
        saved_white_king_moved = self.white_king_moved
        saved_black_king_moved = self.black_king_moved
        saved_white_rook_a_moved = self.white_rook_a_moved
        saved_white_rook_h_moved = self.white_rook_h_moved
        saved_black_rook_a_moved = self.black_rook_a_moved
        saved_black_rook_h_moved = self.black_rook_h_moved

        for move in legal_moves[:]:
            self.state = [r[:] for r in saved_board_state]
            self.white_king_moved = saved_white_king_moved
            self.black_king_moved = saved_black_king_moved
            self.white_rook_a_moved = saved_white_rook_a_moved
            self.white_rook_h_moved = saved_white_rook_h_moved
            self.black_rook_a_moved = saved_black_rook_a_moved
            self.black_rook_h_moved = saved_black_rook_h_moved

            new_row = move[0]
            new_col = move[1]
            promotion_piece = move[2]

            ## EXTRA CASTLING CHECK: cannot castle out of, through, or into check
            if piece == 6 and row == 7 and column == 4 and new_row == 7 and new_col == 6:
                w_in_check, b_in_check, white_king_pos, black_king_pos = self.king_check_check()
                if w_in_check:
                    legal_moves.remove(move)
                    continue

                self.move_piece(7,4,7,5,None)
                w_in_check, b_in_check, white_king_pos, black_king_pos = self.king_check_check()
                if w_in_check:
                    legal_moves.remove(move)
                    continue

                self.state = [r[:] for r in saved_board_state]
                self.white_king_moved = saved_white_king_moved
                self.black_king_moved = saved_black_king_moved
                self.white_rook_a_moved = saved_white_rook_a_moved
                self.white_rook_h_moved = saved_white_rook_h_moved
                self.black_rook_a_moved = saved_black_rook_a_moved
                self.black_rook_h_moved = saved_black_rook_h_moved

            elif piece == 6 and row == 7 and column == 4 and new_row == 7 and new_col == 2:
                w_in_check, b_in_check, white_king_pos, black_king_pos = self.king_check_check()
                if w_in_check:
                    legal_moves.remove(move)
                    continue

                self.move_piece(7,4,7,3,None)
                w_in_check, b_in_check, white_king_pos, black_king_pos = self.king_check_check()
                if w_in_check:
                    legal_moves.remove(move)
                    continue

                self.state = [r[:] for r in saved_board_state]
                self.white_king_moved = saved_white_king_moved
                self.black_king_moved = saved_black_king_moved
                self.white_rook_a_moved = saved_white_rook_a_moved
                self.white_rook_h_moved = saved_white_rook_h_moved
                self.black_rook_a_moved = saved_black_rook_a_moved
                self.black_rook_h_moved = saved_black_rook_h_moved

            elif piece == -6 and row == 0 and column == 4 and new_row == 0 and new_col == 6:
                w_in_check, b_in_check, white_king_pos, black_king_pos = self.king_check_check()
                if b_in_check:
                    legal_moves.remove(move)
                    continue

                self.move_piece(0,4,0,5,None)
                w_in_check, b_in_check, white_king_pos, black_king_pos = self.king_check_check()
                if b_in_check:
                    legal_moves.remove(move)
                    continue

                self.state = [r[:] for r in saved_board_state]
                self.white_king_moved = saved_white_king_moved
                self.black_king_moved = saved_black_king_moved
                self.white_rook_a_moved = saved_white_rook_a_moved
                self.white_rook_h_moved = saved_white_rook_h_moved
                self.black_rook_a_moved = saved_black_rook_a_moved
                self.black_rook_h_moved = saved_black_rook_h_moved

            elif piece == -6 and row == 0 and column == 4 and new_row == 0 and new_col == 2:
                w_in_check, b_in_check, white_king_pos, black_king_pos = self.king_check_check()
                if b_in_check:
                    legal_moves.remove(move)
                    continue

                self.move_piece(0,4,0,3,None)
                w_in_check, b_in_check, white_king_pos, black_king_pos = self.king_check_check()
                if b_in_check:
                    legal_moves.remove(move)
                    continue

                self.state = [r[:] for r in saved_board_state]
                self.white_king_moved = saved_white_king_moved
                self.black_king_moved = saved_black_king_moved
                self.white_rook_a_moved = saved_white_rook_a_moved
                self.white_rook_h_moved = saved_white_rook_h_moved
                self.black_rook_a_moved = saved_black_rook_a_moved
                self.black_rook_h_moved = saved_black_rook_h_moved
            
            self.move_piece(row,column,new_row,new_col,promotion_piece)
            w_in_check, b_in_check, white_king_pos, black_king_pos = self.king_check_check()

            if team == 1:
                if w_in_check:
                    legal_moves.remove(move)

            if team == -1:
                if b_in_check:
                    legal_moves.remove(move)

        self.state = saved_board_state
        self.white_king_moved = saved_white_king_moved
        self.black_king_moved = saved_black_king_moved
        self.white_rook_a_moved = saved_white_rook_a_moved
        self.white_rook_h_moved = saved_white_rook_h_moved
        self.black_rook_a_moved = saved_black_rook_a_moved
        self.black_rook_h_moved = saved_black_rook_h_moved

        return legal_moves
    
    def get_all_legal_moves(self, team):
        all_legal_moves = []
        x = 0
        for r in self.state:
            y = 0
            for c in r:
                if c * team > 0:
                    piece_moves = self.get_legal_moves(x, y)
                    for move in piece_moves:
                        all_legal_moves.append((x, y, move[0], move[1], move[2]))
                y += 1
            x += 1
        return all_legal_moves
    
    def check_for_win(self, team):
        all_legal_moves = self.get_all_legal_moves(team)
        if len(all_legal_moves) == 0:
            white_in_check, black_in_check, white_king_pos, black_king_pos = self.king_check_check()
            match team:
                case 1:
                    if white_in_check:
                        return -1 ## WHITE CHECKMATE
                    else:
                        return 0 ## STALEMATE
                case -1:
                    if black_in_check:
                        return 1 ## BLACK CHECKMATE
                    else:
                        return 0
                        
import pygame
from pathlib import Path
from board import Board
from evaluate import Evaluate
from search import Search

BASE_DIR = Path(__file__).resolve().parent

class Game:
    def __init__(self):
        
        pygame.init() 

        self.board = Board()
        self.evaluate = Evaluate()
        self.search = Search()

        self.screen_size = 900
        self.screen = pygame.display.set_mode((self.screen_size, self.screen_size))
        pygame.display.set_caption("board")
        self.font = pygame.font.SysFont(None, 36)
        self.clock = pygame.time.Clock()
        self.running = True
        

        self.board_size = len(self.board.state)
        self.board_pixel_size = int(self.screen_size * 0.76)
        self.square_size = self.board_pixel_size // self.board_size
        self.board_pixel_size = self.square_size * self.board_size
        self.board_left = (self.screen_size - self.board_pixel_size) // 2
        self.board_top = (self.screen_size - self.board_pixel_size) // 2
        self.piece_size = int(self.square_size * 0.80)

        self.selected_square = None
        self.current_row = None
        self.current_col = None
        self.active_team = 1

        self.white_king_check_pos = None
        self.black_king_check_pos = None

        self.promotion_possible = False
        self.promotion_rects = {}
        self.matched_moves = []

        self.white_win = False
        self.black_win = False
        self.stalemate = False

        self.piece_images = {
            1: self.load_piece_image("w_pawn_png_1024px.png"),
            2: self.load_piece_image("w_knight_png_1024px.png"),
            3: self.load_piece_image("w_bishop_png_1024px.png"),
            4: self.load_piece_image("w_rook_png_1024px.png"),
            5: self.load_piece_image("w_queen_png_1024px.png"),
            6: self.load_piece_image("w_king_png_1024px.png"),
            -1: self.load_piece_image("b_pawn_png_1024px.png"),
            -2: self.load_piece_image("b_knight_png_1024px.png"),
            -3: self.load_piece_image("b_bishop_png_1024px.png"),
            -4: self.load_piece_image("b_rook_png_1024px.png"),
            -5: self.load_piece_image("b_queen_png_1024px.png"),
            -6: self.load_piece_image("b_king_png_1024px.png"),
        }

    def load_piece_image(self, filename):
        image = pygame.image.load(BASE_DIR / filename)
        return pygame.transform.smoothscale(image, (self.piece_size, self.piece_size))

    def check_click(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            
            ## HANDLE CLICKS AND USER INPUT ON WHITE TURN VVVV

            if self.active_team == 1: 
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if self.promotion_possible:
                        for piece, rect in self.promotion_rects.items():
                            if rect.collidepoint(event.pos):
                                for move in self.matched_moves:
                                    if piece == move[2]:
                                        self.board.move_piece(self.selected_square[0], self.selected_square[1], move[0], move[1], move[2])
                                        self.selected_square = None
                                        self.current_row = None
                                        self.current_col = None
                                        self.active_team *= -1
                                        match self.board.check_for_win(self.active_team):
                                            case 1:
                                                self.white_win = True
                                            case 0:
                                                self.stalemate = True
                                            case -1:
                                                self.black_win = True
                                        self.promotion_possible = False
                                        self.matched_moves = []
                                        return  
                        return

                    mouse_x, mouse_y = event.pos

                    board_x = mouse_x - self.board_left
                    board_y = mouse_y - self.board_top

                    if 0 <= board_x < self.board_size * self.square_size and 0 <= board_y < self.board_size * self.square_size:
                        col = board_x // self.square_size
                        row = board_y // self.square_size

                        piece = self.board.state[row][col]

                        if self.selected_square is not None:
                            moves = self.board.get_legal_moves(self.selected_square[0], self.selected_square[1])
                            legal_clicked_square = False
                            
                            for move in moves:
                                if row == move[0] and col == move[1]:
                                    legal_clicked_square = True
                                    break

                            if legal_clicked_square: 
                                    matched_moves = []
                                    for move in moves:
                                        if row == move[0] and col == move[1]:
                                            matched_moves.append(move)
                                            
                                    if len(matched_moves) > 1:
                                        self.promotion_possible = True
                                        self.matched_moves = matched_moves
                                        return

                                    else:
                                        move = matched_moves[0]
                                        self.board.move_piece(self.selected_square[0], self.selected_square[1], move[0], move[1], move[2])
                                        self.selected_square = None
                                        self.current_row = None
                                        self.current_col = None

                                        self.active_team *= -1
                                        match self.board.check_for_win(self.active_team):
                                            case 1:
                                                self.white_win = True
                                            case 0:
                                                self.stalemate = True
                                            case -1:
                                                self.black_win = True

                                        white_in_check, black_in_check, white_king_pos, black_king_pos = self.board.king_check_check()

                                        self.white_king_check_pos = white_king_pos
                                        self.black_king_check_pos = black_king_pos


                                        continue

                            selected_piece = self.board.state[self.selected_square[0]][self.selected_square[1]]
                            selected_piece_team = 1 if selected_piece > 0 else -1

                            if piece != 0:
                                clicked_piece_team = 1 if piece > 0 else -1

                                if clicked_piece_team == self.active_team:
                                    if clicked_piece_team == selected_piece_team:
                                        self.current_row = row
                                        self.current_col = col
                                        self.selected_square = (row, col)
                                    else:
                                        self.selected_square = None
                                        self.current_row = None
                                        self.current_col = None
                                else:
                                    self.selected_square = None
                                    self.current_row = None
                                    self.current_col = None
                            else:
                                self.selected_square = None
                                self.current_row = None
                                self.current_col = None

                        else:
                            if piece != 0:          
                                piece_team = 1 if piece > 0 else -1
                                if piece_team == self.active_team:
                                    self.current_row = row
                                    self.current_col = col
                                    self.selected_square = (row, col)

            else: ## CPU TAKES TURN
                best_eval, best_move = self.search.minmax(self.board, -1, 2, -99999, 99999)
                print(best_move)

                if best_move is not None:
                    self.board.move_piece(best_move[0], best_move[1], best_move[2], best_move[3], best_move[4])
                    self.active_team = 1

                    match self.board.check_for_win(self.active_team):
                        case 1:
                            self.white_win = True
                        case 0:
                            self.stalemate = True
                        case -1:
                            self.black_win = True

        white_in_check, black_in_check, white_king_pos, black_king_pos = self.board.king_check_check()

        self.white_king_check_pos = white_king_pos
        self.black_king_check_pos = black_king_pos
                            
    def draw(self):
        self.screen.fill("#000000")
        self.promotion_rects = {}

        for row in range(self.board_size):
            for col in range(self.board_size):
                x = col * self.square_size + self.board_left
                y = row * self.square_size + self.board_top

                color = "#061F0B" if (row + col) % 2 else "#42AB52"
                pygame.draw.rect(self.screen, color, (x, y, self.square_size, self.square_size))

                if self.white_king_check_pos == (row, col) or self.black_king_check_pos == (row, col):
                    pygame.draw.rect(self.screen, "red", (x, y, self.square_size, self.square_size), 4)

                if self.selected_square == (row, col):
                    pygame.draw.rect(self.screen, "#D95A88", (x, y, self.square_size, self.square_size), 4)

                piece = self.board.state[row][col]
                if piece != 0 and piece != 7 and piece != -7:
                    self.screen.blit(self.piece_images[piece], (x + self.square_size * 0.1, y + self.square_size * 0.1))

        if self.promotion_possible:
            pygame.draw.rect(
                self.screen,
                'white',
                (self.screen_size / 4, self.screen_size / 2.7, self.screen_size / 2, self.screen_size / 4)
            )

            knight_rect = pygame.Rect(145, self.screen_size / 2.7 + 40, self.piece_size, self.piece_size)
            bishop_rect = pygame.Rect(202, self.screen_size / 2.7 + 40, self.piece_size, self.piece_size)
            rook_rect = pygame.Rect(260, self.screen_size / 2.7 + 40, self.piece_size, self.piece_size)
            queen_rect = pygame.Rect(317, self.screen_size / 2.7 + 40, self.piece_size, self.piece_size)

            self.promotion_rects = {
                2: knight_rect,
                3: bishop_rect,
                4: rook_rect,
                5: queen_rect
            }

            self.screen.blit(self.piece_images[2], (knight_rect.x, knight_rect.y))
            self.screen.blit(self.piece_images[3], (bishop_rect.x, bishop_rect.y))
            self.screen.blit(self.piece_images[4], (rook_rect.x, rook_rect.y))
            self.screen.blit(self.piece_images[5], (queen_rect.x, queen_rect.y))

        result_text = None
        if self.white_win:
            result_text = "White Wins"
        elif self.black_win:
            result_text = "Black Wins"
        elif self.stalemate:
            result_text = "Stalemate"

        if result_text is not None:
            pygame.draw.rect(
                self.screen,
                "white",
                (self.screen_size / 4, 15, self.screen_size / 2, 50)
            )
            pygame.draw.rect(
                self.screen,
                "black",
                (self.screen_size / 4, 15, self.screen_size / 2, 50),
                2
            )

            text_surface = self.font.render(result_text, True, "black")
            text_rect = text_surface.get_rect(center=(self.screen_size / 2, 40))
            self.screen.blit(text_surface, text_rect)

    def run(self):
        while self.running:
            self.check_click()
            self.draw()
            pygame.display.flip()
            self.clock.tick(60)
        pygame.quit()

if __name__ == "__main__":
    game = Game()
    game.run()

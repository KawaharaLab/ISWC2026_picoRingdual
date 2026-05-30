import math
import pygame
import os
from paths import ICONS_DIR, DEFAULT_VIDEO
from youtube_mode import YoutubeMode

class AppState:
    MENU = "MENU"
    YOUTUBE = "YOUTUBE"

class AppAction:
    NONE = "NONE"
    LAUNCH_PICO_SNIPER = "LAUNCH_PICO_SNIPER"

class AppStateManager:
    def __init__(self, screen, input_manager):
        self.screen = screen
        self.input_manager = input_manager
        self.width, self.height = screen.get_size()

        pygame.font.init()
        self.font_large = pygame.font.SysFont("Arial", 42)
        self.font_small = pygame.font.SysFont("Arial", 24)
        self.font_tiny = pygame.font.SysFont("Arial", 18)

        self.current_state = AppState.YOUTUBE
        self.current_action = AppAction.NONE

        # --- アイコン素材の読み込みとリサイズ ---
        icon_size = 116
        def load_icon(path):
            try:
                img = pygame.image.load(path).convert_alpha()
                return pygame.transform.smoothscale(img, (icon_size, icon_size))
            except Exception as e:
                print(f"Error loading icon {path}: {e}")
                # 代わりの空サーフェスを返す
                surf = pygame.Surface((icon_size, icon_size))
                surf.fill((50, 50, 50))
                return surf

        # メニュー項目の定義（画像を割り当て）
        self.menu_items = [
            {"id": "PDF", "name": "PDF", "color": (255, 160, 60), "img": load_icon(f"{ICONS_DIR}/pdf_icon.png")},
            {"id": "YOUTUBE", "name": "Video", "color": (255, 70, 70), "img": load_icon(f"{ICONS_DIR}/movie_icon.png")},
            {"id": "MAP", "name": "Map", "color": (60, 210, 210), "img": load_icon(f"{ICONS_DIR}/map_icon.png")},
            {"id": "PICO_SNIPER", "name": "Pico Sniper", "color": (120, 255, 120), "img": load_icon(f"{ICONS_DIR}/sniper_icon.png")},
        ]
        
        self.menu_index = 0
        self.menu_scroll_accum = 0.0
        self.menu_anim_tick = 0.0
        self.menu_scroll_threshold = 0.1

        self.last_input_time = 0  # 追加：最後に操作した時刻を記録
        self.input_cooldown = 300  # 追加：クールダウン時間（ミリ秒）

        self.yt_mode = YoutubeMode((self.width, self.height), DEFAULT_VIDEO)

    def pop_action(self):
        action = self.current_action
        self.current_action = AppAction.NONE
        return action

    def open_menu(self):
        if self.current_state != AppState.MENU:
            self.current_state = AppState.MENU
            self.menu_scroll_accum = 0.0
            print("DEBUG: MENU opened by gesture")

    def update(self):
        hand = self.input_manager.get_active_hand_data()
        if self.current_state == AppState.YOUTUBE:
            self._update_youtube(hand)
        elif self.current_state == AppState.MENU:
            self._update_menu(hand)

    def draw(self):
        self.screen.fill((0, 0, 0))
        if self.current_state == AppState.YOUTUBE:
            self._draw_youtube()
        elif self.current_state == AppState.MENU:
            self._draw_menu()
        self._draw_debug_info()

    def _update_youtube(self, hand):
        current_time = pygame.time.get_ticks()
        
        # クールダウン判定（メニューと同様）
        if current_time - self.last_input_time < self.input_cooldown:
            return

        # クリック（再生/停止）
        if hand.is_clicked:
            self.yt_mode.toggle_play()
            self.last_input_time = current_time # 操作したのでタイマー更新

        # シーク（送り・戻し）
        # 回転量が一定以上（0.5）の場合のみ反応させる
        if abs(hand.tb_rotation_y) > 0.5:
            self.yt_mode.seek(-hand.tb_rotation_y)
            self.last_input_time = current_time # 操作したのでタイマー更新
        
        self.yt_mode.update()

    def _draw_youtube(self):
        self.yt_mode.draw(self.screen)
        self._draw_hint("Gesture: open MENU")

    def _update_menu(self, hand):
        current_time = pygame.time.get_ticks()
        self.menu_anim_tick += 0.07
        
        # クールダウン中（0.5秒以内）なら蓄積もリセットして何もしない
        if current_time - self.last_input_time < self.input_cooldown:
            self.menu_scroll_accum = 0.0
            return

        self.menu_scroll_accum += hand.tb_rotation_x

        if self.menu_scroll_accum > self.menu_scroll_threshold:
            self.menu_index = min(self.menu_index + 1, len(self.menu_items) - 1)
            self.menu_scroll_accum = 0.0
            self.last_input_time = current_time  # 操作時刻を更新
        elif self.menu_scroll_accum < -self.menu_scroll_threshold:
            self.menu_index = max(self.menu_index - 1, 0)
            self.menu_scroll_accum = 0.0
            self.last_input_time = current_time  # 操作時刻を更新

        if hand.is_clicked:
            # クリックにもクールダウンを適用する場合
            selected = self.menu_items[self.menu_index]["id"]
            self.last_input_time = current_time # 操作時刻を更新
            if selected == "YOUTUBE":
                self.current_state = AppState.YOUTUBE
            elif selected == "PICO_SNIPER":
                self.current_action = AppAction.LAUNCH_PICO_SNIPER
            else:
                print(f"DEBUG: {selected} is icon-only (not implemented).")

    def _draw_menu(self):
        float_y = math.sin(self.menu_anim_tick) * 8.0
        icon_size = 116
        spacing = 56
        total_w = len(self.menu_items) * icon_size + (len(self.menu_items) - 1) * spacing
        start_x = (self.width - total_w) // 2
        y = self.height // 2 - icon_size // 2 + float_y

        for i, item in enumerate(self.menu_items):
            focused = i == self.menu_index
            x = start_x + i * (icon_size + spacing)
            color = item["color"]

            if focused:
                # 選択中の光彩エフェクト
                glow = pygame.Surface((icon_size + 30, icon_size + 30), pygame.SRCALPHA)
                pygame.draw.rect(glow, (*color, 70), (0, 0, icon_size + 30, icon_size + 30), border_radius=24)
                self.screen.blit(glow, (x - 15, int(y) - 15))

            # アイコン画像を表示（背景の黒枠は省略し、画像そのものを表示）
            self.screen.blit(item["img"], (x, int(y)))

            # 選択中の枠線表示
            if focused:
                pygame.draw.rect(self.screen, color, (x, int(y), icon_size, icon_size), width=3, border_radius=18)

            label = self.font_tiny.render(item["name"], True, (255, 255, 255))
            self.screen.blit(label, (x + (icon_size - label.get_width()) // 2, int(y) + icon_size + 14))

        # title = self.font_large.render("Menu", True, (240, 240, 240))
        # self.screen.blit(title, ((self.width - title.get_width()) // 2, 90))
        # self._draw_hint("Horizontal scroll: select / Click: open")

    def _draw_hint(self, text):
        guide = self.font_tiny.render(text, True, (255, 255, 255))
        bg = pygame.Surface((guide.get_width() + 20, 30), pygame.SRCALPHA)
        bg.fill((0, 0, 0, 140))
        x = self.width // 2 - bg.get_width() // 2
        y = self.height - 50
        self.screen.blit(bg, (x, y))
        self.screen.blit(guide, (self.width // 2 - guide.get_width() // 2, y + 5))

    def _draw_debug_info(self):
        hand_id = self.input_manager.get_active_hand_id()
        hand = self.input_manager.get_active_hand_data()
        txt = f"Hand: {hand_id}"
        dbg = self.font_tiny.render(txt, True, (120, 255, 120))
        self.screen.blit(dbg, (10, 10))

        # scroll = f"TB x={getattr(hand, 'tb_rotation_x', 0.0):.1f} y={getattr(hand, 'tb_rotation_y', 0.0):.1f}"
        # dbg2 = self.font_tiny.render(scroll, True, (220, 220, 100))
        # self.screen.blit(dbg2, (10, 30))

    def cleanup(self):
        if self.yt_mode:
            self.yt_mode.release()
        print("DEBUG: AppStateManager cleaned up.")
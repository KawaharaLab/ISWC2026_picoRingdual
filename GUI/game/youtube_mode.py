import pygame
import cv2
import numpy as np
import os
from paths import DEFAULT_VIDEO

class YoutubeMode:
    def __init__(self, screen_size, video_path=DEFAULT_VIDEO):
        self.screen_width, self.screen_height = screen_size
        self.video_path = video_path
        self.is_playing = True
        
        self.frames = [] # List of pre-scaled pygame surfaces
        self.current_frame_index = 0
        self.video_fps = 30
        # 実時間に合わせた再生。1.0でメタデータfps相当。さらに遅くするなら 0.85 など。
        self.playback_speed = 1.0
        self._play_accum = 0.0
        self._last_update_ticks = None

        # UI Feedback
        self.overlay_timer = 0
        self.overlay_type = None

        self._load_video()

    def _load_video(self):
        if not os.path.exists(self.video_path):
            print(f"DEBUG: Video file not found: {self.video_path}")
            return
            
        cap = cv2.VideoCapture(self.video_path)
        if not cap.isOpened():
            print(f"DEBUG: Failed to open video: {self.video_path}")
            return
            
        self.video_fps = cap.get(cv2.CAP_PROP_FPS)
        if self.video_fps <= 0: self.video_fps = 30
        
        print(f"DEBUG: Loading video to RAM: {self.video_path}...")
        self.frames = []
        
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            # BGR to RGB
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            frame = np.transpose(frame, (1, 0, 2))
            
            orig_w, orig_h = frame.shape[0], frame.shape[1]
            ratio = min(self.screen_width / orig_w, self.screen_height / orig_h)
            new_size = (int(orig_w * ratio), int(orig_h * ratio))
            
            # Create surface and scale immediately
            temp_surface = pygame.surfarray.make_surface(frame)
            scaled_surface = pygame.transform.scale(temp_surface, new_size)
            self.frames.append(scaled_surface)
            
        cap.release()
        print(f"DEBUG: Cached {len(self.frames)} frames in RAM.")

    def toggle_play(self):
        self.is_playing = not self.is_playing
        self.overlay_type = 'PLAY' if self.is_playing else 'PAUSE'
        self.overlay_timer = 45
        print(f"DEBUG: Video {'Playing' if self.is_playing else 'Paused'}")

    def seek(self, amount):
        """ Seek by index based on amount """
        if not self.frames: return
        
        # 1.0 amount approx 5 frames
        shift = int(amount * 1.0)
        self.current_frame_index += shift
        
        # Clamp and Loop
        if self.current_frame_index >= len(self.frames):
            self.current_frame_index = 0
        elif self.current_frame_index < 0:
            self.current_frame_index = len(self.frames) - 1
            
        # UI Feedback
        self.overlay_type = 'FORWARD' if amount > 0 else 'BACKWARD'
        self.overlay_timer = 30

    def update(self, force_read=False, dt=None):
        if self.overlay_timer > 0:
            self.overlay_timer -= 1

        if not self.frames:
            return

        if dt is None:
            now = pygame.time.get_ticks()
            if self._last_update_ticks is None:
                self._last_update_ticks = now
                dt = 0.0
            else:
                dt = (now - self._last_update_ticks) / 1000.0
                self._last_update_ticks = now
        dt = min(max(dt, 0.0), 0.25)

        if self.is_playing:
            self._play_accum += dt * self.video_fps * self.playback_speed
            while self._play_accum >= 1.0:
                self._play_accum -= 1.0
                self.current_frame_index += 1
                if self.current_frame_index >= len(self.frames):
                    self.current_frame_index = 0

    def draw(self, screen):
        if self.frames and self.current_frame_index < len(self.frames):
            surface = self.frames[self.current_frame_index]
            rect = surface.get_rect(center=(self.screen_width//2, self.screen_height//2))
            screen.blit(surface, rect)
            
            if self.overlay_timer > 0:
                self._draw_overlay(screen)
        else:
            font = pygame.font.SysFont('Arial', 32)
            msg = font.render(f"Video Error or Empty: {self.video_path}", True, (255, 0, 0))
            screen.blit(msg, (200, 250))

    def _draw_overlay(self, screen):
        cx, cy = self.screen_width // 2, self.screen_height // 2
        # Alpha transparency
        alpha = min(255, self.overlay_timer * 10)
        s = pygame.Surface((120, 120), pygame.SRCALPHA)
        color = (255, 255, 255, alpha)
        
        # Semi-transparent circle background
        pygame.draw.circle(s, (0, 0, 0, alpha // 2), (60, 60), 50)

        if self.overlay_type == 'PLAY':
            pygame.draw.polygon(s, color, [(45, 40), (45, 80), (85, 60)])
        elif self.overlay_type == 'PAUSE':
            pygame.draw.rect(s, color, (40, 40, 15, 40))
            pygame.draw.rect(s, color, (65, 40, 15, 40))
        elif self.overlay_type == 'FORWARD':
            pygame.draw.polygon(s, color, [(30, 40), (30, 80), (60, 60)])
            pygame.draw.polygon(s, color, [(60, 40), (60, 80), (90, 60)])
        elif self.overlay_type == 'BACKWARD':
            pygame.draw.polygon(s, color, [(90, 40), (90, 80), (60, 60)])
            pygame.draw.polygon(s, color, [(60, 40), (60, 80), (30, 60)])

        screen.blit(s, (cx - 60, cy - 60))

    def release(self):
        self.frames = []
        print("DEBUG: YoutubeMode RAM released.")
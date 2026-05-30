# VR sniper mini-game. Uses mgllib derived from pyvr-example:
# https://github.com/DaFluffyPotato/pyvr-example  (see credits.py)
import sys
import time
import math
import random
import noise
import pygame
from OpenGL import GL
import glm
import numpy as np
import numpy as np
import moderngl
import struct

from mgllib.xrwin import XRWindow
from mgllib.mgl import MGL
from mgllib.elements import ElementSingleton, elems
from mgllib.mat3d import prep_mat
from mgllib.model.obj import OBJ
from mgllib.camera import Camera
from mgllib.player_body import PlayerBody
from mgllib.world.world import World, BLOCK_SCALE
from mgllib.world.decor import Decor
from mgllib.skybox import Skybox
from mgllib.npc import NPC
from mgllib.sound import Sounds
from mgllib.hud import HUD

from pygame.locals import *

from serial_input import InputManager

class SniperHUD(ElementSingleton):
    def __init__(self, dimensions):
        super().__init__(custom_id='HUD')
        self.dimensions = dimensions
        self.ctx = self.e['MGL'].ctx
        self.program = self.e['MGL'].program('data/shaders/quad.vert', 'data/shaders/hud_scope.frag')
        
        self.surface = pygame.Surface(dimensions, pygame.SRCALPHA)
        self.texture = self.ctx.texture(dimensions, 4)
        
        self.quad_buffer = self.ctx.buffer(data=np.array([
            -1.0, 1.0, 0.0, 1.0,  # (x, y, u, v) の 'v' の値を 0.0 から 1.0 に変更
            -1.0, -1.0, 0.0, 0.0, # (x, y, u, v) の 'v' の値を 1.0 から 0.0 に変更
            1.0, 1.0, 1.0, 1.0,   # (x, y, u, v) の 'v' の値を 0.0 から 1.0 に変更
            1.0, -1.0, 1.0, 0.0,  # (x, y, u, v) の 'v' の値を 1.0 から 0.0 に変更
        ], dtype='f4'))
        self.vao = self.ctx.vertex_array(self.program, [(self.quad_buffer, '2f 2f', 'vert', 'texcoord')])
        self.font = pygame.font.Font('data/rubik_medium.ttf', size=32)

    def clear(self):
        self.surface.fill((0, 0, 0, 0))

    def add_text(self, text, pos, color=(255, 255, 255)):
        txt_surf = self.font.render(text, True, color)
        self.surface.blit(txt_surf, pos)

    def draw_scope(self):
        w, h = self.dimensions
        cx, cy = w // 2, h // 2
        radius = 160 
        pygame.draw.circle(self.surface, (0, 0, 0, 255), (cx, cy), radius, 5)
        pygame.draw.line(self.surface, (0, 0, 0, 200), (cx - radius, cy), (cx + radius, cy), 2)
        pygame.draw.line(self.surface, (0, 0, 0, 200), (cx, cy - radius), (cx, cy + radius), 2)

    def draw_hit_marker(self):
        w, h = self.dimensions
        cx, cy = w // 2, h // 2
        size = 20
        pygame.draw.line(self.surface, (255, 50, 50, 200), (cx - size, cy - size), (cx + size, cy + size), 3)
        pygame.draw.line(self.surface, (255, 50, 50, 200), (cx + size, cy - size), (cx - size, cy + size), 3)

    def update_texture(self):
        data = pygame.image.tobytes(self.surface, 'RGBA', True)
        self.texture.write(data)

    def render(self, is_zoomed=False, show_hit=False, scope_tex=None):
        if is_zoomed:
            self.draw_scope()
        if show_hit:
            self.draw_hit_marker()
        self.update_texture()
        
        self.texture.use(0)
        if scope_tex:
            scope_tex.use(1)
            
        self.program['hud_tex'] = 0
        self.program['scope_tex'] = 1
        self.program['is_zoomed'] = is_zoomed
        self.program['aspect'] = self.dimensions[0] / self.dimensions[1]
        
        self.ctx.screen.depth_mask = False
        self.vao.render(mode=moderngl.TRIANGLE_STRIP)
        self.ctx.screen.depth_mask = True

    def flash(self):
        # mgllib内部から呼ばれるダミーメソッド
        # 将来的には画面を赤く光らせるなどの処理を入れてもOK
        pass

class PicoSniper(ElementSingleton):
    def __init__(self):
        super().__init__(custom_id='Demo')
        self.window = XRWindow(self, (1200, 800))
        self.start_time = time.time()
        pygame.init()
        self.font = pygame.font.Font('data/rubik_medium.ttf', size=32)
        
        self.zoom_indices = [70, 20, 5]
        self.zoom_idx = 0
        self.reloading = False
        self.reload_timer = 0
        self.menu_open = False
        self.recoil = glm.vec3(0)
        self.battery_life = "600h"
        self.max_ammo = 4
        self.ammo = self.max_ammo
        
        self.aim_yaw = 0
        self.aim_pitch = 0
        self.events = []
        self.shoot_visual_timer = 0
        self.hit_marker_timer = 0
        self.right_hold_reload_seconds = 1.0
        self.right_hold_start_time = None
        self.right_hold_reload_fired = False
        self.initial_view_reset_done = False
        
        # 【デバッグ用】何フレーム分のログを出すかのカウンター
        self.debug_frames_left = 0

        self.is_ads = False       # 構えているかどうか
        self.ads_progress = 0.0   # 0.0(腰だめ) ～ 1.0(完全に覗いている)
        self.ads_speed = 10.0     # 構える速度（大きいほど速い）

        # ポートを両方指定して初期化
        self.input_mgr = InputManager(
            port_right='/dev/cu.usbmodem11101', 
            port_left='/dev/cu.usbmodem11201'
        )

    @property
    def watch_text(self):
        return str(self.score)

    def init_mgl(self):

        self.mgl = MGL()
        self.sounds = Sounds('data/sfx')
        
        self.main_shader = self.mgl.program('data/shaders/default.vert', 'data/shaders/default.frag')
        self.npc_shader = self.mgl.program('data/shaders/npc.vert', 'data/shaders/npc.frag')
        self.tracer_shader = self.mgl.program('data/shaders/default.vert', 'data/shaders/tracer.frag')
        self.no_norm_shader = self.mgl.program('data/shaders/no_norm.vert', 'data/shaders/no_norm.frag')
        self.decor_shader = self.mgl.program('data/shaders/decor.vert', 'data/shaders/default.frag')
        
        self.hand_obj = OBJ('data/models/hand/hand.obj', self.main_shader, centered=True)
        self.watch_obj = OBJ('data/models/watch/watch.obj', self.main_shader)
        self.head_res = OBJ('data/models/head/head.obj', self.npc_shader)
        self.body_res = OBJ('data/models/body/body.obj', self.npc_shader)
        self.helmet_res = OBJ('data/models/helmet/helmet.obj', self.main_shader)
        self.m4_res = OBJ('data/models/m4/m4.obj', self.main_shader, centered=False)
        self.m4_mag_res = OBJ('data/models/m4/mag.obj', self.main_shader, centered=False)
        self.m4_rack_res = OBJ('data/models/m4/rack.obj', self.main_shader, centered=False)
        self.tracer_res = OBJ('data/models/tracer/tracer.obj', self.tracer_shader, centered=False, simple=True)

        # --- 2. シェーダーが揃ってから、OBJモデルをロードする ---
        # 1. 1x1ピクセルの白いテクスチャを自作する (Macのエラー対策 & 床テクスチャ混入対策)
        green_data = b'\x78\xb4\x78\xff' 
        self.balloon_color_tex = self.mgl.ctx.texture((1, 1), 4, green_data)
        self.balloon_color_tex.filter = (moderngl.NEAREST, moderngl.NEAREST)
        self.balloon_model = OBJ('data/models/balloon/Balloon.obj', self.main_shader, centered=True)
        # ------------------------------------------------
        
        from mgllib.model.polygon import Polygon, TETRAHEDRON
        self.spark_res = Polygon(TETRAHEDRON, self.mgl.program('data/shaders/polygon.vert', 'data/shaders/polygon.frag'))

        self.world = World(self.main_shader)
        self.hud = SniperHUD((1200, 800))
        self.skybox = Skybox('data/textures/skybox', self.mgl.program('data/shaders/skybox.vert', 'data/shaders/skybox.frag'))
        
        self.scope_tex = self.mgl.ctx.texture((1200, 800), 4)
        self.scope_depth = self.mgl.ctx.depth_renderbuffer((1200, 800))
        #self.scope_depth = self.mgl.ctx.depth_texture((1200, 800))
        self.scope_fbo = self.mgl.ctx.framebuffer(self.scope_tex, self.scope_depth)
        
        for x in range(100):
            for z in range(100):
                for y in range(3):
                    self.world.add_block('grass' if y == 2 else 'dirt', (x - 50, y - 3, z - 50), rebuild=False)
            
        self.world.rebuild()
        self.world.gen_navmesh((0, 0, 0), scan_range=20)
        
        self.mgl.ctx.blend_func = moderngl.SRC_ALPHA, moderngl.ONE_MINUS_SRC_ALPHA
        
        self.hand_entity = self.hand_obj.new_entity()
        self.hand_entity.transform.scale = [0.045, 0.045, 0.045]
        
        self.player = PlayerBody()
        # 自前の座標変数を作成 (初期位置: x=0, y=0, z=5)
        self.logical_pos = glm.vec3(0, 0, 5) 
        self.player.world_pos.pos = [0, 0, 5]

        self.player.world_pos.pos = [0, 0, 5]
        self.npcs = []
        self.score = 0
        self.particles = []
        self.tracers = []

        self.move_velocity = glm.vec3(0, 0, 0) # 現在の速度ベクトル
        self.move_accel = 600.0                 # m/s^2 相当の加速度
        self.move_max_speed = 600             # 最大移動速度 (m/s)
        self.move_friction = 2.0              # 減速係数 (1/s), 大きいほど早く止まる

        # 仰角制限（±20度）
        self.max_pitch = math.radians(20.0)
        self.min_pitch = math.radians(-20.0)
        # 前後移動は初期向き（-Z）のレール上のみ（照準を動かしても位置が戻らない）
        self.move_rail_forward = glm.vec3(0, 0, -1)
        self.move_anchor = glm.vec3(self.logical_pos)
        self.move_rail_distance = 0.0
        self.move_fwd_min = -5.0
        self.move_fwd_max = 28.0

    def _get_forward_right(self):
        forward = glm.vec3(math.sin(self.aim_yaw), 0, math.cos(self.aim_yaw) * -1)
        right = glm.cross(forward, glm.vec3(0, 1, 0))
        return forward, right

    def _clamp_aim_pitch(self):
        self.aim_pitch = max(self.min_pitch, min(self.max_pitch, self.aim_pitch))

    def _clamped_visual_pitch(self):
        return max(self.min_pitch, min(self.max_pitch, self.aim_pitch + self.recoil.y))

    def _add_forward_impulse(self, direction_sign, dt):
        power = self.move_accel * (1.0 - self.ads_progress * 0.5)
        self.move_velocity += self.move_rail_forward * direction_sign * power * dt

    def _integrate_forward_movement(self, dt):
        rail = self.move_rail_forward
        fwd_speed = glm.dot(self.move_velocity, rail)
        if abs(fwd_speed) > self.move_max_speed:
            fwd_speed = math.copysign(self.move_max_speed, fwd_speed)

        self.move_rail_distance += fwd_speed * dt
        self.move_rail_distance = max(self.move_fwd_min, min(self.move_fwd_max, self.move_rail_distance))
        self.logical_pos = self.move_anchor + rail * self.move_rail_distance

        fwd_speed *= math.exp(-self.move_friction * dt)
        self.move_velocity = rail * fwd_speed

    def _spawn_npc_in_front(self):
        """レール正面（初期向き -Z）の手前に NPC をまとめて出す"""
        forward = self.move_rail_forward
        right = glm.cross(forward, glm.vec3(0, 1, 0))
        dist = random.uniform(4.0, 15.0)
        lateral = random.uniform(-10.0, 10.0)
        spawn = self.logical_pos + forward * dist + right * lateral
        spawn.y = 0.0
        return (spawn.x, 0, spawn.z)

    def handle_sniper_inputs(self):
        dt = self.window.dt
        keys = pygame.key.get_pressed()

        for event in self.events:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_e:
                    self.is_ads = not self.is_ads
                    self.zoom_idx = 1 if self.is_ads else 0
                elif event.key == pygame.K_f:
                    self.shoot()
                elif event.key == pygame.K_r:
                    self.start_reload()

        if self.menu_open: return

        # キーボード移動: 前後のみ
        if keys[pygame.K_w]:
            self._add_forward_impulse(1.0, dt)
        if keys[pygame.K_s]:
            self._add_forward_impulse(-1.0, dt)

    def start_reload(self):
        if not self.reloading and self.ammo < self.max_ammo:
            self.reloading = True
            self.reload_timer = 2.0
            self.sounds.play('reload', volume=1.0)
            self.ammo = self.max_ammo

    def shoot(self):
        if self.reloading: return
        if self.ammo <= 0: return

        self.ammo -= 1
        self.sounds.play('m4_fire', volume=1.0)
        
        # --- 修正ポイント：player.world_pos.pos ではなく logical_pos を使う ---
        ray_origin = glm.vec3(self.logical_pos) + glm.vec3(0, 1.8, 0)
        
        visual_pitch = self._clamped_visual_pitch()
        ray_dir = glm.vec3(
            math.cos(visual_pitch) * math.sin(self.aim_yaw),
            math.sin(visual_pitch),
            math.cos(visual_pitch) * math.cos(self.aim_yaw) * -1
        )
        
        # トレーサー（弾道）の発生位置も修正
        tracer_rot = glm.quat(glm.rotate(self.aim_yaw, (0, 1, 0)) * glm.rotate(visual_pitch, (1, 0, 0)))
        from mgllib.tracer import Tracer
        tracer_spawn = ray_origin + ray_dir * 0.5
        self.tracers.append(Tracer(self.tracer_res, 'm4', tracer_spawn, tracer_rot))

        # ... (以下、NPCとの判定処理) ...
        for npc in self.npcs:
            if npc.killed: continue

            # 修正ポイント1：判定の中心を上にずらす
            # 風船の描画位置が npc.pos + (0, 1.8, 0) あたりなので、
            # 中心を 1.8m 〜 2.0m くらいに上げると本体に重なります。
            npc_center = glm.vec3(npc.pos) + glm.vec3(0, 2.0, 0) 
            
            offset = npc_center - ray_origin
            proj = glm.dot(offset, ray_dir)
            if proj < 0: continue 
            
            closest_point_on_ray = ray_origin + ray_dir * proj
            dist_to_ray = glm.distance(npc_center, closest_point_on_ray)

            # 修正ポイント2：判定を少しタイトにする
            # 1.2m だと風船に対してかなり広いので、0.7m 〜 0.9m くらいにすると
            # 「ちゃんと風船を狙わないと当たらない」絶妙な難易度になります。
            if dist_to_ray < 0.8: 
                self.hit_marker_timer = 0.15 
                npc.damage('m4', 'body')
                self.score += 10
                break
        # for npc in self.npcs:
        #     if npc.killed: continue
        #     npc_center = glm.vec3(npc.pos) + glm.vec3(0, 1.0, 0)
        #     offset = npc_center - ray_origin  # ここも正しくなる
        #     proj = glm.dot(offset, ray_dir)
        #     if proj < 0: continue 
            
        #     closest_point_on_ray = ray_origin + ray_dir * proj
        #     dist_to_ray = glm.distance(npc_center, closest_point_on_ray)
        #     if dist_to_ray < 1.2: 
        #         self.hit_marker_timer = 0.15 
        #         npc.damage('m4', 'body')
        #         self.score += 10 # Add score
        #         break

    def single_update(self):
        self.player.cycle()

        self.handle_sniper_inputs()
        if self.menu_open: return

        # --- 修正1: リロード完了時に弾をフルにする ---
        if self.reloading:
            self.reload_timer -= self.window.dt
            if self.reload_timer <= 0:
                self.reloading = False
                self.ammo = self.max_ammo  # ここで弾を補充！

        # --- 修正2: ADS（構え）の進行度を計算する ---
        # これがないと is_zoomed が True にならず、スコープ画面に切り替わりません
        dt = self.window.dt
        if self.is_ads:
            self.ads_progress = min(1.0, self.ads_progress + self.ads_speed * dt)
        else:
            self.ads_progress = max(0.0, self.ads_progress - self.ads_speed * dt)

        self.recoil *= 0.8
        if self.hit_marker_timer > 0: self.hit_marker_timer -= self.window.dt
        
        # --- NPCの生成位置も床の中央に合わせる ---
        # for npc in list(self.npcs):
        #     if npc.update(): self.npcs.remove(npc)

        for npc in list(self.npcs):
            try:
                if npc.update():
                    self.npcs.remove(npc)
                    continue
            except Exception as e:
                print(f"[NPC update error] {e}")
                continue

            # 水平位置をスポーン地点に毎フレーム固定（上下のbobbing描画側は別途やるのでy=0固定でOK）
            if hasattr(npc, '_spawn_pos'):
                npc.pos[0] = npc._spawn_pos[0]
                npc.pos[2] = npc._spawn_pos[2]
            
        while len(self.npcs) < 10:
            spawn_pos = self._spawn_npc_in_front()
            
            new_npc = NPC(spawn_pos) 
            
            if hasattr(new_npc, 'world'):
                new_npc.world = self.world
            
            # brainをNoneにしてAIを完全停止
            if hasattr(new_npc, 'brain'):
                new_npc.brain = None
            
            # 速度・移動系の変数をゼロにリセット
            for attr in ('velocity', 'vel', 'speed', 'move_speed'):
                if hasattr(new_npc, attr):
                    try:
                        setattr(new_npc, attr, glm.vec3(0))
                    except Exception:
                        setattr(new_npc, attr, 0)
            
            # スポーン位置を記憶（毎フレーム水平座標を固定するため）
            new_npc._spawn_pos = list(spawn_pos)
            
            new_npc.health = 10
            self.npcs.append(new_npc)
        # while len(self.npcs) < 12:
        #     spawn_pos = self._spawn_npc_in_front()
            
        #     # 2. 第一引数に座標を渡す（self.world は不要、または別の方法で設定）
        #     new_npc = NPC(spawn_pos) 
            
        #     # もし world を設定する必要があるなら生成後に（NPCの仕様によります）
        #     if hasattr(new_npc, 'world'):
        #         new_npc.world = self.world
            
        #     if hasattr(new_npc, 'brain') and new_npc.brain: 
        #         new_npc.brain.weapon = None
            
        #     new_npc.health = 40
        #     self.npcs.append(new_npc)
            
        for p in list(self.particles):
            if p.update(): self.particles.remove(p)
        for t in list(self.tracers):
            if t.update(): self.tracers.remove(t)

        # Update HUD Text content
        self.hud.clear()
        self.hud.add_text(f"AMMO: {self.ammo}/{self.max_ammo}", (30, self.window.dimensions[1] - 80), color=(0, 0, 0))
        self.hud.add_text(f"ZOOM: {70 // self.zoom_indices[self.zoom_idx]}x", (30, self.window.dimensions[1] - 130), color=(0, 0, 0))
        self.hud.add_text(f"SCORE: {self.score}", (self.window.dimensions[0] - 220, 30), color=(0, 0, 0))
        
        if self.ammo <= 0 and not self.reloading:
            self.hud.add_text("PRESS R TO RELOAD", (self.window.dimensions[0]//2 - 140, self.window.dimensions[1]//2 + 150), color=(255, 255, 0))

        if self.reloading:
            self.hud.add_text("RELOADING...", (self.window.dimensions[0]//2 - 80, self.window.dimensions[1]//2 + 100), color=(255, 100, 100))
        
        # Flash on shoot
        if self.shoot_visual_timer > 0:
            self.shoot_visual_timer -= self.window.dt
            flash_surf = pygame.Surface(self.window.dimensions, pygame.SRCALPHA)
            flash_surf.fill((255, 255, 255, 100))
            self.hud.surface.blit(flash_surf, (0, 0))

        self.hud.update()
        self.player.late_cycle()

    def render_scene(self, camera, include_viewmodel=False, fbo=None):
        if fbo:
            fbo.use()

        self.mgl.ctx.clear(red=0.5, green=0.7, blue=0.9, alpha=1.0, depth=1.0)
            
        # 全シェーダーに現在の行列を叩き込む（writeを使用）
        shaders = [
            self.main_shader, self.npc_shader, self.tracer_shader, 
            self.no_norm_shader, self.decor_shader
        ]
        
        import struct
        mat_bytes = struct.pack('16f', *camera.prepped_matrix)
        
        for shader in shaders:
            if 'view_projection' in shader:
                shader['view_projection'].write(mat_bytes)
            elif 'u_view_projection' in shader:
                shader['u_view_projection'].write(mat_bytes)
        
        #self.skybox.render(camera)
        
        # Skybox描画後にターゲットを確実に元に戻す
        if fbo:
            fbo.use()
        else:
            self.mgl.ctx.screen.use()
            
        self.mgl.ctx.enable(moderngl.DEPTH_TEST)
        self.mgl.ctx.depth_mask = True
        
        # for npc in self.npcs: npc.render(camera)
        self.world.render(camera)
        
# --- render_scene 内の NPC ループ ---
        # --- render_scene 内の NPC ループ ---
        for i, npc in enumerate(self.npcs):
            if hasattr(npc, 'killed') and npc.killed: continue

            # 1. まず位置と動きの計算（ここで model_mat を定義！）
            balloon_pos = glm.vec3(npc.pos) + glm.vec3(0, 1.8, 0)
            bobbing = math.sin(time.time() * 2.0 + i) * 0.1
            
            model_mat = glm.translate(balloon_pos + glm.vec3(0, bobbing, 0))
            model_mat = glm.rotate(model_mat, time.time() * 0.5, glm.vec3(0, 1, 0))
            model_mat = glm.scale(model_mat, glm.vec3(1, 1, 1)) # サイズはお好みで

            # 2. テクスチャを上書き（床のテクスチャを追い出す）
            self.balloon_color_tex.use(0)

            # 3. uniforms の作成（ここで model_mat を使う）
            from mgllib.mat3d import prep_mat
            render_uniforms = {
                'world_transform': prep_mat(model_mat),
                'view_projection': camera.prepped_matrix,
                'u_color': (1.0, 1.0, 1.0, 1.0), 
                'color': (1.0, 1.0, 1.0, 1.0),
                'u_use_texture': 1.0,
                'u_texture': 0
            }

            # 4. 描画実行
            self.balloon_model.vao.render(uniforms=render_uniforms)

        for p in self.particles: p.render(camera)
        for t in self.tracers: t.render(camera)
        # self.world.render(camera)
        
        if include_viewmodel: self.render_viewmodel(camera)


    def render_viewmodel(self, camera):
        # 腰だめ時の位置 (右下)
        hip_pos = glm.vec3(0.12, -0.18, -0.22)
        # ADS時の位置 (画面中央・少し手前) 
        # ※モデルの形に合わせて X と Y を微調整してください
        ads_pos = glm.vec3(0.0, -0.12, -0.15) 

        # ads_progressを使って、2つの位置の間を線形補間(Mix)する
        view_offset = glm.mix(hip_pos, ads_pos, self.ads_progress)

        cam_pos = glm.vec3(camera.eye_pos)
        visual_pitch = self._clamped_visual_pitch()
        q_yaw = glm.angleAxis(-self.aim_yaw, glm.vec3(0, 1, 0))
        q_pitch = glm.angleAxis(visual_pitch, glm.vec3(1, 0, 0))
        orientation = q_yaw * q_pitch

        # 銃の行列計算
        gun_transform = glm.translate(cam_pos) * glm.mat4(orientation) * glm.translate(view_offset) * glm.scale(glm.vec3(0.08))
        
        self.m4_res.vao.render(uniforms={
            'world_transform': prep_mat(gun_transform),
            'view_projection': camera.prepped_matrix,
            'world_light_pos': tuple(camera.light_pos),
            'eye_pos': camera.eye_pos
        })

    def update(self, view_index):
        if view_index == 0:
            self.single_update()

        self.input_mgr.update()
        hand_r = self.input_mgr.right_hand
        hand_l = self.input_mgr.left_hand
        dt = self.window.dt

        # if view_index == 0 and not self.initial_view_reset_done:
        #     hand_r.reset_view()
        #     if hasattr(hand_l, 'reset_view'):
        #         hand_l.reset_view()
        #     self.initial_view_reset_done = True

        # --- 視点リセット (Q または 左手クリック) ---
        for event in self.events:
            if event.type == pygame.KEYDOWN and event.key == pygame.K_q:
                hand_r.reset_view()
                if hasattr(hand_l, 'reset_view'):
                    hand_l.reset_view()
                    
        # 左コントローラーのクリックで視点リセット
        if hand_l.is_clicked:
            hand_r.reset_view()
            if hasattr(hand_l, 'reset_view'):
                hand_l.reset_view()

        # --- 右手：照準・射撃・ズーム ---
        self.aim_yaw, self.aim_pitch = hand_r.get_euler()
        self._clamp_aim_pitch()
        if view_index == 0 and hand_r.is_clicked:
            self.shoot()

        if view_index == 0:
            now = pygame.time.get_ticks() / 1000.0
            if getattr(hand_r, 'is_clicking', False):
                if self.right_hold_start_time is None:
                    self.right_hold_start_time = now
                    self.right_hold_reload_fired = False
                elif (not self.right_hold_reload_fired) and (now - self.right_hold_start_time >= self.right_hold_reload_seconds):
                    self.start_reload()
                    self.right_hold_reload_fired = True
            else:
                self.right_hold_start_time = None
                self.right_hold_reload_fired = False
        
        if abs(hand_r.tb_rotation_y) > 0:
            self.is_ads = not self.is_ads
            self.zoom_idx = 1 if self.is_ads else 0

        # --- 左手：前後移動のみ ---
        if view_index == 0:
            if hand_l.tb_rotation_y < 0:
                self._add_forward_impulse(1.0, dt)
            if hand_l.tb_rotation_y > 0:
                self._add_forward_impulse(-1.0, dt)

            self._integrate_forward_movement(dt)

            # --- 銃（プレイヤー）の完全同期 ---
            # 銃が消えないよう、直接成分を代入
            self.player.world_pos.pos[0] = self.logical_pos.x
            self.player.world_pos.pos[1] = self.logical_pos.y
            self.player.world_pos.pos[2] = self.logical_pos.z
            
            # 銃の向き（Yaw）を更新。もし 'rotation' が無ければ AttributeError を無視
            try:
                self.player.world_pos.rotation[1] = self.aim_yaw
            except:
                pass

        # --- 5. レンダリング準備 ---
        cam = self.e['XRCamera']
        cam_pos = self.logical_pos + glm.vec3(0, 1.8, 0)
        visual_pitch = self._clamped_visual_pitch()
        is_zoomed = (self.ads_progress > 0.5)

        # 共通の視線ベクトル計算
        front = glm.vec3(
            math.cos(visual_pitch) * math.sin(self.aim_yaw),
            math.sin(visual_pitch),
            math.cos(visual_pitch) * math.cos(self.aim_yaw) * -1
        )
        view_mat = glm.lookAt(cam_pos, cam_pos + front, glm.vec3(0, 1, 0))

        # --- 6. Scope Rendering (PiP) ---
        if is_zoomed:
            self.scope_fbo.use()
            self.mgl.ctx.viewport = (0, 0, 1200, 800)
            self.scope_fbo.clear(0, 0, 0, 1, depth=1.0)
            
            proj_scope = glm.perspective(glm.radians(self.zoom_indices[self.zoom_idx]), 1.5, 0.03, 300.0)
            
            from mgllib.xrmock import Matrix4x4f
            cam.matrix = Matrix4x4f() 
            cam.pos, cam.eye_pos = list(cam_pos), list(cam_pos)
            cam.world_rotation = [-visual_pitch, -self.aim_yaw, 0]
            cam.prepped_matrix = prep_mat(proj_scope * view_mat)
            cam.sky_matrix = cam.prepped_matrix
            
            self.render_scene(cam, include_viewmodel=False, fbo=self.scope_fbo)

        # --- 7. Main Screen Rendering ---
        self.mgl.ctx.screen.use()
        self.mgl.ctx.viewport = (0, 0, 1200, 800)
        
        proj_main = glm.perspective(glm.radians(70), 1.5, 0.03, 300.0)
        # 非ADS時でも viewmodel が正しく追従するように、毎フレーム更新する
        cam.pos, cam.eye_pos = list(cam_pos), list(cam_pos)
        cam.world_rotation = [-visual_pitch, -self.aim_yaw, 0]
        cam.prepped_matrix = prep_mat(proj_main * view_mat)
        cam.sky_matrix = cam.prepped_matrix
        
        self.render_scene(cam, include_viewmodel=True, fbo=None)
        
        # --- 8. HUD Composite ---
        self.hud.render(is_zoomed=is_zoomed, show_hit=(self.hit_marker_timer > 0), scope_tex=self.scope_tex)

        if self.debug_frames_left > 0:
            self.debug_frames_left -= 1

    def run(self):
        self.window.run()

if __name__ == "__main__":
    PicoSniper().run()

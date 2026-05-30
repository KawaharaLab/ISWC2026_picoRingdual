import gc
import time
import math

import glm
import numpy as np
from pympler import tracker
from OpenGL import GL
try:
    import xr
except (ImportError, NotImplementedError):
    from . import xrmock as xr

from .xr_plugin_hack import hack_pyopenxr
from .xrinput import XRInput
from .elements import ElementSingleton

class XRCamera(ElementSingleton):
    def __init__(self, pos=[0, 0, 1], target=[0, 0, 0], up=[0, 1, 0]):
        super().__init__()
        self.pos = list(pos)
        self.target = list(target)
        self.up = list(up)

        self.matrix = None
        self.prepped_matrix = None
        self.sky_matrix = None

        self.world_matrix = None
        self.world_rotation = [0, 0, 0]

        self.light_pos = [0.1, 1, 0.2]
        self.eye_pos = [0, 0, 0]

    def cycle(self):
        if type(self.world_matrix) != type(None):
            # take original view matrix -> remove head offset -> apply world transform
            self.prepped_matrix = (self.world_matrix.T @ self.e['XRInput'].head_transform @ np.reshape(self.matrix.as_numpy(), (4, 4))).flatten()

            # hacked eye pos (not accurate for separate eye positions; just based on head pos)
            # only used for specular
            self.eye_pos = [self.e['Demo'].player.world_pos.pos[0], self.pos[1] + self.e['Demo'].player.world_pos.pos[1], self.e['Demo'].player.world_pos.pos[2]]
        else:
            self.prepped_matrix = self.matrix.as_numpy()
            self.eye_pos = list(self.pos)

        self.sky_matrix = self.matrix.as_numpy()

class XRState(ElementSingleton):
    def __init__(self):
        super().__init__()

        self.camera = XRCamera()
        self.orientation = None

    @property
    def forward_vec(self):
        return glm.mat4(glm.quat(self.orientation[3], *self.orientation[:3])) * glm.vec3(0, 0, -1)

    @property
    def xz_angle(self):
        if self.orientation:
            return math.atan2(self.forward_vec.x, self.forward_vec.z)
        return 0

class XRWindow(ElementSingleton):
    def __init__(self, application, dimensions=(800, 800), fps=165, title='VR Test'):
        super().__init__()
        
        self.application = application
        self.dimensions = dimensions
        self.fps = fps

        self.dt = 0.1
        self.last_frame = time.time()

        self.xrstate = XRState()

        self.title = title

        self.input = XRInput()

        self.motion_flags = [0, 1, 0]

        #self.mem_check = tracker.SummaryTracker()

    def run(self):
        is_mock = hasattr(xr, 'ContextObject') and xr.__name__.endswith('xrmock')
        
        if is_mock:
            import pygame
            pygame.init()
            pygame.display.gl_set_attribute(pygame.GL_CONTEXT_MAJOR_VERSION, 3)
            pygame.display.gl_set_attribute(pygame.GL_CONTEXT_MINOR_VERSION, 3)
            pygame.display.gl_set_attribute(pygame.GL_CONTEXT_PROFILE_MASK, pygame.GL_CONTEXT_PROFILE_CORE)
            self.screen = pygame.display.set_mode(self.dimensions, pygame.OPENGL | pygame.DOUBLEBUF)
            pygame.display.set_caption(self.title)
            
            self.application.init_mgl()
            self.input.init(None) # Pass None to mock init
            
            clock = pygame.time.Clock()
            while True:
                self.application.events = pygame.event.get()
                for event in self.application.events:
                    if event.type == pygame.QUIT:
                        pygame.quit()
                        import sys
                        sys.exit()
                
                new_time = time.time()
                self.dt = min(new_time - self.last_frame, 0.1)
                self.last_frame = new_time
                
                # Mock frame state
                frame_state = type('FrameState', (), {'predicted_display_time': time.time()})()
                self.input.update(frame_state)
                
                # Render logic (simplified for desktop)
                GL.glClearColor(0, 0, 0, 1) # Black reset
                GL.glClearDepth(1.0)
                GL.glClear(GL.GL_COLOR_BUFFER_BIT | GL.GL_DEPTH_BUFFER_BIT)
                
                self.application.update(0) # view_index 0
                
                pygame.display.flip()
                clock.tick(self.fps)
            return

        hack_pyopenxr(self.dimensions, self.title)
                

                #if frame_index % 600 == 0:
                #    self.mem_check.print_diff()
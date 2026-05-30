import numpy as np
import glm
import time

class typedefs:
    class Vector3f:
        def __init__(self, x, y, z):
            self.x, self.y, self.z = x, y, z
        def __getitem__(self, i):
            return [self.x, self.y, self.z][i]
    class Quaternionf:
        def __init__(self, x, y, z, w):
            self.x, self.y, self.z, self.w = x, y, z, w
        def __getitem__(self, i):
            return [self.x, self.y, self.z, self.w][i]
    class Posef:
        def __init__(self, orientation, position):
            self.orientation = orientation
            self.position = position

class Matrix4x4f:
    def __init__(self, m=None):
        if m is None:
            self.m = np.identity(4, dtype=np.float32)
        else:
            self.m = m
    
    def as_numpy(self):
        return self.m.flatten()
    
    def __matmul__(self, other):
        return Matrix4x4f(self.m @ other.m)

    @staticmethod
    def create_projection_fov(graphics_api, fov, near_z, far_z):
        # Simplified projection
        return Matrix4x4f(np.identity(4, dtype=np.float32))

    @staticmethod
    def create_translation_rotation_scale(translation, rotation, scale):
        return Matrix4x4f(np.identity(4, dtype=np.float32))

    @staticmethod
    def invert_rigid_body(m):
        return Matrix4x4f(np.linalg.inv(m.m))

class GraphicsAPI:
    OPENGL = 1

class View:
    def __init__(self):
        self.fov = None
        self.pose = typedefs.Posef(typedefs.Quaternionf(0,0,0,1), typedefs.Vector3f(0,0,0))

class Context:
    def __init__(self):
        self.session = None
        self.instance = None
        self.default_action_set = None
        self.swapchains = [type('Swapchain', (), {'width': 1920, 'height': 1080})()]
        self.session_state = 3 # FOCUSED
    
    def frame_loop(self):
        while True:
            yield type('FrameState', (), {'predicted_display_time': time.time()})()
    
    def view_loop(self, frame_state):
        yield View()

class ContextObject:
    def __init__(self, instance_create_info=None):
        pass
    def __enter__(self):
        return Context()
    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

# Enums
KHR_OPENGL_ENABLE_EXTENSION_NAME = "XR_KHR_opengl_enable"
ActionType = type('ActionType', (), {'POSE_INPUT': 1, 'FLOAT_INPUT': 2, 'BOOLEAN_INPUT': 3, 'VIBRATION_OUTPUT': 4})()
SessionState = type('SessionState', (), {'FOCUSED': 3})()
SPACE_LOCATION_POSITION_VALID_BIT = 1
NULL_PATH = 0
ReferenceSpaceType = type('ReferenceSpaceType', (), {'VIEW': 1})()

def string_to_path(instance, path_string): return 0
def create_action(*args, **kwargs): return 0
def create_action_space(*args, **kwargs): return 0
def create_reference_space(*args, **kwargs): return 0
def locate_space(*args, **kwargs): 
    return type('SpaceLocation', (), {'location_flags': 1, 'pose': typedefs.Posef(typedefs.Quaternionf(0,0,0,1), typedefs.Vector3f(0,0,0))})()
def sync_actions(*args, **kwargs): pass
def get_action_state_float(*args, **kwargs): return type('S', (), {'current_state': 0.0})()
def get_action_state_boolean(*args, **kwargs): return type('S', (), {'current_state': False, 'changed_since_last_sync': False})()

class InstanceCreateInfo:
    def __init__(self, enabled_extension_names): pass
class ActionCreateInfo:
    def __init__(self, **kwargs): pass
class ActionSuggestedBinding:
    def __init__(self, **kwargs): pass
class InteractionProfileSuggestedBinding:
    def __init__(self, **kwargs): pass
def suggest_interaction_profile_bindings(*args, **kwargs): pass

# Haptics
MIN_HAPTIC_DURATION = 0
FREQUENCY_UNSPECIFIED = 0
class HapticVibration:
    def __init__(self, **kwargs): pass
class HapticActionInfo:
    def __init__(self, **kwargs): pass
class HapticBaseHeader: pass
def apply_haptic_feedback(*args, **kwargs): pass

class ActiveActionSet:
    def __init__(self, **kwargs): pass
class ActionsSyncInfo:
    def __init__(self, **kwargs): pass
class ActionStateGetInfo:
    def __init__(self, **kwargs): pass

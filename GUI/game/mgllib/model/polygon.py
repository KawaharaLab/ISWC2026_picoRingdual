import math
from array import array
import glm
import moderngl
from ..mat3d import flatten, prep_mat
from ..elements import Element

# --- 1. 四面体のデータはそのまま残す（他のエフェクトで使用するため） ---
TETRAHEDRON_VERTICES = [
    (math.cos(0.0) * 0.7, math.sin(0.0) * 0.7, 0.0),
    (math.cos(math.pi * 2 / 3) * 0.7, math.sin(math.pi * 2 / 3) * 0.7, 0.5),
    (math.cos(math.pi * 4 / 3) * 0.7, math.sin(math.pi * 4 / 3) * 0.7, 0.5),
    (0.0, 0.0, -0.5),
]

TETRAHEDRON = [
    TETRAHEDRON_VERTICES[0], TETRAHEDRON_VERTICES[1], TETRAHEDRON_VERTICES[2],
    TETRAHEDRON_VERTICES[0], TETRAHEDRON_VERTICES[2], TETRAHEDRON_VERTICES[3],
    TETRAHEDRON_VERTICES[1], TETRAHEDRON_VERTICES[0], TETRAHEDRON_VERTICES[3],
    TETRAHEDRON_VERTICES[2], TETRAHEDRON_VERTICES[1], TETRAHEDRON_VERTICES[3],
]

# --- 2. 風船用の「球体に近い」データを追加する ---
def generate_sphere_vertices(segments=8):
    vertices = []
    for i in range(segments):
        lat0 = math.pi * (-0.5 + float(i) / segments)
        lat1 = math.pi * (-0.5 + float(i + 1) / segments)
        for j in range(segments):
            lon0 = 2 * math.pi * float(j) / segments
            lon1 = 2 * math.pi * float(j + 1) / segments
            def get_p(lat, lon):
                return (math.cos(lat) * math.cos(lon), math.sin(lat), math.cos(lat) * math.sin(lon))
            p1, p2, p3, p4 = get_p(lat0, lon0), get_p(lat0, lon1), get_p(lat1, lon1), get_p(lat1, lon0)
            vertices.extend([p1, p2, p3, p1, p3, p4])
    return vertices

BALLOON = generate_sphere_vertices(12) # 12分割くらいするとかなり丸くなります

class Polygon(Element):
    def __init__(self, points, program):
        super().__init__()
        ctx = self.e['MGL'].ctx
        self.program = program
        self.buffer = ctx.buffer(data=array('f', flatten(points)))
        
        # 変数名のエラーを防ぐための柔軟なバインド
        in_name = 'vert'
        if 'in_vert' in program: in_name = 'in_vert'
        elif 'vert_pos' in program: in_name = 'vert_pos'
        
        self.vao = ctx.vertex_array(program, [(self.buffer, '3f', in_name)])

    def update_uniforms(self, uniforms={}):
        uniform_list = list(self.program)
        tex_id = 0
        for name, value in uniforms.items():
            if name in uniform_list:
                if isinstance(value, moderngl.Texture):
                    value.use(tex_id)
                    self.program[name].value = tex_id
                    tex_id += 1
                else:
                    # 行列(bytes)と数値(float/int/tuple)を自動判別して書き込む
                    if isinstance(value, (bytes, bytearray)):
                        self.program[name].write(value)
                    else:
                        self.program[name].value = value

class PolygonOBJ(Element):
    def __init__(self, shape, pos=None, rotation=None):
        super().__init__()
        self.polygon = shape
        self.scale = glm.vec3(1.0, 1.0, 1.0)
        self.pos = glm.vec3(pos) if pos else glm.vec3(0.0, 0.0, 0.0)
        self.rotation = glm.quat(rotation) if rotation else glm.quat()
        self.calculate_transform()

    def calculate_transform(self):
        self.transform = glm.translate(self.pos) * glm.mat4(self.rotation) * glm.scale(self.scale)

    def update(self):
        self.calculate_transform()

    def render(self, camera, uniforms={}):
        # 以前起きていた tuple 渡しのエラーを防ぐため、ここで bytes に変換
        import struct
        from ..mat3d import prep_mat
        
        uniforms['world_transform'] = struct.pack('16f', *prep_mat(self.transform))
        
        vp = camera.prepped_matrix
        if isinstance(vp, tuple):
            uniforms['view_projection'] = struct.pack('16f', *vp)
        else:
            uniforms['view_projection'] = vp

        self.polygon.update_uniforms(uniforms=uniforms)
        self.polygon.vao.render(mode=moderngl.TRIANGLES)
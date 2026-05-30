from .mat3d import prep_mat, perspective_matrix, lookat_matrix

class Camera:
    def __init__(self, pos=[0, 0, 1], target=[0, 0, 0], up=[0, 1, 0], fov=80, ratio=1.0):
        self.pos = list(pos)
        self.target = list(target)
        self.up = list(up)
        self.fov = fov
        self.ratio = ratio
        self.update_matrix()

        self.eye_pos = list(self.pos)
        self.light_pos = [0, 1, 0]

    def lookat(self, target):
        self.target = list(target)
        self.update_matrix()

    def move(self, movement):
        for i in range(3):
            self.pos[i] += movement[i]
        self.eye_pos = list(self.pos)
        self.update_matrix()

    def set_pos(self, pos):
        self.pos = list(pos)
        self.eye_pos = list(self.pos)
        self.update_matrix()
    
    def update_matrix(self):
        view_matrix = lookat_matrix(self.pos, self.target, self.up)
        projection_matrix = perspective_matrix(self.fov, self.ratio, 0.001, 200)
        self.matrix = projection_matrix * view_matrix
        self.prepped_matrix = prep_mat(self.matrix)
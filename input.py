from PySide2 import QtGui
from PySide2.QtCore import Qt

from objects import Scene
import glm
import math

class InputController:
    def __init__(self, scene: Scene):
        self.scene = scene

    def update(self, keys: dict[Qt.Key, bool], mouse_delta: QtGui.QVector2D, delta_time: float):
        rotate_speed = 0.05
        self.scene.camera.orientation += rotate_speed * glm.vec3(mouse_delta.y(), mouse_delta.x(), 0)
        self.scene.camera.orientation.x = min(max(self.scene.camera.orientation.x, -45), 45)

        light_dirs = glm.vec3()
        light_key_map = {
            Qt.Key_I: (0, 1, 0),
            Qt.Key_J: (-1, 0, 0),
            Qt.Key_K: (0, -1, 0),
            Qt.Key_L: (1, 0, 0),
            Qt.Key_U: (0, 0, -1),
            Qt.Key_O: (0, 0, 1),
        }
        light_moved = False
        for key in light_key_map:
            if(keys.get(key, False)):
                light_dirs = light_dirs + glm.vec3(*light_key_map[key])
                light_moved = True

        light_velocity = 3.0
        self.scene.light.position += light_dirs * light_velocity * delta_time
        self.scene.light.need_shadow_render = light_moved

        dirs = glm.vec3()
        key_map = {
            Qt.Key_W: (0, 1, 0),
            Qt.Key_A: (-1, 0, 0),
            Qt.Key_S: (0, -1, 0),
            Qt.Key_D: (1, 0, 0),
            Qt.Key_Q: (0, 0, -1),
            Qt.Key_E: (0, 0, 1),
        }

        accel = 15.0
        for key in key_map:
            if(keys.get(key, False)):
                dirs = dirs + glm.vec3(*key_map[key])
        accel_vector = accel * dirs

        matrix = glm.mat4()
        matrix = matrix * glm.rotate(math.radians(self.scene.camera.orientation.y), glm.vec3(0, 0, 1))

        drag = 15.0
        drag_vector = matrix * (-self.scene.camera.velocity * drag)

        if accel_vector.x == 0: accel_vector.x = drag_vector.x
        if accel_vector.y == 0: accel_vector.y = drag_vector.y
        if accel_vector.z == 0: accel_vector.z = drag_vector.z

        matrix = glm.mat4()
        matrix = matrix * glm.rotate(math.radians(-self.scene.camera.orientation.y), glm.vec3(0, 0, 1))

        self.scene.camera.velocity += matrix * (accel_vector * delta_time)
        max_velocity = 7.0
        if glm.length(self.scene.camera.velocity) > max_velocity:
            self.scene.camera.velocity = glm.normalize(self.scene.camera.velocity)
            self.scene.camera.velocity *= max_velocity
        self.scene.camera.position += self.scene.camera.velocity * delta_time

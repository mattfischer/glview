from PySide2 import QtGui
from PySide2.QtCore import Qt

class InputController:
    def __init__(self, camera, light):
        self.camera = camera
        self.light = light

    def update(self, keys, mouse_delta, delta_time):
        rotate_speed = 0.05
        self.camera.orientation += rotate_speed * QtGui.QVector3D(mouse_delta.y(), mouse_delta.x(), 0)
        self.camera.orientation.setX(min(max(self.camera.orientation.x(), -45), 45))

        light_dirs = QtGui.QVector3D()
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
                light_dirs = light_dirs + QtGui.QVector3D(*light_key_map[key])
                light_moved = True

        light_velocity = 3.0
        self.light.position += light_dirs * light_velocity * delta_time
        self.light.need_shadow_render = light_moved

        dirs = QtGui.QVector3D()
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
                dirs = dirs + QtGui.QVector3D(*key_map[key])
        accel_vector = accel * dirs

        matrix = QtGui.QMatrix4x4()
        matrix.rotate(self.camera.orientation.y(), 0, 0, 1)

        drag = 15.0
        drag_vector = matrix.mapVector(-self.camera.velocity * drag)

        if accel_vector.x() == 0: accel_vector.setX(drag_vector.x())
        if accel_vector.y() == 0: accel_vector.setY(drag_vector.y())
        if accel_vector.z() == 0: accel_vector.setZ(drag_vector.z())

        matrix = QtGui.QMatrix4x4()
        matrix.rotate(-self.camera.orientation.y(), 0, 0, 1)

        self.camera.velocity += matrix.mapVector(accel_vector * delta_time)
        max_velocity = 7.0
        if self.camera.velocity.length() > max_velocity:
            self.camera.velocity.normalize()
            self.camera.velocity *= max_velocity
        self.camera.position += self.camera.velocity * delta_time

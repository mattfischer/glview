from PySide2 import QtGui

from OpenGL import GL
import pygltflib

class Camera:
    def __init__(self, position: QtGui.QVector3D, fov: float):
        self.orientation = QtGui.QVector3D()
        self.position = position
        self.velocity = QtGui.QVector3D()
        self.vertical_fov = fov

    def view_transform(self) -> QtGui.QMatrix4x4:
        transform = QtGui.QMatrix4x4()
        transform.rotate(self.orientation.x(), 1, 0, 0)
        transform.rotate(self.orientation.y(), 0, 0, 1)
        transform.translate(-self.position)
        return transform

    def projection_transform(self, aspect_ratio: float) -> QtGui.QMatrix4x4:
        transform = QtGui.QMatrix4x4()
        transform.perspective(self.vertical_fov, aspect_ratio, .1, 100)
        return transform

class Light:
    def __init__(self, position: QtGui.QVector3D):
        self.position = position
        self.need_shadow_render = True

class GltfObject:
    def __init__(self, filename: str):
        gltf = pygltflib.GLTF2().load(filename)
        self.gltf = gltf

class Scene:
    def __init__(self, objects: list[GltfObject], camera: Camera, light: Light):
        self.objects = objects
        self.camera = camera
        self.light = light

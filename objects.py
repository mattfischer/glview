from PySide2 import QtGui

from OpenGL import GL
import pygltflib

from render import GltfRenderer, ShadowRenderer

class Camera:
    def __init__(self, position, fov):
        self.orientation = QtGui.QVector3D()
        self.position = position
        self.velocity = QtGui.QVector3D()
        self.vertical_fov = fov

    def view_transform(self):
        transform = QtGui.QMatrix4x4()
        transform.rotate(self.orientation.x(), 1, 0, 0)
        transform.rotate(self.orientation.y(), 0, 0, 1)
        transform.translate(-self.position)
        return transform

    def projection_transform(self, aspect_ratio):
        transform = QtGui.QMatrix4x4()
        transform.perspective(self.vertical_fov, aspect_ratio, .1, 100)
        return transform

class Light:
    def __init__(self, position):
        self.position = position
        self.renderer = ShadowRenderer(self)
        self.need_shadow_render = True

class GltfObject:
    def __init__(self, filename):
        gltf = pygltflib.GLTF2().load(filename)
        self.gltf = gltf
        self.renderer = GltfRenderer(self)

class Scene:
    def __init__(self, objects, camera, light):
        self.objects = objects
        self.camera = camera
        self.light = light

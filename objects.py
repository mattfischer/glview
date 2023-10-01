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

    def view_transform(self, face):
        transform = QtGui.QMatrix4x4()
        transform.scale(1, -1, -1)
        if face == GL.GL_TEXTURE_CUBE_MAP_POSITIVE_X:
            transform.rotate(-90, 0, 1, 0)
        elif face == GL.GL_TEXTURE_CUBE_MAP_NEGATIVE_X:
            transform.rotate(90, 0, 1, 0)
        elif face == GL.GL_TEXTURE_CUBE_MAP_POSITIVE_Y:
            transform.rotate(90, 1, 0, 0)
        elif face == GL.GL_TEXTURE_CUBE_MAP_NEGATIVE_Y:
            transform.rotate(-90, 1, 0, 0)
        elif face == GL.GL_TEXTURE_CUBE_MAP_POSITIVE_Z:
            transform.rotate(180, 0, 1, 0)
        elif face == GL.GL_TEXTURE_CUBE_MAP_NEGATIVE_Z:
            transform.rotate(180, 0, 1, 0)

        transform.translate(-self.position)
        return transform

    def projection_transform(self):
        transform = QtGui.QMatrix4x4()
        transform.perspective(90, 1, .1, 30)
        return transform

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

from PySide2 import QtGui

from OpenGL import GL
import pygltflib

import glm
import math

class Camera:
    def __init__(self, position: glm.vec3, fov: float):
        self.orientation = glm.vec3()
        self.position = position
        self.velocity = glm.vec3()
        self.vertical_fov = fov

    def view_transform(self) -> glm.mat4:
        transform = glm.mat4()
        transform = transform * glm.rotate(math.radians(self.orientation.x), glm.vec3(1, 0, 0))
        transform = transform * glm.rotate(math.radians(self.orientation.y), glm.vec3(0, 0, 1))
        transform = transform * glm.translate(-self.position)
        return transform

    def projection_transform(self, aspect_ratio: float) -> glm.mat4:
        return glm.perspective(math.radians(self.vertical_fov), aspect_ratio, .1, 100)

class Light:
    def __init__(self, position: glm.vec3):
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

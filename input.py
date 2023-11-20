from scene import Scene
import glm
import math
import glfw

class InputController:
    def __init__(self, scene: Scene, window):
        self.scene = scene
        self.window = window
        self.grabbed_mouse = False
        self.last_cursor = (0, 0)

    def update(self, delta_time: float):
        if glfw.get_mouse_button(self.window, glfw.MOUSE_BUTTON_LEFT) == glfw.PRESS:
            self.grabbed_mouse = True
            glfw.set_input_mode(self.window, glfw.CURSOR, glfw.CURSOR_DISABLED)
            self.last_cursor = glfw.get_cursor_pos(self.window)

        if glfw.get_key(self.window, glfw.KEY_ESCAPE) == glfw.PRESS:
            self.grabbed_mouse = False
            glfw.set_input_mode(self.window, glfw.CURSOR, glfw.CURSOR_NORMAL)

        mouse_delta = (0, 0)
        if self.grabbed_mouse:
            cursor_pos = glfw.get_cursor_pos(self.window)
            mouse_delta = (cursor_pos[0] - self.last_cursor[0], cursor_pos[1] - self.last_cursor[1])
            self.last_cursor = cursor_pos

        rotate_speed = 0.05
        self.scene.camera.orientation += rotate_speed * glm.vec3(mouse_delta[1], mouse_delta[0], 0)
        self.scene.camera.orientation.x = min(max(self.scene.camera.orientation.x, -45), 45)

        light_dirs = glm.vec3()
        light_key_map = {
            glfw.KEY_I: (0, 1, 0),
            glfw.KEY_J: (-1, 0, 0),
            glfw.KEY_K: (0, -1, 0),
            glfw.KEY_L: (1, 0, 0),
            glfw.KEY_U: (0, 0, -1),
            glfw.KEY_O: (0, 0, 1),
        }
        light_moved = False
        for key in light_key_map:
            if(glfw.get_key(self.window, key) == glfw.PRESS):
                light_dirs = light_dirs + glm.vec3(*light_key_map[key])
                light_moved = True

        light_velocity = 3.0
        self.scene.light.position += light_dirs * light_velocity * delta_time
        if light_moved:
            self.scene.light.need_shadow_render = True

        light_intensity_velocity = 500
        light_intensity_key_map = {
            glfw.KEY_M: -1,
            glfw.KEY_N: 1
        }
        for key in light_intensity_key_map:
            if(glfw.get_key(self.window, key) == glfw.PRESS):
                self.scene.light.intensity += light_intensity_key_map[key] * light_intensity_velocity * delta_time
                self.scene.light.intensity = max(self.scene.light.intensity, 0)

        dirs = glm.vec3()
        key_map = {
            glfw.KEY_W: (0, 1, 0),
            glfw.KEY_A: (-1, 0, 0),
            glfw.KEY_S: (0, -1, 0),
            glfw.KEY_D: (1, 0, 0),
            glfw.KEY_Q: (0, 0, -1),
            glfw.KEY_E: (0, 0, 1),
        }

        accel = 15.0
        for key in key_map:
            if(glfw.get_key(self.window, key) == glfw.PRESS):
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

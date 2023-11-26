from scene import Scene
from lights import Light
from objects import Camera, GltfObject, Skybox
from input import InputController

import glfw
import glm
import time

# https://sketchfab.com/3d-models/lowpoly-fps-tdm-game-map-d41a19f699ea421a9aa32b407cb7537b
gltf_object = GltfObject('lowpoly__fps__tdm__game__map.glb')

# https://sketchfab.com/3d-models/viking-room-6d61f7f0b597490aab7afa003e4ec725
# gltf_object = GltfObject('viking_room.glb')

camera = Camera(glm.vec3(0, .5, 0), 50)
light = Light(glm.vec3(8, 8, -11), 2000.0)
skybox = Skybox('skybox_texture.jpg')
scene = Scene([gltf_object], camera, light, skybox)

glfw.init()
window = glfw.create_window(1600, 1200, 'glview', None, None)

input_controller = InputController(scene, window)

glfw.make_context_current(window)

scene.init_gl(*glfw.get_window_size(window))
grabbed_mouse = False
last_frame_start_time = time.time()
render_time = 0
render_frames = 0
last_fps_print_time = time.time()

while not glfw.window_should_close(window):
    frame_start_time = time.time()
    delta_time = frame_start_time - last_frame_start_time
    last_frame_start_time = frame_start_time

    input_controller.update(delta_time)

    render_start_time = time.time()
    scene.render(*glfw.get_window_size(window))
    render_end_time = time.time()

    render_time += (render_end_time - render_start_time)
    render_frames += 1
    if render_end_time > last_fps_print_time + 1:
        print('Average render time: %ims' % (render_time * 1000 / render_frames))
        render_time = 0
        render_frames = 0
        last_fps_print_time = render_end_time
    
    glfw.swap_buffers(window)
    glfw.poll_events()

glfw.terminate()
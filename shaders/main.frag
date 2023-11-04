#version 130

uniform vec4 base_color;
uniform sampler2D color_texture;
uniform bool has_color_texture;
uniform vec3 light_position;
uniform samplerCubeShadow shadow_texture;

varying vec3 frag_pos;
varying vec3 frag_normal;
varying vec2 frag_texcoord;
void main()
{
    vec4 color;
    if(has_color_texture) {
        color = texture(color_texture, frag_texcoord);
    } else {
        color = base_color;
    }

    vec3 light_vec = frag_pos - light_position;
    float light_dist = length(light_vec);
    float shade = max(-dot(light_vec / light_dist, frag_normal), 0);
    float light_depth = max(max(abs(light_vec.x), abs(light_vec.y)), abs(light_vec.z));
    float far = 30;
    float near = .1;
    light_depth -= 0.05 / shade;
    float depth_ref = (far + near) / (far - near) - (2 * far * near) / ((far - near) * light_depth);
    depth_ref = (depth_ref + 1) / 2;

    float shadow = texture(shadow_texture, vec4(light_vec, depth_ref));
    gl_FragColor = (shadow * shade + .25) * color;
}
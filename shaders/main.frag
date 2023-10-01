#version 130

uniform vec4 color;
uniform vec3 light_position;
uniform samplerCubeShadow shadow_texture;

varying vec3 frag_pos;
varying vec3 frag_normal;

void main()
{
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
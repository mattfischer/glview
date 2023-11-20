#version 130

uniform vec3 base_color;
uniform sampler2D color_texture;
uniform bool has_color_texture;
uniform vec3 light_position;
uniform samplerCubeShadow shadow_texture;
uniform float light_intensity;

varying vec3 frag_pos;
varying vec3 frag_normal;
varying vec2 frag_texcoord;
void main()
{
    vec3 color;
    if(has_color_texture) {
        color = texture(color_texture, frag_texcoord).xyz;
    } else {
        color = base_color;
    }

    vec3 light_vec = frag_pos - light_position;
    float light_dist = length(light_vec);
    float light_cos = max(-dot(light_vec / light_dist, frag_normal), 0);

    float light_depth = max(max(abs(light_vec.x), abs(light_vec.y)), abs(light_vec.z));
    float far = 30;
    float near = .1;
    light_depth -= 0.05 / light_cos;
    float depth_ref = (far + near) / (far - near) - (2 * far * near) / ((far - near) * light_depth);
    depth_ref = (depth_ref + 1) / 2;

    float light_visibility = texture(shadow_texture, vec4(light_vec, depth_ref));

    vec3 light_color = vec3(1, 1, 1);
    vec3 light_radiance = light_color * light_intensity;
    vec3 light_irradiance = light_radiance * light_visibility * light_cos / (light_dist * light_dist);
    vec3 ambient_irradiance = vec3(1, 1, 1);
    vec3 irradiance = light_irradiance + ambient_irradiance;
    vec3 radiance = irradiance * color / 3.14;

    vec3 fragColor = radiance / (radiance + vec3(1, 1, 1));
    gl_FragColor = vec4(fragColor, 1.0);
}
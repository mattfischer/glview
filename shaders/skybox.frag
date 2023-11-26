#version 130

uniform samplerCube skybox_texture;

varying vec3 frag_pos;

void main()
{
    gl_FragColor = texture(skybox_texture, frag_pos);
}
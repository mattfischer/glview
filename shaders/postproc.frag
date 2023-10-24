#version 130

uniform sampler2D frame;
uniform sampler2D depth;

void main()
{
    ivec2 pos = ivec2(gl_FragCoord.xy);

    vec4 color = texelFetch(frame, pos, 0);
    vec4 blurColor = (texelFetch(frame, pos + ivec2(-5, -5), 0) + texelFetch(frame, pos + ivec2(0, -5), 0) + texelFetch(frame, pos + ivec2(5, -5), 0) +
                 texelFetch(frame, pos + ivec2(-5, 0), 0) + texelFetch(frame, pos + ivec2(0, 0), 0) + texelFetch(frame, pos + ivec2(5, 0), 0) +
                 texelFetch(frame, pos + ivec2(-5, 5), 0) + texelFetch(frame, pos + ivec2(0, 5), 0) + texelFetch(frame, pos + ivec2(5, -5), 0)) / 9;
    
    float d = texelFetch(depth, pos, 0).r;
    if(d < 0.9) {
        gl_FragColor = color;
    } else if(d > 0.95) {
        gl_FragColor = blurColor;
    } else {
        float f = (d - 0.9) / 0.05;
        gl_FragColor = color * (1 - f) + blurColor * f;
    }
}
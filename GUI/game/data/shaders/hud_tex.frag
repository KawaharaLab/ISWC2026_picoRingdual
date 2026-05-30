#version 330

uniform sampler2D tex;
out vec4 f_color;
in vec2 uv;

void main() {
    f_color = texture(tex, uv);
    if (f_color.a < 0.1) {
        discard;
    }
}

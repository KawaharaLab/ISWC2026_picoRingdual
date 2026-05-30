#version 330

uniform sampler2D hud_tex;
uniform sampler2D scope_tex;
uniform bool is_zoomed;
uniform float aspect;

out vec4 f_color;
in vec2 uv;

void main() {
    vec4 hud_col = texture(hud_tex, uv);
    
    if (is_zoomed) {
        // Scope circle logic
        vec2 center = vec2(0.5, 0.5);
        vec2 diff = uv - center;
        // Adjust x by aspect ratio to make distance spherical (circular)
        diff.x *= aspect;
        float dist = length(diff);
        float radius = 0.25; // Adjusted for better circle size
        
        if (dist < radius) {
            // Inside scope: show zoomed view
            f_color = texture(scope_tex, uv);
            
            // Apply a slight vignette/darkening inside scope edges
            float vignette = smoothstep(radius, radius - 0.02, dist);
            f_color.rgb *= vignette;
            
            // Composite HUD (crosshairs) on top
            if (hud_col.a > 0.1) {
                f_color = mix(f_color, hud_col, hud_col.a);
            }
        } else if (dist < radius + 0.005) {
            // Scope border
            f_color = vec4(0.0, 0.0, 0.0, 1.0);
        } else {
            // Outside scope: show HUD overlay (which might have scope shadow)
            if (hud_col.a > 0.1) {
                f_color = hud_col;
            } else {
                discard;
            }
        }
    } else {
        // Not zoomed: just show HUD
        f_color = hud_col;
        if (f_color.a < 0.1) {
            discard;
        }
    }
}

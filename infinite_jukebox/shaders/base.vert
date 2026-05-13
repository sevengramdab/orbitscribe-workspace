// Agent 6 — VFX Artist: Fullscreen Vertex Pass-Through
// =====================================================
// ELI5: This shader is like a drafting-table lightbox. You tape a blank
// sheet of vellum to the table so it exactly covers the drawing surface.
// The lightbox doesn't draw anything; it just makes sure the sheet is
// perfectly flat and aligned for the pens (fragment shaders) that come next.

attribute vec2 a_position;
varying vec2 v_uv;

void main () {
    // Convert blueprint coordinates (-1 to +1) to texture coordinates (0 to 1),
    // like switching from architectural scale to full-size construction units.
    v_uv = a_position * 0.5 + 0.5;

    // Place the vertex at the exact corner of the viewport sheet,
    // like pinning vellum to the four corners of a drawing board.
    gl_Position = vec4(a_position, 0.0, 1.0);
}

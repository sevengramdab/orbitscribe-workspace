// Agent 2 — Physicist: Gradient Subtraction (Pressure-Balancing Valve)
// =====================================================================
// ELI5: A pressure-balancing shower valve keeps hot/cold mix steady
// even when someone flushes a toilet. This shader subtracts the
// pressure gradient from velocity so the fluid becomes divergence-free:
// no more backups or overflows in the pipe network.

precision highp float;
varying vec2 v_uv;

uniform sampler2D u_pressure;
uniform sampler2D u_velocity;
uniform vec2 u_texelSize;

void main () {
    // Read pressure left/right and top/bottom.
    float L = texture2D(u_pressure, v_uv - vec2(u_texelSize.x, 0.0)).x;
    float R = texture2D(u_pressure, v_uv + vec2(u_texelSize.x, 0.0)).x;
    float T = texture2D(u_pressure, v_uv + vec2(0.0, u_texelSize.y)).x;
    float B = texture2D(u_pressure, v_uv - vec2(0.0, u_texelSize.y)).x;

    // Subtract gradient from velocity.
    vec2 vel = texture2D(u_velocity, v_uv).xy;
    vel.xy -= 0.5 * vec2(R - L, T - B);

    gl_FragColor = vec4(vel, 0.0, 1.0);
}

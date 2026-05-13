// Agent 2 — Physicist: Semi-Lagrangian Advection
// ================================================
// ELI5: Imagine you're a kayaker on a river. Instead of guessing
// where you'll be tomorrow (forward), you look upstream to see
// where the water came from yesterday (backward). That backward
// lookup is exactly what this shader does for every pixel.

precision highp float;
precision highp sampler2D;

varying vec2 v_uv;

uniform sampler2D u_velocity;    // The river current map
uniform sampler2D u_source;      // The dye or momentum we're carrying
uniform vec2 u_texelSize;        // How big one pixel is in UV space
uniform float u_dt;              // Time step — one frame = one heartbeat
uniform float u_dissipation;     // How fast the dye fades (like sun-bleaching)

void main () {
    // Read the local water velocity at this pixel,
    // like checking the anemometer on your weather station.
    vec2 vel = texture2D(u_velocity, v_uv).xy;

    // Trace BACKWARD to find where this water came from,
    // like reading the current meter and paddling upstream
    // to find the source of the leaf floating past you.
    vec2 prevUV = v_uv - u_dt * vel * u_texelSize;

    // Sample the dye at that upstream location with bilinear filtering,
    // like a smart interpolating multimeter that averages adjacent readings.
    vec4 color = texture2D(u_source, prevUV);

    // Fade the dye slightly: pipe friction bleeds energy over distance.
    gl_FragColor = u_dissipation * color;
}

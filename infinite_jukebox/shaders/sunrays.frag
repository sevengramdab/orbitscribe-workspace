// Agent 6 — VFX Artist: Volumetric Sunrays (God-Rays)
// =====================================================
// ELI5: Stand in a dark warehouse with one skylight. Dust catches
// the beam and you see rays fanning outward. This shader stretches
// bright pixels away from the center and fades them, mimicking light
// scattering through a hazy atmosphere.

precision highp float;
varying vec2 v_uv;

uniform sampler2D u_texture;      // The image we're adding rays to
uniform vec2 u_lightPosition;     // Center of the skylight in UV coordinates
uniform float u_weight;           // How thick the dust/haze is

void main () {
    // Vector from light center to this pixel, like a tape measure
    // pulled from the electrical room to this outlet.
    vec2 delta = v_uv - u_lightPosition;

    // Distance from center, like measuring cable run length.
    float dist = length(delta);

    // Direction toward the light, like the arrow on a conduit plan.
    vec2 dir = delta / (dist + 1e-5);

    // Step size: how far we walk toward the light each sample,
    // like the spacing between junction boxes in a long conduit run.
    float stepSize = dist / 32.0;

    // Accumulator for the light shaft, like a bus bar collecting current.
    vec4 ray = vec4(0.0);

    // Decay factor: light fades as it travels through dust,
    // like voltage drop along a long extension cord.
    float decay = 1.0;

    // March from this pixel back toward the light source,
    // like tracing a wire run back to the main panel.
    vec2 pos = v_uv;
    for (int i = 0; i < 32; i++) {
        pos -= dir * stepSize;

        // Sample the image at this position along the beam.
        vec4 sampleColor = texture2D(u_texture, pos);

        // Only bright areas generate rays: like dust only glowing
        // where the light is strong enough to hit it.
        float brightness = dot(sampleColor.rgb, vec3(0.299, 0.587, 0.114));
        sampleColor *= float(brightness > 0.3) * decay;

        // Add to the accumulator, like wiring another fixture into the circuit.
        ray += sampleColor;

        // Fade the contribution, like voltage drop across each outlet.
        decay *= 0.96;
    }

    // Average the samples so we don't overload the display.
    ray /= 32.0;

    // Read the original image at this pixel.
    vec4 base = texture2D(u_texture, v_uv);

    // Composite the rays on top, scaled by the weight knob.
    gl_FragColor = base + ray * u_weight * 0.25;
}

// Agent 5 / Agent 6 — Display & Final Color Grading
// ==================================================
// ELI5: This is the last dimmer board before the lights hit the stage.
// It takes the raw dye texture, applies exposure (master dimmer),
// tone mapping (compressor/limiter), dithering (grain to hide banding),
// and color temperature (tunable-white LED shift), then outputs sRGB.

precision highp float;
varying vec2 v_uv;

uniform sampler2D u_texture;       // The dye/density field
uniform float u_colorTemp;         // Kelvin (2700–6500) like a tunable LED driver
uniform float u_exposure;          // Master dimmer 0–2
uniform float u_gamma;             // Curve shape (usually 2.2)
uniform float u_ditherStrength;    // How much grain to add
uniform float u_time;              // For subtle animated grain

// Convert color temperature in Kelvin to RGB tint,
// like dialing a Lutron tunable-white fixture from candlelight to daylight.
vec3 kelvinToRGB(float k) {
    float t = k / 1000.0;
    float r = (t <= 6.5) ? 1.0 : 1.292936186062745 * pow(t - 6.5, -0.1332047592);
    float g = (t <= 8.0)
        ? 0.832796096 * pow(t - 2.0, -0.0755148492)
        : 1.35666721 * pow(t - 2.0, 0.234945);
    float b = (t >= 6.5) ? 1.0 : 0.543206789110196 * pow(t - 0.5, 0.454294);
    return clamp(vec3(r, g, b), 0.0, 1.0);
}

void main () {
    // Sample the raw dye at this pixel, like reading a voltage meter.
    vec4 dye = texture2D(u_texture, v_uv);
    vec3 color = dye.rgb;

    // Apply color temperature tint, like gelling a stage light.
    vec3 tint = kelvinToRGB(u_colorTemp);
    color *= tint;

    // Exposure: boost brightness like turning up a smart dimmer.
    color *= u_exposure;

    // Reinhard tone map: compress hot highlights like an HVAC limit switch
    // that caps the output so the furnace never overheats.
    color = color / (1.0 + color * 0.2);

    // Gamma encode: shape the curve like a video projector's LUT.
    color = pow(max(color, vec3(0.0)), vec3(1.0 / u_gamma));

    // Ordered dither: break banding with a Bayer pattern,
    // like tapping a textured roller over wall paint so lap marks disappear.
    // We encode the 4×4 matrix as a mat4 so it works in WebGL1
    // without array-constructor syntax.
    mat4 bayer = mat4(
         0.0 / 16.0 - 0.5,  8.0 / 16.0 - 0.5,  2.0 / 16.0 - 0.5, 10.0 / 16.0 - 0.5,
        12.0 / 16.0 - 0.5,  4.0 / 16.0 - 0.5, 14.0 / 16.0 - 0.5,  6.0 / 16.0 - 0.5,
         3.0 / 16.0 - 0.5, 11.0 / 16.0 - 0.5,  1.0 / 16.0 - 0.5,  9.0 / 16.0 - 0.5,
        15.0 / 16.0 - 0.5,  7.0 / 16.0 - 0.5, 13.0 / 16.0 - 0.5,  5.0 / 16.0 - 0.5
    );
    int by = int(mod(gl_FragCoord.y, 4.0));
    int bx = int(mod(gl_FragCoord.x, 4.0));
    float noise = bayer[by][bx];
    color += noise * u_ditherStrength;

    // Clamp to sRGB range so we don't send overvoltage to the display.
    gl_FragColor = vec4(clamp(color, 0.0, 1.0), 1.0);
}

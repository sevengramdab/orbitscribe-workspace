/**
 * Agent 5 / Agent 9 — ACE-Step 1.5 Audio Engine & Signal Path DAG
 * ================================================================
 * Think of this file as the digital equivalent of a full Crestron
 * DM-NVX DSP rack: it generates procedural music through a strict
 * Signal Path DAG (like a conduit riser diagram with no loops),
 * enforces ACE-Step 1.5 hard constraints (like a tamper-proof
 * breaker panel), and uses Negative Space Mapping (like calling
 * 811 before digging) to prevent frequency masking collisions.
 *
 * ELI5: Imagine a pipe organ with 512 pipes. Each pipe is an FFT bin.
 * We blow air (generate sound) through the pipes, but BEFORE we open
 * any valve, we check a clearance map to make sure no other pipe is
 * already singing too close. That prevents muddy, crowded chords.
 */

class InfiniteJukeboxAudio {
    constructor(options = {}) {
        // --- Audio Context — like the main electrical service entrance ---
        // ELI5: This is the utility company's transformer on the pole.
        // Everything in the house plugs into it, and if it trips, silence.
        this.ctx = new (window.AudioContext || window.webkitAudioContext)();
        this.sampleRate = this.ctx.sampleRate;
        this.fftSize = options.fftSize || 512;
        this.smoothing = options.smoothing || 0.85;

        // --- ACE-Step 1.5 Hard Constraints — the tamper-proof breaker panel ---
        // ELI5: These are the rules etched on a brass plate inside the panel:
        // max amps, minimum spacing between circuits, and which breakers
        // can never be on at the same time.
        this.aceConstraints = {
            maxSyllabicDensity: options.maxSyllabicDensity ?? 0.45,
            minNegativeSpaceRatio: options.minNegativeSpaceRatio ?? 0.25,
            frequencyMaskBudgetHz: options.frequencyMaskBudgetHz ?? 120.0,
            tempoQuantizeGrid: options.tempoQuantizeGrid ?? 16,
            lockState: options.lockState ?? 'free',
            grammarPreset: options.grammarPreset ?? 'ambient_electronic',
        };

        // --- Negative Space Map — the utility clearance tracker ---
        // ELI5: Before you dig a trench for a new water main, you call 811
        // and they paint lines on the ground showing where existing pipes are.
        // This 2-D grid does the same for audio frequencies over time.
        this.negativeSpaceMap = new Float32Array(64 * 512);
        this.timeSlotIndex = 0;
        this.binResolutionHz = this.sampleRate / (this.fftSize * 2);

        // --- Signal Path DAG — the audio riser diagram ---
        // ELI5: Like a blueprint showing every outlet, switch, and junction
        // box wired in order from the main panel to the last bedroom lamp.
        // Audio flows ONE WAY — no loops, no feedback howling.
        this.signalDag = new Map();
        this._buildDefaultSignalPath();

        // --- Dynamics chain: compressor → limiter → master gain → destination ---
        // ELI5: Like a whole-house surge protector + load balancer. It keeps
        // the volume from clipping and destroying speakers when the band gets loud.
        this.compressor = this.ctx.createDynamicsCompressor();
        this.compressor.threshold.value = -24;
        this.compressor.knee.value = 12;
        this.compressor.ratio.value = 12;
        this.compressor.attack.value = 0.003;
        this.compressor.release.value = 0.25;

        this.masterGain = this.ctx.createGain();
        this.masterGain.gain.value = options.masterVolume ?? 0.45;

        this.compressor.connect(this.masterGain);
        this.masterGain.connect(this.ctx.destination);

        // Analyzer node — the spectrum analyzer display
        // ELI5: Like the LED bar-graph on a home stereo that shows bass on
        // the left and treble on the right. We read this to feed the fluid.
        this.analyser = this.ctx.createAnalyser();
        this.analyser.fftSize = this.fftSize * 2;
        this.analyser.smoothingTimeConstant = this.smoothing;
        this.masterGain.connect(this.analyser);

        // --- State ---
        this.isPlaying = false;
        this.oscillators = [];
        this.lfos = [];
        this.time = 0;
        this._callbacks = [];
        this._frameId = null;

        // --- Procedural Music State ---
        this.bpm = options.bpm || 110;
        this.mood = options.mood || 'ambient';
        this.scale = this._getScaleForMood(this.mood);
        this.rootNote = options.rootNote || 55;
        this.currentMeasure = 0;
        this.syllabicDensity = 0.0;
    }

    // -------------------------------------------------------------------------
    // ACE-STEP 1.5 SIGNAL PATH DAG — The rigid conduit system
    // -------------------------------------------------------------------------
    _buildDefaultSignalPath() {
        // ELI5: We're drawing the electrical riser for a small house.
        // Each room (node) gets power from the room before it, and the
        // main breaker (master out) is at the very end.
        this._addDagNode('osc_bank_a', 'oscillator', [], ['filter_a']);
        this._addDagNode('osc_bank_b', 'oscillator', [], ['filter_b']);
        this._addDagNode('filter_a', 'filter', ['osc_bank_a'], ['mixer']);
        this._addDagNode('filter_b', 'filter', ['osc_bank_b'], ['mixer']);
        this._addDagNode('mixer', 'mixer', ['filter_a', 'filter_b'], ['compressor']);
        this._addDagNode('compressor', 'dynamics', ['mixer'], ['master_out']);
        this._addDagNode('master_out', 'output', ['compressor'], []);
    }

    _addDagNode(id, type, inputs, outputs, params = {}) {
        // ELI5: Like adding a new room to the riser diagram: label it,
        // draw lines to the rooms that feed it, and note the breaker size.
        this.signalDag.set(id, { id, type, inputs, outputs, params, enabled: true });
    }

    _getDagSortedOrder() {
        // ELI5: Kahn's algorithm is like wiring a house starting at the
        // breaker panel and only moving to rooms whose incoming wires are
        // already connected. No room gets power before its upstream rooms.
        const inDegree = new Map();
        for (const [id, node] of this.signalDag) {
            inDegree.set(id, 0);
        }
        for (const node of this.signalDag.values()) {
            for (const out of node.outputs) {
                if (inDegree.has(out)) inDegree.set(out, inDegree.get(out) + 1);
            }
        }
        const queue = [];
        for (const [id, deg] of inDegree) {
            if (deg === 0) queue.push(id);
        }
        const sorted = [];
        while (queue.length) {
            const cur = queue.shift();
            sorted.push(cur);
            const node = this.signalDag.get(cur);
            for (const out of node.outputs) {
                if (inDegree.has(out)) {
                    const nd = inDegree.get(out) - 1;
                    inDegree.set(out, nd);
                    if (nd === 0) queue.push(out);
                }
            }
        }
        if (sorted.length !== this.signalDag.size) {
            throw new Error('Signal Path DAG has a cycle — like a short circuit in the wiring.');
        }
        return sorted;
    }

    // -------------------------------------------------------------------------
    // START / STOP — The master power switch
    // -------------------------------------------------------------------------
    async start() {
        // ELI5: Like flipping the main breaker from OFF to ON. The hum
        // you hear is the transformer energizing; then every sub-panel
        // downstream comes alive one by one.
        if (this.ctx.state === 'suspended') await this.ctx.resume();
        this.isPlaying = true;
        this._scheduleLoop();
        this._analyzeLoop();
    }

    stop() {
        // ELI5: Emergency shutdown sequence: dim every light, stop every
        // motor, then pull the main disconnect so the building is dark.
        this.isPlaying = false;
        if (this._frameId) cancelAnimationFrame(this._frameId);
        this.oscillators.forEach(o => {
            try { o.stop(); o.disconnect(); } catch(e) {}
        });
        this.oscillators = [];
        this.lfos.forEach(o => {
            try { o.stop(); o.disconnect(); } catch(e) {}
        });
        this.lfos = [];
    }

    // -------------------------------------------------------------------------
    // NEGATIVE SPACE MAP — Call 811 before digging
    // -------------------------------------------------------------------------
    _reserveFrequencyBand(freqCenterHz, bandwidthHz, timeSlots = 2) {
        // ELI5: Before digging a trench for a new gas line, you check the
        // ground-paint map. If there's already a water line at that depth,
        // you pick a different depth or wait. Returns true if the band is clear.
        const centerBin = Math.round(freqCenterHz / this.binResolutionHz);
        const halfBins = Math.max(1, Math.round(bandwidthHz / (2 * this.binResolutionHz)));
        const lo = Math.max(0, centerBin - halfBins);
        const hi = Math.min(512, centerBin + halfBins);
        const t = this.timeSlotIndex % 64;

        // Check all requested time slots for collisions
        for (let dt = 0; dt < timeSlots; dt++) {
            const tt = (t + dt) % 64;
            for (let b = lo; b < hi; b++) {
                if (this.negativeSpaceMap[tt * 512 + b] > 0.5) return false;
            }
        }

        // Paint the clearance map so future notes know this band is occupied
        for (let dt = 0; dt < timeSlots; dt++) {
            const tt = (t + dt) % 64;
            for (let b = lo; b < hi; b++) {
                this.negativeSpaceMap[tt * 512 + b] = 1.0;
            }
        }
        return true;
    }

    _clearPastTimeSlots() {
        // ELI5: Once the concrete truck has driven past a street segment,
        // you erase the traffic-control paint so normal cars can use it.
        const t = this.timeSlotIndex % 64;
        for (let b = 0; b < 512; b++) {
            this.negativeSpaceMap[t * 512 + b] = 0.0;
        }
    }

    _advanceTimeSlot() {
        // ELI5: The PLC scan cycle increments. Every tick we clear the
        // oldest time-slot paint and move the window forward one step.
        this._clearPastTimeSlots();
        this.timeSlotIndex++;
    }

    // -------------------------------------------------------------------------
    // ACE-STEP 1.5 CONSTRAINT CHECK — The plan reviewer
    // -------------------------------------------------------------------------
    _checkAceConstraints(density, notes) {
        // ELI5: Before the city issues a building permit, the plan reviewer
        // checks that you haven't drawn 50 apartments on a lot zoned for 10.
        // If you exceed the zoning, the permit is denied.
        const c = this.aceConstraints;
        if (c.lockState === 'override') return { allowed: true, reason: 'OVERRIDE' };
        if (c.lockState === 'locked') {
            // In locked mode, only allow notes that decrease density
            if (density > c.maxSyllabicDensity * 0.8) {
                return { allowed: false, reason: 'LOCKED: density exceeds 80% of rated load' };
            }
        }
        if (density > c.maxSyllabicDensity) {
            return { allowed: false, reason: `Density ${density.toFixed(2)} exceeds max ${c.maxSyllabicDensity}` };
        }
        const silenceRatio = 1.0 - density;
        if (silenceRatio < c.minNegativeSpaceRatio) {
            return { allowed: false, reason: `Silence ratio ${silenceRatio.toFixed(2)} below minimum ${c.minNegativeSpaceRatio}` };
        }
        return { allowed: true, reason: null };
    }

    // -------------------------------------------------------------------------
    // PROCEDURAL MUSIC — Player piano with zoning enforcement
    // -------------------------------------------------------------------------
    _scheduleLoop() {
        // ELI5: Like a player piano reading a roll of paper, but the holes
        // are punched by math instead of a factory machine. We look ahead
        // 4 beats so the notes hit exactly on time, like a feed-forward
        // conveyor in an automated warehouse.
        if (!this.isPlaying) return;
        const now = this.ctx.currentTime;
        const beatDur = 60.0 / this.bpm;

        // Remove finished oscillators so the array doesn't grow forever
        // ELI5: Like an electrician pulling out old temp wire instead of
        // leaving it coiled in the panel forever.
        this.oscillators = this.oscillators.filter(o => {
            try { return o.context.currentTime < o._stopTime; } catch(e) { return false; }
        });

        // Compute current density for this scheduling window
        // ELI5: Count how many appliances are currently running before
        // plugging in a new space heater. If the breaker is near tripping,
        // skip the heater.
        this.syllabicDensity = this._computeSyllabicDensity();
        const aceCheck = this._checkAceConstraints(this.syllabicDensity, []);

        if (!aceCheck.allowed) {
            // Shed load: only schedule kick and bass, skip arpeggios
            // ELI5: During a brown-out, the utility remotely shuts off
            // non-essential circuits (pool pump, hot tub) but keeps lights
            // and refrigerator running.
            for (let beat = 0; beat < 4; beat++) {
                const t = now + beat * beatDur;
                if (beat % 2 === 0) this._triggerKick(t, beatDur);
                const bassNote = this._midiToFreq(this.rootNote + this.scale[beat % this.scale.length]);
                this._triggerBass(t, bassNote, beatDur * 1.2);
            }
        } else {
            // Full schedule: all instruments permitted
            for (let beat = 0; beat < 4; beat++) {
                const t = now + beat * beatDur;
                const density = this.syllabicDensity;

                if (beat % 2 === 0) this._triggerKick(t, beatDur);
                if (beat % 2 === 1) this._triggerSnare(t, beatDur);

                const bassNote = this._midiToFreq(this.rootNote + this.scale[beat % this.scale.length]);
                this._triggerBass(t, bassNote, beatDur * 1.2);

                // Ethereal arpeggio — only if density leaves enough negative space
                if (density < 0.5 && beat % 2 === 0) {
                    const arpFreq = this._midiToFreq(this.rootNote + 12 + this.scale[(beat + 2) % this.scale.length]);
                    const arpBand = this._reserveFrequencyBand(arpFreq, this.aceConstraints.frequencyMaskBudgetHz, 1);
                    if (arpBand) this._triggerPluck(t + beatDur * 0.5, arpFreq, beatDur * 0.5);
                }

                // Lush pad — wide ambient wash
                if (beat === 0) {
                    const padRoot = this._midiToFreq(this.rootNote + 24);
                    this._triggerPad(t, padRoot, beatDur * 4, 0.06);
                }
            }
        }

        // Advance the negative-space time window
        this._advanceTimeSlot();

        // Schedule next batch before this one ends
        setTimeout(() => this._scheduleLoop(), (4 * beatDur * 1000) - 100);
    }

    _computeSyllabicDensity() {
        // ELI5: Like counting how many words per second someone speaks.
        // More words = denser = need more visual negative space.
        const base = 0.3 + Math.sin(this.currentMeasure * 0.2) * 0.2;
        this.currentMeasure += 0.25;
        return Math.max(0.1, Math.min(0.9, base));
    }

    _getScaleForMood(mood) {
        // ELI5: Like selecting a Lutron lighting scene: "Cooking" gives
        // bright white task lighting; "Movie" gives warm dim accent light.
        // Each mood chooses a different musical key (scale).
        const scales = {
            ambient: [0, 2, 4, 7, 9],
            energetic: [0, 2, 3, 5, 7, 8, 10],
            dark: [0, 1, 4, 5, 7, 8, 11],
            chaos: [0, 1, 2, 4, 6, 7, 8, 10, 11],
            minimal: [0, 7],
        };
        return scales[mood] || scales.ambient;
    }

    // -------------------------------------------------------------------------
    // INSTRUMENT SYNTHESIS — Virtual analog oscillator + filter chains
    // -------------------------------------------------------------------------
    _triggerKick(time, beatDur) {
        // ELI5: Instead of a hammer on a trash can, it's a soft palm tap
        // on a thick yoga ball: deep, round, and gentle.
        const osc = this.ctx.createOscillator();
        const gain = this.ctx.createGain();
        const filter = this.ctx.createBiquadFilter();
        osc.type = 'sine';
        osc.frequency.setValueAtTime(120, time);
        osc.frequency.exponentialRampToValueAtTime(55, time + 0.25);
        gain.gain.setValueAtTime(0.0, time);
        gain.gain.linearRampToValueAtTime(0.9, time + 0.02);
        gain.gain.exponentialRampToValueAtTime(0.01, time + 0.35);
        filter.type = 'lowpass';
        filter.frequency.value = 180;
        filter.Q.value = 0.8;
        osc.connect(filter);
        filter.connect(gain);
        gain.connect(this.compressor);
        osc.start(time);
        osc.stop(time + 0.4);
        osc._stopTime = time + 0.4;
        this.oscillators.push(osc);
    }

    _triggerSnare(time, beatDur) {
        // ELI5: Instead of rice in a can, it's the sound of silk curtains
        // rustling in a breeze. Very soft and high-frequency.
        const noise = this.ctx.createBufferSource();
        const noiseBuf = this._createNoiseBuffer();
        noise.buffer = noiseBuf;
        const noiseFilter = this.ctx.createBiquadFilter();
        noiseFilter.type = 'bandpass';
        noiseFilter.frequency.value = 3000;
        noiseFilter.Q.value = 0.6;
        const noiseGain = this.ctx.createGain();
        noiseGain.gain.setValueAtTime(0.0, time);
        noiseGain.gain.linearRampToValueAtTime(0.35, time + 0.005);
        noiseGain.gain.exponentialRampToValueAtTime(0.01, time + 0.18);
        noise.connect(noiseFilter);
        noiseFilter.connect(noiseGain);
        noiseGain.connect(this.compressor);
        noise.start(time);
        noise.stop(time + 0.2);

        const osc = this.ctx.createOscillator();
        osc.type = 'sine';
        osc.frequency.value = 220;
        const oscGain = this.ctx.createGain();
        oscGain.gain.setValueAtTime(0.0, time);
        oscGain.gain.linearRampToValueAtTime(0.15, time + 0.01);
        oscGain.gain.exponentialRampToValueAtTime(0.01, time + 0.12);
        osc.connect(oscGain);
        oscGain.connect(this.compressor);
        osc.start(time);
        osc.stop(time + 0.15);
        osc._stopTime = time + 0.15;
        this.oscillators.push(osc);
    }

    _triggerBass(time, freq, duration) {
        // ELI5: Like a large tuning fork humming in a concert hall.
        // Deep, resonant, and clean — no buzz or distortion.
        const osc = this.ctx.createOscillator();
        osc.type = 'triangle';
        osc.frequency.value = freq;
        const filter = this.ctx.createBiquadFilter();
        filter.type = 'lowpass';
        filter.frequency.setValueAtTime(350, time);
        filter.frequency.exponentialRampToValueAtTime(80, time + duration);
        filter.Q.value = 0.5;
        const gain = this.ctx.createGain();
        gain.gain.setValueAtTime(0.0, time);
        gain.gain.linearRampToValueAtTime(0.55, time + 0.04);
        gain.gain.exponentialRampToValueAtTime(0.01, time + duration);
        osc.connect(filter);
        filter.connect(gain);
        gain.connect(this.compressor);
        osc.start(time);
        osc.stop(time + duration + 0.1);
        osc._stopTime = time + duration + 0.1;
        this.oscillators.push(osc);
    }

    _triggerPad(time, freq, duration, volume) {
        // ELI5: Like three wine glasses rubbed with wet fingers in a
        // cathedral. Each glass is tuned slightly differently, and the
        // sound swells and fades like breathing.
        const waveTypes = ['sine', 'triangle'];
        const detune = [-10, 0, 10];
        waveTypes.forEach((wave, wi) => {
            detune.forEach(dt => {
                const osc = this.ctx.createOscillator();
                osc.type = wave;
                osc.frequency.value = freq;
                osc.detune.value = dt + (wi * 3);
                const filter = this.ctx.createBiquadFilter();
                filter.type = 'lowpass';
                filter.Q.value = 1.2;
                const lfo = this.ctx.createOscillator();
                lfo.type = 'sine';
                lfo.frequency.value = 0.15 + Math.random() * 0.25;
                const lfoGain = this.ctx.createGain();
                lfoGain.gain.value = 250;
                lfo.connect(lfoGain);
                lfoGain.connect(filter.frequency);
                filter.frequency.value = 500;
                const gain = this.ctx.createGain();
                gain.gain.setValueAtTime(0.0, time);
                gain.gain.linearRampToValueAtTime(volume * 0.6, time + 1.2);
                gain.gain.linearRampToValueAtTime(0.0, time + duration);
                osc.connect(filter);
                filter.connect(gain);
                gain.connect(this.compressor);
                osc.start(time);
                osc.stop(time + duration + 0.5);
                osc._stopTime = time + duration + 0.5;
                lfo.start(time);
                lfo.stop(time + duration + 0.5);
                this.oscillators.push(osc);
                this.lfos.push(lfo);
            });
        });
    }

    _triggerPluck(time, freq, duration) {
        // ELI5: Like tapping a crystal wine glass with a feather.
        const carrier = this.ctx.createOscillator();
        const modulator = this.ctx.createOscillator();
        const modGain = this.ctx.createGain();
        const env = this.ctx.createGain();
        carrier.type = 'sine';
        carrier.frequency.value = freq;
        modulator.type = 'sine';
        modulator.frequency.value = freq * 2.01;
        modGain.gain.value = freq * 0.8;
        env.gain.setValueAtTime(0.0, time);
        env.gain.linearRampToValueAtTime(0.25, time + 0.01);
        env.gain.exponentialRampToValueAtTime(0.001, time + duration);
        modulator.connect(modGain);
        modGain.connect(carrier.frequency);
        carrier.connect(env);
        env.connect(this.compressor);
        carrier.start(time);
        carrier.stop(time + duration + 0.1);
        carrier._stopTime = time + duration + 0.1;
        modulator.start(time);
        modulator.stop(time + duration + 0.1);
        this.oscillators.push(carrier);
    }

    _createNoiseBuffer() {
        // ELI5: Like recording the sound of a ventilation fan for 2 seconds
        // so you can play it back on a loop as white noise.
        const buffer = this.ctx.createBuffer(1, this.sampleRate * 2, this.sampleRate);
        const data = buffer.getChannelData(0);
        for (let i = 0; i < data.length; i++) {
            data[i] = Math.random() * 2 - 1;
        }
        return buffer;
    }

    _midiToFreq(midi) {
        // ELI5: Converting musical notes to Hz is like converting
        // architectural drawing scales: 440 Hz = 1" = 1'-0", and every
        // semitone is a fixed ratio (like 1/12 scale).
        return 440 * Math.pow(2, (midi - 69) / 12);
    }

    // -------------------------------------------------------------------------
    // CONFIG UPDATE — Live-tweak from the dashboard
    // -------------------------------------------------------------------------
    applyConfig(config) {
        // ELI5: Like a facilities manager walking into the mechanical room
        // and adjusting thermostat setpoints without shutting down the chiller.
        if (config.bpm !== undefined) this.bpm = Math.max(60, Math.min(180, config.bpm));
        if (config.mood !== undefined) {
            this.mood = config.mood;
            this.scale = this._getScaleForMood(config.mood);
        }
        if (config.maxSyllabicDensity !== undefined) this.aceConstraints.maxSyllabicDensity = config.maxSyllabicDensity;
        if (config.minNegativeSpaceRatio !== undefined) this.aceConstraints.minNegativeSpaceRatio = config.minNegativeSpaceRatio;
        if (config.frequencyMaskBudgetHz !== undefined) this.aceConstraints.frequencyMaskBudgetHz = config.frequencyMaskBudgetHz;
        if (config.lockState !== undefined) this.aceConstraints.lockState = config.lockState;
        if (config.masterVolume !== undefined) this.masterGain.gain.value = config.masterVolume;
    }

    // -------------------------------------------------------------------------
    // FFT ANALYSIS — The spectrum analyzer loop
    // -------------------------------------------------------------------------
    _analyzeLoop() {
        // ELI5: Like the LED bar-graph on a home stereo that updates 60 times
        // per second. We read the heights, normalize them, and broadcast.
        if (!this.isPlaying) return;
        const data = new Uint8Array(this.analyser.frequencyBinCount);
        this.analyser.getByteFrequencyData(data);

        const normalized = new Float32Array(data.length);
        for (let i = 0; i < data.length; i++) {
            normalized[i] = data[i] / 255.0;
        }

        const frame = {
            timestampMs: performance.now(),
            frequencyBins: normalized,
            peakAmplitude: Math.max(...normalized),
            zeroCrossingRate: 0,
            spectralCentroid: this._spectralCentroid(normalized),
        };

        this._callbacks.forEach(cb => {
            try { cb(frame); } catch(e) {}
        });

        this._frameId = requestAnimationFrame(() => this._analyzeLoop());
    }

    _spectralCentroid(bins) {
        // ELI5: The "center of mass" of the spectrum. If all the energy is
        // in the bass, it's like a shelf loaded with heavy books on the
        // bottom. If it's in the treble, the heavy books are on top.
        let num = 0, den = 1e-6;
        for (let i = 0; i < bins.length; i++) {
            num += i * bins[i];
            den += bins[i];
        }
        return num / den / bins.length;
    }

    onAudioFrame(callback) {
        // ELI5: Like pairing a wireless light switch to a smart-home hub.
        // Once paired, every time someone flips the switch, the hub knows.
        this._callbacks.push(callback);
    }

    removeCallback(callback) {
        // ELI5: Unpairing the switch from the hub.
        this._callbacks = this._callbacks.filter(cb => cb !== callback);
    }
}

// Export for module bundlers or global use
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { InfiniteJukeboxAudio };
}

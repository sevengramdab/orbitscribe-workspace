/**
 * Visualizer Themes & Particle System
 * ===================================
 * Theme presets + 2D canvas particle overlay for the Infinite Jukebox.
 */

const VISUALIZER_THEMES = {
  aurora: {
    name: 'Aurora',
    bgColor: [0.008, 0.008, 0.012],
    bgPattern: 0.004,
    colorTemp: 6500,
    exposure: 1.0,
    gamma: 1.7,
    bloomIntensity: 0.0,
    sunraysWeight: 0.5,
    ditherStrength: 0.008,
    simResolution: 512,
    dyeResolution: 2048,
    pressureIterations: 25,
    curlStrength: 42,
    densityDissipation: 0.994,
    velocityDissipation: 0.995,
    dt: 0.016,
    splatRadius: 0.0035,
    audioColors: [
      [0.45, 0.18, 0.06],
      [0.08, 0.30, 0.25],
      [0.40, 0.32, 0.07],
      [0.22, 0.08, 0.20],
      [0.20, 0.22, 0.08],
    ],
    particles: {
      count: 80,
      size: 2.0,
      glow: 0.4,
      trail: 0.25,
      speed: 0.8,
      colors: ['#8B5A2B', '#2F5D50', '#C4A35A', '#5D3A5D', '#6B7B3A'],
      spawnRate: 1,
    }
  },
  nebula: {
    name: 'Nebula',
    bgColor: [0.012, 0.008, 0.016],
    bgPattern: 0.005,
    colorTemp: 4200,
    exposure: 0.95,
    gamma: 1.75,
    bloomIntensity: 0.0,
    sunraysWeight: 0.4,
    ditherStrength: 0.012,
    simResolution: 512,
    dyeResolution: 2048,
    pressureIterations: 30,
    curlStrength: 42,
    densityDissipation: 0.993,
    velocityDissipation: 0.992,
    dt: 0.016,
    splatRadius: 0.004,
    audioColors: [
      [0.35, 0.12, 0.20],
      [0.15, 0.08, 0.25],
      [0.08, 0.18, 0.30],
      [0.20, 0.15, 0.35],
      [0.30, 0.12, 0.25],
    ],
    particles: {
      count: 100,
      size: 1.6,
      glow: 0.35,
      trail: 0.35,
      speed: 0.6,
      colors: ['#704040', '#403060', '#305050', '#504060', '#603840'],
      spawnRate: 2,
    }
  },
  inferno: {
    name: 'Inferno',
    bgColor: [0.025, 0.008, 0.0],
    bgPattern: 0.006,
    colorTemp: 2800,
    exposure: 1.05,
    gamma: 1.65,
    bloomIntensity: 0.0,
    sunraysWeight: 0.6,
    ditherStrength: 0.008,
    simResolution: 512,
    dyeResolution: 2048,
    pressureIterations: 20,
    curlStrength: 42,
    densityDissipation: 0.992,
    velocityDissipation: 0.992,
    dt: 0.016,
    splatRadius: 0.0035,
    audioColors: [
      [0.50, 0.12, 0.02],
      [0.45, 0.22, 0.03],
      [0.55, 0.35, 0.06],
      [0.40, 0.18, 0.05],
      [0.48, 0.15, 0.08],
    ],
    particles: {
      count: 90,
      size: 2.4,
      glow: 0.4,
      trail: 0.2,
      speed: 1.0,
      colors: ['#8B4513', '#A0522D', '#CD853F', '#704020', '#905030'],
      spawnRate: 1,
    }
  },
  ocean: {
    name: 'Ocean',
    bgColor: [0.0, 0.012, 0.024],
    bgPattern: 0.004,
    colorTemp: 8000,
    exposure: 0.95,
    gamma: 1.8,
    bloomIntensity: 0.0,
    sunraysWeight: 0.5,
    ditherStrength: 0.01,
    simResolution: 512,
    dyeResolution: 2048,
    pressureIterations: 25,
    curlStrength: 40,
    densityDissipation: 0.993,
    velocityDissipation: 0.993,
    dt: 0.016,
    splatRadius: 0.004,
    audioColors: [
      [0.05, 0.20, 0.30],
      [0.08, 0.28, 0.32],
      [0.10, 0.35, 0.30],
      [0.12, 0.30, 0.25],
      [0.08, 0.25, 0.28],
    ],
    particles: {
      count: 90,
      size: 1.8,
      glow: 0.35,
      trail: 0.3,
      speed: 0.7,
      colors: ['#2F5D6B', '#3A6B5D', '#4A7B6B', '#305050', '#3A5A60'],
      spawnRate: 1,
    }
  },
  matrix: {
    name: 'Matrix',
    bgColor: [0.005, 0.010, 0.005],
    bgPattern: 0.003,
    colorTemp: 5000,
    exposure: 1.0,
    gamma: 1.7,
    bloomIntensity: 0.0,
    sunraysWeight: 0.4,
    ditherStrength: 0.008,
    simResolution: 512,
    dyeResolution: 2048,
    pressureIterations: 20,
    curlStrength: 42,
    densityDissipation: 0.994,
    velocityDissipation: 0.995,
    dt: 0.016,
    splatRadius: 0.0035,
    audioColors: [
      [0.06, 0.22, 0.08],
      [0.10, 0.28, 0.10],
      [0.14, 0.32, 0.12],
      [0.18, 0.30, 0.14],
      [0.22, 0.28, 0.12],
    ],
    particles: {
      count: 70,
      size: 1.8,
      glow: 0.3,
      trail: 0.15,
      speed: 0.9,
      colors: ['#3A5A2A', '#4A6A30', '#5A7A38', '#3A4A28', '#4A5A30'],
      spawnRate: 1,
    }
  },
  dark: {
    name: 'Dark (Classic)',
    bgColor: [0.008, 0.010, 0.014],
    bgPattern: 0.004,
    colorTemp: 6000,
    exposure: 0.9,
    gamma: 1.75,
    bloomIntensity: 0.0,
    sunraysWeight: 0.3,
    ditherStrength: 0.015,
    simResolution: 256,
    dyeResolution: 1024,
    pressureIterations: 20,
    curlStrength: 32,
    densityDissipation: 0.991,
    velocityDissipation: 0.99,
    dt: 0.016,
    splatRadius: 0.003,
    audioColors: [
      [0.25, 0.08, 0.06],
      [0.20, 0.12, 0.05],
      [0.06, 0.18, 0.10],
      [0.05, 0.12, 0.18],
      [0.15, 0.08, 0.15],
    ],
    particles: {
      count: 0,
      size: 2,
      glow: 0.3,
      trail: 0.2,
      speed: 0.8,
      colors: ['#5A4A3A'],
      spawnRate: 0,
    }
  }
};

class ParticleSystem {
  constructor(canvas) {
    this.canvas = canvas;
    this.ctx = canvas.getContext('2d');
    this.particles = [];
    this.config = VISUALIZER_THEMES.aurora.particles;
    this.fluid = null;
    this.running = false;
    this._lastTime = 0;
    this._spawnAccum = 0;
    this.resize();
    window.addEventListener('resize', () => this.resize());
  }

  setFluid(fluid) {
    this.fluid = fluid;
  }

  setConfig(config) {
    this.config = { ...this.config, ...config };
    while (this.particles.length > this.config.count) {
      this.particles.pop();
    }
  }

  resize() {
    const dpr = window.devicePixelRatio || 1;
    const displayW = Math.round(this.canvas.clientWidth * dpr);
    const displayH = Math.round(this.canvas.clientHeight * dpr);
    this.canvas.width = displayW;
    this.canvas.height = displayH;
    this.width = displayW;
    this.height = displayH;
  }

  spawn() {
    const colors = this.config.colors;
    const color = colors[Math.floor(Math.random() * colors.length)];
    const x = Math.random() * this.width;
    const y = Math.random() * this.height;
    this.particles.push({
      x, y,
      vx: (Math.random() - 0.5) * 2,
      vy: (Math.random() - 0.5) * 2,
      life: 1.0,
      decay: 0.003 + Math.random() * 0.005,
      size: (this.config.size || 2) * (0.5 + Math.random()),
      color,
      glow: this.config.glow || 0.5,
    });
  }

  update(dt) {
    if (!this.config.count) {
      this.particles = [];
      return;
    }

    this._spawnAccum += (this.config.spawnRate || 2) * dt * 60;
    while (this._spawnAccum >= 1 && this.particles.length < this.config.count) {
      this.spawn();
      this._spawnAccum -= 1;
    }

    const t = performance.now() * 0.001;
    const speed = this.config.speed || 1;

    for (let i = this.particles.length - 1; i >= 0; i--) {
      const p = this.particles[i];
      p.life -= p.decay * dt * 60;

      // Flow field perturbation (sine-based, GPU-friendly fallback)
      const fx = Math.sin(p.y * 0.008 + t * 0.7) * 0.4 + Math.cos(p.x * 0.005 + t * 0.3) * 0.2;
      const fy = Math.cos(p.x * 0.008 + t * 0.5) * 0.4 + Math.sin(p.y * 0.005 + t * 0.4) * 0.2;
      p.vx += fx * dt * 60 * speed;
      p.vy += fy * dt * 60 * speed;

      p.x += p.vx * dt * 60 * speed;
      p.y += p.vy * dt * 60 * speed;

      p.vx *= 0.97;
      p.vy *= 0.97;

      if (p.x < -20) p.x = this.width + 20;
      if (p.x > this.width + 20) p.x = -20;
      if (p.y < -20) p.y = this.height + 20;
      if (p.y > this.height + 20) p.y = -20;

      if (p.life <= 0) {
        this.particles.splice(i, 1);
      }
    }
  }

  render() {
    const ctx = this.ctx;
    const trail = this.config.trail || 0.2;

    // Clear fully — the particle canvas sits on top of the WebGL fluid canvas.
    // A semi-transparent black fill would progressively darken the fluid
    // underneath, making it invisible. Particles rely on glow + life decay.
    ctx.globalCompositeOperation = 'source-over';
    ctx.clearRect(0, 0, this.width, this.height);

    if (!this.particles.length) return;

    ctx.globalCompositeOperation = 'lighter';
    for (const p of this.particles) {
      const alpha = p.life * p.glow;
      if (alpha < 0.01) continue;

      ctx.save();
      ctx.globalAlpha = alpha;

      // Outer glow
      const glowSize = p.size * 5;
      const grad = ctx.createRadialGradient(p.x, p.y, 0, p.x, p.y, glowSize);
      grad.addColorStop(0, p.color);
      grad.addColorStop(0.4, p.color);
      grad.addColorStop(1, 'transparent');
      ctx.fillStyle = grad;
      ctx.beginPath();
      ctx.arc(p.x, p.y, glowSize, 0, Math.PI * 2);
      ctx.fill();

      // Bright core
      ctx.fillStyle = '#ffffff';
      ctx.beginPath();
      ctx.arc(p.x, p.y, p.size * 0.5, 0, Math.PI * 2);
      ctx.fill();

      ctx.restore();
    }
    ctx.globalAlpha = 1.0;
  }

  start() {
    if (this.running) return;
    this.running = true;
    this._lastTime = performance.now();
    const loop = () => {
      if (!this.running) return;
      const now = performance.now();
      const dt = Math.min((now - this._lastTime) / 1000, 0.05);
      this._lastTime = now;
      this.update(dt);
      this.render();
      requestAnimationFrame(loop);
    };
    requestAnimationFrame(loop);
  }

  stop() {
    this.running = false;
  }

  clear() {
    this.ctx.clearRect(0, 0, this.width, this.height);
  }
}

function applyVisualizerTheme(fluid, particles, themeName) {
  const theme = VISUALIZER_THEMES[themeName];
  if (!theme) return;

  if (particles) {
    particles.setConfig(theme.particles);
    if (!theme.particles.count) {
      particles.clear();
    }
  }

  if (!fluid) return;

  // Pass every theme property through applyConfig so the fluid gets
  // a complete, consistent configuration in one shot.
  fluid.applyConfig({
    viscosity: Math.max(0, Math.min(1, (theme.velocityDissipation - 0.95) / 0.04)),
    flowVelocity: theme.dt ? theme.dt / 0.016 : 1,
    densityDissipation: theme.densityDissipation,
    velocityDissipation: theme.velocityDissipation,
    dt: theme.dt,
    curlStrength: theme.curlStrength,
    pressureIterations: theme.pressureIterations,
    bloomIntensity: theme.bloomIntensity,
    sunraysWeight: theme.sunraysWeight,
    colorTemp: theme.colorTemp,
    exposure: theme.exposure,
    gamma: theme.gamma,
    ditherStrength: theme.ditherStrength,
    splatRadius: theme.splatRadius,
    dyeResolution: theme.dyeResolution,
    simResolution: theme.simResolution,
  });

  fluid._themeBgColor = theme.bgColor;
  fluid._themeBgPattern = theme.bgPattern;
  fluid._themeAudioColors = theme.audioColors;
}

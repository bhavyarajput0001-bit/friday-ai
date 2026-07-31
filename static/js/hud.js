/* ══════════════════════════════════════════════════════════════════════════════
   FRIDAY AI — Center Hologram Canvas Animation
   Multiple presets: concentric rings (ticks/arcs/dots), radar sweep, glow, particles
   ══════════════════════════════════════════════════════════════════════════════ */

const HUD = (() => {
    let canvas, ctx, w, h, cx, cy;
    let animFrame;
    let startTime = Date.now();
    let state = 'idle'; // idle, listening, processing
    let particles = [];
    let presetName = 'core';
    let preset = null;

    // Per-state color palettes for each hologram preset
    const PALETTES = {
        cyan:    { idle: {r:0,g:212,b:255},  listening: {r:0,g:255,b:136}, processing: {r:255,g:179,b:0} },
        green:   { idle: {r:0,g:255,b:136},  listening: {r:0,g:212,b:255}, processing: {r:255,g:179,b:0} },
        violet:  { idle: {r:155,g:123,b:255}, listening: {r:0,g:255,b:136}, processing: {r:255,g:179,b:0} },
        amber:   { idle: {r:255,g:179,b:0},   listening: {r:0,g:255,b:136}, processing: {r:255,g:71,b:87} },
        magenta: { idle: {r:255,g:80,b:200},  listening: {r:0,g:212,b:255}, processing: {r:255,g:179,b:0} },
        red:     { idle: {r:255,g:71,b:87},   listening: {r:0,g:255,b:136}, processing: {r:255,g:179,b:0} },
    };

    // Preset definitions. style: ticks | arcs | dots
    const PRESETS = {
        core: {
            name: 'Core', palette: 'cyan', style: 'ticks', sweep: false, particles: 40,
            rings: [
                { rFactor: 0.36, speed: 0.0003, dir: 1,  ticks: 72, tickLen: 8,  tickWidth: 1.5, dashGap: true },
                { rFactor: 0.30, speed: 0.0005, dir: -1, ticks: 48, tickLen: 12, tickWidth: 1,   dashGap: false },
                { rFactor: 0.24, speed: 0.0004, dir: 1,  ticks: 36, tickLen: 6,  tickWidth: 2,   dashGap: true },
            ],
        },
        arc: {
            name: 'Arc', palette: 'violet', style: 'arcs', sweep: false, particles: 26,
            rings: [
                { rFactor: 0.34, speed: 0.0002, dir: 1,  ticks: 3, tickLen: 0, tickWidth: 2.5, dashGap: false },
                { rFactor: 0.28, speed: -0.00045, dir: -1, ticks: 5, tickLen: 0, tickWidth: 1.5, dashGap: false },
                { rFactor: 0.20, speed: 0.0006, dir: 1,  ticks: 2, tickLen: 0, tickWidth: 4,   dashGap: false },
            ],
        },
        radar: {
            name: 'Radar', palette: 'green', style: 'ticks', sweep: true, particles: 30,
            rings: [
                { rFactor: 0.34, speed: 0.0004, dir: 1, ticks: 96, tickLen: 4, tickWidth: 1, dashGap: true },
                { rFactor: 0.26, speed: -0.00025, dir: -1, ticks: 48, tickLen: 10, tickWidth: 1.2, dashGap: false },
            ],
        },
        nebula: {
            name: 'Nebula', palette: 'magenta', style: 'dots', sweep: false, particles: 90,
            rings: [
                { rFactor: 0.36, speed: 0.00012, dir: 1, ticks: 60, tickLen: 3, tickWidth: 2, dashGap: true },
                { rFactor: 0.30, speed: -0.0002, dir: -1, ticks: 48, tickLen: 3, tickWidth: 1.5, dashGap: false },
                { rFactor: 0.24, speed: 0.0003, dir: 1, ticks: 36, tickLen: 3, tickWidth: 1, dashGap: false },
            ],
        },
        matrix: {
            name: 'Matrix', palette: 'green', style: 'ticks', sweep: false, particles: 60,
            rings: [
                { rFactor: 0.36, speed: 0.0005, dir: 1, ticks: 96, tickLen: 6, tickWidth: 1, dashGap: true },
                { rFactor: 0.30, speed: 0.0007, dir: 1, ticks: 72, tickLen: 8, tickWidth: 0.8, dashGap: false },
                { rFactor: 0.24, speed: -0.0004, dir: -1, ticks: 48, tickLen: 5, tickWidth: 1.2, dashGap: false },
            ],
        },
        pulse: {
            name: 'Pulse', palette: 'amber', style: 'arcs', sweep: false, particles: 18,
            rings: [
                { rFactor: 0.30, speed: 0.0008, dir: 1, ticks: 1, tickLen: 0, tickWidth: 3, dashGap: false },
                { rFactor: 0.24, speed: -0.0008, dir: -1, ticks: 1, tickLen: 0, tickWidth: 5, dashGap: false },
            ],
        },
    };

    function init() {
        canvas = document.getElementById('hologramCanvas');
        if (!canvas) return;
        ctx = canvas.getContext('2d');
        preset = PRESETS[presetName] || PRESETS.core;
        _resize();
        window.addEventListener('resize', _resize);
        _initParticles(preset.particles);
        _animate();
    }

    function setState(newState) {
        state = newState;
    }

    function setPreset(name) {
        if (!PRESETS[name]) return false;
        presetName = name;
        preset = PRESETS[name];
        if (canvas && ctx) {
            startTime = Date.now();
            _initParticles(preset.particles);
        }
        return true;
    }

    function getPresets() { return PRESETS; }
    function getPreset() { return presetName; }

    function _resize() {
        const rect = canvas.parentElement.getBoundingClientRect();
        const dpr = window.devicePixelRatio || 1;
        w = rect.width;
        h = rect.height;
        canvas.width = w * dpr;
        canvas.height = h * dpr;
        canvas.style.width = w + 'px';
        canvas.style.height = h + 'px';
        ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
        cx = w / 2;
        cy = h / 2;
    }

    function _getAccentColor() {
        const pal = (preset && PALETTES[preset.palette]) || PALETTES.cyan;
        return pal[state] || pal.idle;
    }

    function _initParticles(count) {
        particles = [];
        for (let i = 0; i < count; i++) {
            particles.push({
                angle: Math.random() * Math.PI * 2,
                radius: 0.2 + Math.random() * 0.22,
                speed: (0.0002 + Math.random() * 0.0004) * (Math.random() > 0.5 ? 1 : -1),
                size: 0.5 + Math.random() * 1.5,
                opacity: 0.2 + Math.random() * 0.5,
                twinkleSpeed: 0.001 + Math.random() * 0.003,
            });
        }
    }

    function _drawRing(ring, r, angle, alpha, accent, t) {
        const style = preset.style;
        const isArcs = style === 'arcs';
        const isDots = style === 'dots';

        ctx.save();
        ctx.translate(cx, cy);
        ctx.rotate(angle);

        if (isArcs) {
            const segments = Math.max(ring.ticks, 1);
            const seg = (Math.PI * 2) / segments;
            for (let i = 0; i < segments; i++) {
                const a0 = i * seg;
                const a1 = a0 + seg * 0.68;
                ctx.beginPath();
                ctx.arc(0, 0, r, a0, a1);
                ctx.strokeStyle = `rgba(${accent.r},${accent.g},${accent.b},${alpha * 0.75})`;
                ctx.lineWidth = ring.tickWidth;
                ctx.lineCap = 'round';
                ctx.stroke();
            }
        } else if (isDots) {
            for (let i = 0; i < ring.ticks; i++) {
                if (ring.dashGap && (i % 3 === 0)) continue;
                const a = (i / ring.ticks) * Math.PI * 2;
                const tickAlpha = alpha * (0.3 + 0.7 * Math.abs(Math.sin(a * 2 + t * 0.002)));
                ctx.beginPath();
                ctx.arc(Math.cos(a) * r, Math.sin(a) * r, ring.tickWidth * 0.9, 0, Math.PI * 2);
                ctx.fillStyle = `rgba(${accent.r},${accent.g},${accent.b},${tickAlpha})`;
                ctx.fill();
            }
        } else {
            for (let i = 0; i < ring.ticks; i++) {
                const a = (i / ring.ticks) * Math.PI * 2;
                if (ring.dashGap && (i % 3 === 0)) continue;
                const tickAlpha = alpha * (0.4 + 0.6 * Math.abs(Math.sin(a * 2 + t * 0.002)));
                const isAccent = i % (ring.ticks / 4) === 0;
                const len = isAccent ? ring.tickLen * 1.8 : ring.tickLen;
                const iR = r - len;

                ctx.beginPath();
                ctx.moveTo(Math.cos(a) * iR, Math.sin(a) * iR);
                ctx.lineTo(Math.cos(a) * r, Math.sin(a) * r);
                ctx.strokeStyle = `rgba(${accent.r},${accent.g},${accent.b},${isAccent ? alpha : tickAlpha})`;
                ctx.lineWidth = isAccent ? ring.tickWidth * 1.5 : ring.tickWidth;
                ctx.stroke();
            }
        }

        // Faint guide circle
        if (!isArcs) {
            ctx.beginPath();
            ctx.arc(0, 0, r, 0, Math.PI * 2);
            ctx.strokeStyle = `rgba(${accent.r},${accent.g},${accent.b},${alpha * 0.25})`;
            ctx.lineWidth = 1;
            ctx.stroke();
        }

        ctx.restore();
    }

    function _animate() {
        const t = Date.now() - startTime;
        ctx.clearRect(0, 0, w, h);

        const accent = _getAccentColor();
        const minDim = Math.min(w, h);

        // ── Outer glow ──
        const glowR = minDim * 0.38;
        const glow = ctx.createRadialGradient(cx, cy, glowR * 0.3, cx, cy, glowR);
        glow.addColorStop(0, `rgba(${accent.r},${accent.g},${accent.b},0.04)`);
        glow.addColorStop(0.5, `rgba(${accent.r},${accent.g},${accent.b},0.012)`);
        glow.addColorStop(1, 'transparent');
        ctx.fillStyle = glow;
        ctx.fillRect(0, 0, w, h);

        // ── Rings ──
        preset.rings.forEach((ring, ri) => {
            const r = minDim * ring.rFactor;
            const angle = t * ring.speed * ring.dir;
            const alpha = 0.3 + 0.15 * Math.sin(t * 0.001 + ri);
            _drawRing(ring, r, angle, alpha, accent, t);
        });

        // ── Radar sweep line ──
        if (preset.sweep) {
            const sa = t * 0.0008;
            const sweepR = minDim * 0.36;
            ctx.save();
            ctx.translate(cx, cy);
            ctx.rotate(sa);
            const sweepGrad = ctx.createLinearGradient(0, 0, sweepR, 0);
            sweepGrad.addColorStop(0, `rgba(${accent.r},${accent.g},${accent.b},0.0)`);
            sweepGrad.addColorStop(1, `rgba(${accent.r},${accent.g},${accent.b},0.55)`);
            ctx.beginPath();
            ctx.moveTo(0, 0);
            ctx.lineTo(sweepR, 0);
            ctx.strokeStyle = sweepGrad;
            ctx.lineWidth = 1.5;
            ctx.shadowColor = `rgba(${accent.r},${accent.g},${accent.b},0.6)`;
            ctx.shadowBlur = 12;
            ctx.stroke();
            ctx.restore();
        }

        // ── Inner pulsing circle ──
        const pulseR = minDim * 0.08 + Math.sin(t * 0.002) * minDim * 0.01;
        const innerGlow = ctx.createRadialGradient(cx, cy, 0, cx, cy, pulseR);
        innerGlow.addColorStop(0, `rgba(${accent.r},${accent.g},${accent.b},0.12)`);
        innerGlow.addColorStop(0.7, `rgba(${accent.r},${accent.g},${accent.b},0.04)`);
        innerGlow.addColorStop(1, 'transparent');
        ctx.fillStyle = innerGlow;
        ctx.beginPath();
        ctx.arc(cx, cy, pulseR, 0, Math.PI * 2);
        ctx.fill();

        ctx.beginPath();
        ctx.arc(cx, cy, pulseR, 0, Math.PI * 2);
        ctx.strokeStyle = `rgba(${accent.r},${accent.g},${accent.b},0.3)`;
        ctx.lineWidth = 1.5;
        ctx.stroke();

        // ── Particles ──
        particles.forEach(p => {
            p.angle += p.speed;
            const pr = minDim * p.radius;
            const px = cx + Math.cos(p.angle) * pr;
            const py = cy + Math.sin(p.angle) * pr;
            const twinkle = 0.3 + 0.7 * Math.abs(Math.sin(t * p.twinkleSpeed));

            ctx.beginPath();
            ctx.arc(px, py, p.size, 0, Math.PI * 2);
            ctx.fillStyle = `rgba(${accent.r},${accent.g},${accent.b},${p.opacity * twinkle})`;
            ctx.fill();
        });

        // ── Center text ──
        const titleSize = Math.max(18, minDim * 0.065);
        ctx.font = `800 ${titleSize}px 'Orbitron', sans-serif`;
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';

        ctx.shadowColor = `rgba(${accent.r},${accent.g},${accent.b},0.6)`;
        ctx.shadowBlur = 20;
        ctx.fillStyle = `rgba(${accent.r},${accent.g},${accent.b},0.9)`;
        ctx.fillText('F R I D A Y', cx, cy - 4);
        ctx.shadowBlur = 0;

        const subSize = Math.max(7, minDim * 0.022);
        ctx.font = `400 ${subSize}px 'Rajdhani', sans-serif`;
        ctx.fillStyle = `rgba(${accent.r},${accent.g},${accent.b},0.45)`;
        ctx.letterSpacing = '3px';
        ctx.fillText('— ALWAYS AT YOUR SERVICE —', cx, cy + titleSize * 0.7);

        // ── Decorative arcs ──
        const arcR = minDim * 0.40;
        const arcAngle = t * 0.0002;

        ctx.beginPath();
        ctx.arc(cx, cy, arcR, arcAngle, arcAngle + Math.PI * 0.3);
        ctx.strokeStyle = `rgba(${accent.r},${accent.g},${accent.b},0.08)`;
        ctx.lineWidth = 2;
        ctx.stroke();

        ctx.beginPath();
        ctx.arc(cx, cy, arcR, arcAngle + Math.PI, arcAngle + Math.PI * 1.2);
        ctx.strokeStyle = `rgba(${accent.r},${accent.g},${accent.b},0.06)`;
        ctx.lineWidth = 1.5;
        ctx.stroke();

        const arcR2 = minDim * 0.43;
        ctx.beginPath();
        ctx.arc(cx, cy, arcR2, -arcAngle * 1.5, -arcAngle * 1.5 + Math.PI * 0.15);
        ctx.strokeStyle = `rgba(${accent.r},${accent.g},${accent.b},0.12)`;
        ctx.lineWidth = 3;
        ctx.stroke();

        _drawDataReadout(t, accent);

        animFrame = requestAnimationFrame(_animate);
    }

    function _drawDataReadout(t, accent) {
        const fontSize = 8;
        ctx.font = `500 ${fontSize}px 'Share Tech Mono', monospace`;
        ctx.fillStyle = `rgba(${accent.r},${accent.g},${accent.b},0.25)`;
        ctx.textAlign = 'left';

        const dataLines = [
            `SYS.CORE // ONLINE`,
            `FREQ ${(2.4 + Math.sin(t*0.001)*0.1).toFixed(2)} GHz`,
            `NET.STATUS // ACTIVE`,
        ];
        dataLines.forEach((line, i) => {
            ctx.fillText(line, 14, h - 30 + i * 11);
        });

        ctx.textAlign = 'right';
        const rightData = [
            `BUILD v4.0.1`,
            `MEM.ALLOC // NOMINAL`,
            `LATENCY < 1ms`,
        ];
        rightData.forEach((line, i) => {
            ctx.fillText(line, w - 14, h - 30 + i * 11);
        });
    }

    function destroy() {
        if (animFrame) cancelAnimationFrame(animFrame);
        window.removeEventListener('resize', _resize);
    }

    return { init, setState, setPreset, getPresets, getPreset, destroy };
})();

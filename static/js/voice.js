/* ══════════════════════════════════════════════════════════════════════════════
   FRIDAY AI — Voice Waveform Visualization
   ══════════════════════════════════════════════════════════════════════════════ */

const VoiceViz = (() => {
    let canvas, ctx;
    let bars = [];
    const BAR_COUNT = 32;
    let currentRMS = 0;
    let targetRMS = 0;
    let animFrame;
    let isListening = false;

    function init() {
        canvas = document.getElementById('voiceWaveformCanvas');
        if (!canvas) return;
        ctx = canvas.getContext('2d');
        _resize();
        window.addEventListener('resize', _resize);

        // Initialize bars
        bars = Array.from({ length: BAR_COUNT }, () => ({
            height: 2,
            targetHeight: 2,
            velocity: 0,
        }));

        _animate();
    }

    function _resize() {
        const rect = canvas.parentElement.getBoundingClientRect();
        const dpr = window.devicePixelRatio || 1;
        canvas.width = rect.width * dpr;
        canvas.height = 50 * dpr;
        canvas.style.width = rect.width + 'px';
        canvas.style.height = '50px';
        ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    }

    function setRMS(rms) {
        targetRMS = Math.min(rms / 3000, 1);
    }

    function setListening(val) {
        isListening = val;
        if (!val) {
            targetRMS = 0;
        }
    }

    function _animate() {
        const w = canvas.width / (window.devicePixelRatio || 1);
        const h = 50;
        ctx.clearRect(0, 0, w, h);

        // Smooth RMS
        currentRMS += (targetRMS - currentRMS) * 0.15;

        const barWidth = Math.max(2, (w - (BAR_COUNT - 1) * 2) / BAR_COUNT);
        const gap = 2;
        const maxH = h - 6;
        const t = Date.now() * 0.003;

        bars.forEach((bar, i) => {
            // Generate target from RMS + wave pattern
            const wave = Math.sin(t + i * 0.3) * 0.5 + 0.5;
            const center = Math.abs(i - BAR_COUNT / 2) / (BAR_COUNT / 2);
            const centerBoost = 1 - center * 0.6;

            if (isListening && currentRMS > 0.02) {
                bar.targetHeight = (currentRMS * maxH * centerBoost * wave * 0.8) + 3;
            } else if (isListening) {
                // Idle listening: subtle breathing
                bar.targetHeight = 3 + Math.sin(t * 0.5 + i * 0.2) * 2;
            } else {
                bar.targetHeight = 2;
            }

            // Spring physics
            const force = (bar.targetHeight - bar.height) * 0.2;
            bar.velocity += force;
            bar.velocity *= 0.7; // damping
            bar.height += bar.velocity;
            bar.height = Math.max(2, Math.min(maxH, bar.height));

            // Draw bar
            const x = i * (barWidth + gap);
            const y = (h - bar.height) / 2;
            const alpha = 0.3 + (bar.height / maxH) * 0.7;

            // Gradient per bar
            const grad = ctx.createLinearGradient(x, y, x, y + bar.height);
            grad.addColorStop(0, `rgba(0, 212, 255, ${alpha})`);
            grad.addColorStop(1, `rgba(0, 255, 136, ${alpha * 0.6})`);

            ctx.fillStyle = grad;
            ctx.beginPath();
            ctx.roundRect(x, y, barWidth, bar.height, 1);
            ctx.fill();

            // Glow on tall bars
            if (bar.height > maxH * 0.5) {
                ctx.shadowColor = 'rgba(0, 212, 255, 0.4)';
                ctx.shadowBlur = 8;
                ctx.fillRect(x, y, barWidth, bar.height);
                ctx.shadowBlur = 0;
            }
        });

        animFrame = requestAnimationFrame(_animate);
    }

    function destroy() {
        if (animFrame) cancelAnimationFrame(animFrame);
    }

    return { init, setRMS, setListening, destroy };
})();

/* Elastic mesh + a temporary window through the gel. No dependencies or tracking. */
(() => {
  'use strict';
  const stage = document.querySelector('#stage');
  const canvas = document.querySelector('#jelly');
  const ctx = canvas.getContext('2d');
  const reveal = document.querySelector('#reveal');
  const reset = document.querySelector('#reset');
  const status = document.querySelector('#status');
  const label = document.querySelector('#surface-label');
  const motion = matchMedia('(prefers-reduced-motion: reduce)');
  if (!ctx) { stage.classList.add('uncovered'); label.hidden = true; return; }
  const cols = 35, rows = 20;
  let w = 0, h = 0, nodes = [], holes = [], all = motion.matches;
  let pointer = null, activeId = null, down = false, clearOnDown = false;
  let last = 0, frame = 0, idleUntil = 0, keyboard = false;
  document.addEventListener("keydown", event => { if (event.key === "Tab") keyboard = true; });
  document.addEventListener("pointerdown", () => { keyboard = false; }, true);
  const clamp = (v, lo, hi) => Math.min(hi, Math.max(lo, v));

  function setUncovered(value) {
    all = value;
    stage.classList.toggle('uncovered', all);
    reveal.setAttribute('aria-pressed', String(all));
    reveal.innerHTML = all ? 'Cover with jelly <span>↙</span>' : 'Uncover everything <span>↗</span>';
    status.textContent = all ? 'All work uncovered' : 'Soft surface / ready';
    label.classList.toggle('hidden', all || holes.length > 0);
    wake();
  }
  function resize() {
    const rect = stage.getBoundingClientRect();
    w = rect.width; h = rect.height;
    const ratio = Math.min(devicePixelRatio || 1, 2);
    canvas.width = Math.round(w * ratio); canvas.height = Math.round(h * ratio);
    ctx.setTransform(ratio, 0, 0, ratio, 0, 0);
    nodes = Array.from({ length: cols * rows }, (_, i) => ({
      x: i % cols * w / (cols - 1), y: Math.floor(i / cols) * h / (rows - 1),
      dx: 0, dy: 0, vx: 0, vy: 0
    }));
    holes = []; pointer = null; down = false; activeId = null;
    label.classList.toggle('hidden', all);
    wake();
  }
  function wake() { idleUntil = performance.now() + 6000; if (!frame && !document.hidden) frame = requestAnimationFrame(tick); }
  function isClear(x, y) {
    const now = performance.now();
    return all || holes.some(p => now - p.t < 2000 && Math.hypot(p.x - x, p.y - y) < p.r * .7);
  }
  function position(event) {
    const rect = stage.getBoundingClientRect();
    return { x: event.clientX - rect.left, y: event.clientY - rect.top };
  }
  function brush(event) {
    if (all || motion.matches) return;
    const p = position(event);
    const dx = pointer ? clamp(p.x - pointer.x, -30, 30) : 0;
    const dy = pointer ? clamp(p.y - pointer.y, -30, 30) : 0;
    pointer = p;
    const now = performance.now(), radius = w < 600 ? 87 : 130;
    // Keep the most recent position per short interval to bound work on touch devices.
    if (holes.length && now - holes[holes.length - 1].t < 25) holes.pop();
    holes.push({ ...p, t: now, r: radius });
    holes = holes.slice(-90);
    for (const n of nodes) {
      const dist = Math.hypot(n.x + n.dx - p.x, n.y + n.dy - p.y);
      if (dist < radius * 1.8) {
        const force = (1 - dist / (radius * 1.8)) ** 2;
        n.vx += (dx * 10 + (n.x - p.x) * .75) * force;
        n.vy += (dy * 10 + (n.y - p.y) * .75 + (down ? 90 : 12)) * force;
      }
    }
    label.classList.add('hidden');
    status.textContent = down ? 'Stretching / let go to settle' : 'A little of the work, uncovered';
    wake();
  }
  stage.addEventListener('pointerdown', event => {
    if (!event.isPrimary) return;
    const p = position(event);
    clearOnDown = isClear(p.x, p.y);
    activeId = event.pointerId; down = true;
    if (!all && !motion.matches && !event.target.closest('a')) stage.setPointerCapture(event.pointerId);
    brush(event);
  });
  stage.addEventListener('pointermove', event => { if (event.isPrimary) brush(event); });
  function release(event) {
    if (activeId !== event.pointerId) return;
    down = false; activeId = null;
    if (stage.hasPointerCapture(event.pointerId)) stage.releasePointerCapture(event.pointerId);
    if (!all) status.textContent = 'Settling back into shape';
    wake();
  }
  stage.addEventListener('pointerup', release);
  stage.addEventListener('pointercancel', release);
  stage.addEventListener('pointerleave', () => { pointer = null; if (!down) wake(); });
  // A first poke uncovers a covered link; only an already-visible link navigates.
  stage.addEventListener('click', event => {
    if (event.target.closest('a') && event.detail > 0 && !all && !clearOnDown) event.preventDefault();
  });
  // All work stays usable from the keyboard, without needing to move a pointer.
  stage.addEventListener('focusin', () => { if (keyboard) setUncovered(true); });
  reveal.addEventListener('click', () => setUncovered(!all));
  reset.addEventListener('click', () => { holes = []; nodes.forEach(n => { n.dx = n.dy = n.vx = n.vy = 0; }); pointer = null; down = false; activeId = null; setUncovered(motion.matches); });
  motion.addEventListener('change', () => { setUncovered(motion.matches); resize(); });
  document.addEventListener('visibilitychange', () => {
    if (document.hidden) { cancelAnimationFrame(frame); frame = 0; last = 0; }
    else wake();
  });
  new ResizeObserver(resize).observe(stage);

  function tick(now) {
    frame = 0;
    const dt = Math.min((now - (last || now)) / 1000, .032); last = now;
    if (!all && !motion.matches) {
      const fade = Math.exp(-6.2 * dt);
      // Symmetric neighbor forces produce a travelling, damped spring response.
      const force = nodes.map((n, i) => {
        let fx = -n.dx * 45, fy = -n.dy * 45;
        for (const j of [i % cols > 0 ? i - 1 : -1, i % cols < cols - 1 ? i + 1 : -1, i - cols, i + cols]) {
          if (j >= 0 && j < nodes.length) { fx += (nodes[j].dx - n.dx) * 32; fy += (nodes[j].dy - n.dy) * 32; }
        }
        return [fx, fy];
      });
      nodes.forEach((n, i) => {
        const edge = n.x === 0 || n.x === w || n.y === 0 || n.y === h;
        n.vx = (n.vx + force[i][0] * dt) * fade; n.vy = (n.vy + force[i][1] * dt) * fade;
        n.dx = edge ? 0 : clamp(n.dx + n.vx * dt, -95, 95);
        n.dy = edge ? 0 : clamp(n.dy + n.vy * dt, -95, 95);
      });
      ctx.globalCompositeOperation = 'source-over';
      ctx.clearRect(0, 0, w, h);
      const gel = ctx.createLinearGradient(0, 0, w * .6, h);
      gel.addColorStop(0, '#78552d'); gel.addColorStop(.43, '#ae803f'); gel.addColorStop(1, '#45351f');
      ctx.fillStyle = gel; ctx.fillRect(0, 0, w, h);
      for (let y = 0; y < rows; y++) {
        ctx.beginPath();
        for (let x = 0; x < cols; x++) {
          const n = nodes[y * cols + x];
          x ? ctx.lineTo(n.x + n.dx, n.y + n.dy) : ctx.moveTo(n.x + n.dx, n.y + n.dy);
        }
        ctx.strokeStyle = y % 3 === 0 ? 'rgba(255,222,164,.55)' : 'rgba(255,222,164,.24)';
        ctx.lineWidth = .85; ctx.stroke();
      }
      for (let x = 0; x < cols; x++) {
        ctx.beginPath();
        for (let y = 0; y < rows; y++) {
          const n = nodes[y * cols + x];
          y ? ctx.lineTo(n.x + n.dx, n.y + n.dy) : ctx.moveTo(n.x + n.dx, n.y + n.dy);
        }
        ctx.strokeStyle = 'rgba(255,222,164,.18)'; ctx.stroke();
      }
      ctx.globalCompositeOperation = 'destination-out';
      holes = holes.filter(p => now - p.t < 3200);
      for (const p of holes) {
        const opacity = clamp((3200 - (now - p.t)) / 900, 0, 1);
        const clear = ctx.createRadialGradient(p.x, p.y, p.r * .64, p.x, p.y, p.r);
        clear.addColorStop(0, `rgba(0,0,0,${opacity})`); clear.addColorStop(1, 'rgba(0,0,0,0)');
        ctx.fillStyle = clear; ctx.fillRect(p.x - p.r, p.y - p.r, p.r * 2, p.r * 2);
      }
      ctx.globalCompositeOperation = 'source-over';
      if (!holes.length && !down) { label.classList.remove('hidden'); status.textContent = 'Soft surface / ready'; }
    }
    if (now < idleUntil && !document.hidden && !all && !motion.matches) frame = requestAnimationFrame(tick);
  }
  // The same generator supplies the README and demo's public project text.
  fetch('content.json').then(response => {
    if (!response.ok) throw new Error('Content unavailable');
    return response.json();
  }).then(content => {
    for (const [i, project] of content.projects.entries()) {
      const card = document.querySelectorAll('.project')[i];
      if (!card) continue;
      card.querySelector('.project-meta').textContent = `${String(i + 1).padStart(2, '0')} / ${project.language}`;
      card.querySelector('p').textContent = project.description;
    }
  }).catch(() => { /* The authored project links still work offline. */ });
  resize();
  setUncovered(all);
})();

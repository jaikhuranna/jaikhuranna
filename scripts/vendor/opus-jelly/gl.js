// Small WebGL2 helpers shared by the three materials.

export function createContext(canvas) {
  const gl = canvas.getContext('webgl2', {
    alpha: true,
    premultipliedAlpha: true,
    antialias: false,
    depth: false,
    stencil: false,
    preserveDrawingBuffer: false,
  })
  if (!gl) return null
  gl.enable(gl.BLEND)
  gl.blendFunc(gl.ONE, gl.ONE_MINUS_SRC_ALPHA)
  return gl
}

export function program(gl, vs, fs) {
  const make = (type, src) => {
    const s = gl.createShader(type)
    gl.shaderSource(s, src)
    gl.compileShader(s)
    if (!gl.getShaderParameter(s, gl.COMPILE_STATUS)) throw new Error(gl.getShaderInfoLog(s))
    return s
  }
  const p = gl.createProgram()
  const v = make(gl.VERTEX_SHADER, vs), f = make(gl.FRAGMENT_SHADER, fs)
  gl.attachShader(p, v)
  gl.attachShader(p, f)
  gl.linkProgram(p)
  if (!gl.getProgramParameter(p, gl.LINK_STATUS)) throw new Error(gl.getProgramInfoLog(p))
  gl.deleteShader(v)
  gl.deleteShader(f)
  const u = {}
  const n = gl.getProgramParameter(p, gl.ACTIVE_UNIFORMS)
  for (let i = 0; i < n; i++) {
    const name = gl.getActiveUniform(p, i).name.replace(/\[0\]$/, '')
    u[name] = gl.getUniformLocation(p, name)
  }
  return { p, u, attr: (name) => gl.getAttribLocation(p, name) }
}

// Round points with a soft cast shadow. Used by the dots and by loose sand grains.
const POINT_VS = `#version 300 es
in vec3 a_pos;      // x, y in CSS px, glow
in vec2 a_meta;     // seed, mark
uniform vec2 u_res;
uniform float u_size;
uniform float u_shadow;
uniform vec2 u_off;
out float v_seed; out float v_glow; out float v_mark;
void main() {
  vec2 p = a_pos.xy + u_off * u_shadow;
  vec2 c = p / u_res * 2.0 - 1.0;
  gl_Position = vec4(c.x, -c.y, 0.0, 1.0);
  gl_PointSize = u_size * (0.93 + 0.12 * a_meta.x) * (1.0 + 0.32 * u_shadow);
  v_seed = a_meta.x; v_glow = a_pos.z; v_mark = a_meta.y;
}`

const POINT_FS = `#version 300 es
precision highp float;
in float v_seed; in float v_glow; in float v_mark;
uniform float u_shadow;
uniform vec3 u_lo; uniform vec3 u_hi;
uniform float u_alpha;
out vec4 o;
void main() {
  vec2 q = gl_PointCoord * 2.0 - 1.0;
  float d = length(q);
  if (u_shadow > 0.5) {
    float a = (1.0 - smoothstep(0.45, 1.0, d)) * 0.92 * u_alpha;
    o = vec4(vec3(0.035, 0.033, 0.028) * a, a);
    return;
  }
  float a = (1.0 - smoothstep(0.8, 1.0, d)) * u_alpha;
  vec3 n = vec3(q.x, q.y, sqrt(max(0.0, 1.0 - d * d)));
  float l = clamp(dot(n, normalize(vec3(-0.45, -0.6, 0.66))), 0.0, 1.0);
  vec3 base = mix(u_lo, u_hi, v_seed * 0.75 + v_mark * 0.55);
  base += max(v_glow, 0.0) * vec3(0.30, 0.24, 0.10) - max(-v_glow, 0.0) * 0.14;
  vec3 c = base * (0.42 + 0.68 * l) + pow(l, 18.0) * 0.28;
  o = vec4(c * a, a);
}`

export function pointRenderer(gl) {
  const prog = program(gl, POINT_VS, POINT_FS)
  return {
    prog,
    vao(dyn, meta) {
      const vao = gl.createVertexArray()
      gl.bindVertexArray(vao)
      gl.bindBuffer(gl.ARRAY_BUFFER, dyn)
      const ap = prog.attr('a_pos')
      gl.enableVertexAttribArray(ap)
      gl.vertexAttribPointer(ap, 3, gl.FLOAT, false, 12, 0)
      gl.bindBuffer(gl.ARRAY_BUFFER, meta)
      const am = prog.attr('a_meta')
      gl.enableVertexAttribArray(am)
      gl.vertexAttribPointer(am, 2, gl.FLOAT, false, 8, 0)
      gl.bindVertexArray(null)
      return vao
    },
    draw(vao, count, { w, h, size, lo, hi, shadow = true, off = [2.2, 3], alpha = 1 }) {
      gl.useProgram(prog.p)
      gl.uniform2f(prog.u.u_res, w, h)
      gl.uniform2f(prog.u.u_off, off[0], off[1])
      gl.uniform3fv(prog.u.u_lo, lo)
      gl.uniform3fv(prog.u.u_hi, hi)
      gl.uniform1f(prog.u.u_alpha, alpha)
      gl.uniform1f(prog.u.u_size, size)
      gl.bindVertexArray(vao)
      if (shadow) {
        gl.uniform1f(prog.u.u_shadow, 1)
        gl.drawArrays(gl.POINTS, 0, count)
      }
      gl.uniform1f(prog.u.u_shadow, 0)
      gl.drawArrays(gl.POINTS, 0, count)
      gl.bindVertexArray(null)
    },
  }
}

// Deterministic pseudo-random numbers, so a reset always lays the same surface.
export function rng(seed = 7) {
  let s = seed >>> 0
  return () => {
    s = (s + 0x6d2b79f5) >>> 0
    let t = s
    t = Math.imul(t ^ (t >>> 15), t | 1)
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61)
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296
  }
}

// Value noise for laying dunes.
export function noise2(seed = 3) {
  const r = rng(seed)
  const perm = new Float32Array(512)
  for (let i = 0; i < 512; i++) perm[i] = r()
  const at = (x, y) => perm[((x & 255) + ((y & 255) * 57)) & 511]
  return (x, y) => {
    const xi = Math.floor(x), yi = Math.floor(y)
    const xf = x - xi, yf = y - yi
    const u = xf * xf * (3 - 2 * xf), v = yf * yf * (3 - 2 * yf)
    const a = at(xi, yi), b = at(xi + 1, yi), c = at(xi, yi + 1), d = at(xi + 1, yi + 1)
    return a + (b - a) * u + (c - a) * v + (a - b - c + d) * u * v
  }
}

// Where to put material that is pushed off an opened plate: just outside its
// nearest edge, never inside another opened plate.
export function outside(rect, x, y, spread, others) {
  const blocked = (px, py) => others.some((o) => o !== rect && px > o.x && px < o.x + o.w && py > o.y && py < o.y + o.h)
  const cands = [
    [x - rect.x, -1, 0],
    [rect.x + rect.w - x, 1, 0],
    [y - rect.y, 0, -1],
    [rect.y + rect.h - y, 0, 1],
  ].sort((a, b) => a[0] - b[0])
  for (const [, dx, dy] of cands) {
    const bx = dx ? (dx < 0 ? rect.x - 1 : rect.x + rect.w + 1) : x
    const by = dy ? (dy < 0 ? rect.y - 1 : rect.y + rect.h + 1) : y
    if (blocked(bx, by)) continue
    const sx = bx + dx * spread, sy = by + dy * spread
    if (!blocked(sx, sy)) return [sx, sy]
    return [bx, by]
  }
  const [, dx, dy] = cands[0]
  return [dx ? (dx < 0 ? rect.x - 1 : rect.x + rect.w + 1) : x, dy ? (dy < 0 ? rect.y - 1 : rect.y + rect.h + 1) : y]
}

export function inRect(r, x, y) {
  return x > r.x && x < r.x + r.w && y > r.y && y < r.y + r.h
}

export function pad(r, p) {
  return { x: r.x - p, y: r.y - p, w: r.w + p * 2, h: r.h + p * 2 }
}

// Closest point on segment a→b to p.
export function closest(ax, ay, bx, by, px, py) {
  const dx = bx - ax, dy = by - ay
  const l2 = dx * dx + dy * dy
  let t = l2 > 1e-6 ? ((px - ax) * dx + (py - ay) * dy) / l2 : 0
  t = t < 0 ? 0 : t > 1 ? 1 : t
  return [ax + dx * t, ay + dy * t]
}

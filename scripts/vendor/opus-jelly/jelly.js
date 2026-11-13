// Jelly: a continuous elastic sheet. Thickness is mass over current area, so
// wherever the sheet is stretched it thins into a clear film you can read
// through, and wherever it bunches it deepens to opaque amber. Hovering presses
// a springy dimple; pressing grabs and pulls. Pulled far enough the jelly
// yields and keeps its new shape; let go and it wobbles back the last bit.
import { program, pad, outside } from './gl.js'

const VS = `#version 300 es
in vec2 a_pos; in vec2 a_uv; in float a_t; in vec2 a_n;
uniform vec2 u_res;
out vec2 v_uv; out float v_t; out vec2 v_n;
void main() {
  vec2 c = a_pos / u_res * 2.0 - 1.0;
  gl_Position = vec4(c.x, -c.y, 0.0, 1.0);
  v_uv = a_uv; v_t = a_t; v_n = a_n;
}`

const FS = `#version 300 es
precision highp float;
in vec2 v_uv; in float v_t; in vec2 v_n;
uniform sampler2D u_mark;
uniform vec2 u_res;
out vec4 o;
float hash(vec2 p) { p = fract(p * vec2(123.34, 456.21)); p += dot(p, p + 45.32); return fract(p.x * p.y); }
void main() {
  float t = v_t;
  float a = smoothstep(0.3, 0.93, t);
  float mk = texture(u_mark, v_uv / u_res).r;
  vec2 sway = vec2(sin(v_uv.x * 0.019 + v_uv.y * 0.012) + 0.5 * sin(v_uv.y * 0.043 + 1.3),
                   cos(v_uv.y * 0.022 - v_uv.x * 0.009) + 0.5 * cos(v_uv.x * 0.037 - 0.7)) * 0.11;
  vec2 g = v_n * 1.5;
  g *= min(1.0, 0.75 / max(length(g), 1e-4));
  // Bunched jelly reads as one smooth glossy mass, not crumpled foil.
  g /= 1.0 + max(0.0, t - 1.3) * 1.1;
  vec3 n = normalize(vec3(g + sway, 1.0));
  vec3 L = normalize(vec3(-0.42, -0.64, 0.64));
  float diff = clamp(dot(n, L), 0.0, 1.0);
  float spec = pow(clamp(dot(reflect(-L, n), vec3(0.0, 0.0, 1.0)), 0.0, 1.0), 48.0);
  // Suspended bubbles, laid out in the sheet's own coordinates so they stretch with it.
  vec2 cell = floor(v_uv / 30.0);
  vec2 f = v_uv - cell * 30.0;
  float r = hash(cell);
  vec2 c = vec2(hash(cell + 3.1), hash(cell + 7.7)) * 20.0 + 5.0;
  float br = 1.3 + r * 3.2;
  float d = length(f - c);
  float bub = r > 0.78 ? smoothstep(br, br - 1.0, d) * (0.5 + 0.5 * smoothstep(br * 0.2, br * 0.9, length(f - c + vec2(br * 0.35)))) : 0.0;
  // Depth: slow cloudy variation inside the jelly.
  float cloud = sin(v_uv.x * 0.009 + sin(v_uv.y * 0.011) * 2.0) * sin(v_uv.y * 0.008 - v_uv.x * 0.004);
  vec3 pale = vec3(0.97, 0.78, 0.42), mid = vec3(0.74, 0.46, 0.12), deep = vec3(0.3, 0.14, 0.03);
  vec3 col = mix(pale, mid, smoothstep(0.45, 1.0, t));
  col = mix(col, deep, smoothstep(1.1, 2.6, t) * 0.9);
  col *= 0.86 + 0.2 * cloud;
  col = mix(col, deep * 0.7, mk * 0.38);
  col *= 0.58 + 0.6 * diff;
  col += vec3(1.0, 0.86, 0.6) * bub * 0.22;
  float rim = clamp(length(v_n) * 1.2, 0.0, 1.0);
  // A film stretched past ~3x its area is effectively gone: no tint, no gloss.
  float present = smoothstep(0.24, 0.42, t);
  float sheen = (spec * (0.2 + 0.7 * a) + rim * 0.05 * (1.0 - a)) * present;
  vec3 rgb = col * a + vec3(1.0, 0.93, 0.8) * sheen;
  float film = (1.0 - a) * 0.035 * present;
  o = vec4(rgb + vec3(0.75, 0.48, 0.12) * film, clamp(a + sheen * 0.7 + film, 0.0, 1.0));
}`

export class Jelly {
  constructor(gl, { w, h, dpr, reduced, compact, markTex }) {
    Object.assign(this, { gl, w, h, dpr, reduced })
    const sp0 = compact ? 20 : 24
    const cols = Math.max(4, Math.round(w / sp0)) + 1
    const rows = Math.max(4, Math.round(h / sp0)) + 1
    const sx = w / (cols - 1), sy = h / (rows - 1)
    Object.assign(this, { cols, rows, sx, sy, A0: sx * sy })
    const n = cols * rows
    this.n = n
    for (const k of ['ox', 'oy', 'hx', 'hy', 'x', 'y', 'vx', 'vy', 't']) this[k] = new Float32Array(n)
    this.pin = new Uint8Array(n)
    for (let j = 0; j < rows; j++) {
      for (let i = 0; i < cols; i++) {
        const k = j * cols + i
        this.ox[k] = this.hx[k] = this.x[k] = i * sx
        this.oy[k] = this.hy[k] = this.y[k] = j * sy
        if (i === 0 || j === 0 || i === cols - 1 || j === rows - 1) this.pin[k] = 1
      }
    }
    this.dens = new Float32Array((cols - 1) * (rows - 1))
    this.grab = null
    this.opened = []
    this.moving = 1
    this.compact = compact

    this.prog = program(gl, VS, FS)
    // Each cell gets its own four corners, so a stretched cell can be clear
    // right up to a bunched neighbour instead of sharing its thickness.
    const cells = (cols - 1) * (rows - 1)
    this.nn = new Float32Array(n * 2)
    this.buf = new Float32Array(cells * 4 * 7)
    this.vbo = gl.createBuffer()
    gl.bindBuffer(gl.ARRAY_BUFFER, this.vbo)
    gl.bufferData(gl.ARRAY_BUFFER, this.buf.byteLength, gl.DYNAMIC_DRAW)
    const idx = new Uint32Array(cells * 6)
    let q = 0
    for (let c = 0; c < cells; c++) {
      const v = c * 4
      idx[q++] = v; idx[q++] = v + 1; idx[q++] = v + 2
      idx[q++] = v; idx[q++] = v + 2; idx[q++] = v + 3
    }
    this.count = q
    this.vao = gl.createVertexArray()
    gl.bindVertexArray(this.vao)
    this.ibo = gl.createBuffer()
    gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, this.ibo)
    gl.bufferData(gl.ELEMENT_ARRAY_BUFFER, idx, gl.STATIC_DRAW)
    gl.bindBuffer(gl.ARRAY_BUFFER, this.vbo)
    const at = (name, size, off) => {
      const l = this.prog.attr(name)
      gl.enableVertexAttribArray(l)
      gl.vertexAttribPointer(l, size, gl.FLOAT, false, 28, off * 4)
    }
    at('a_pos', 2, 0); at('a_uv', 2, 2); at('a_t', 1, 4); at('a_n', 2, 5)
    gl.bindVertexArray(null)
    this.markTex = markTex
  }

  get openAt() { return 0.8 }

  brush(down) {
    return down ? (this.compact ? 66 : 88) : this.compact ? 40 : 50
  }

  press(px, py) {
    const R = this.brush(true)
    const list = []
    for (let k = 0; k < this.n; k++) {
      if (this.pin[k]) continue
      const dx = this.x[k] - px, dy = this.y[k] - py
      const d = Math.hypot(dx, dy)
      if (d < R) list.push([k, Math.pow(1 - d / R, 1.4), dx, dy])
    }
    this.grab = list
    // A poke: a little dimple and a wobble.
    if (!this.reduced) {
      for (const [k, w, dx, dy] of list) {
        const d = Math.hypot(dx, dy) || 1
        this.vx[k] += (dx / d) * w * 260; this.vy[k] += (dy / d) * w * 260
      }
    }
    this.moving = 1
  }

  release() {
    this.grab = null
    this.moving = 1
  }

  open(rect, instant = false) {
    const r = pad(rect, 6)
    this.opened.push(r)
    let leftLim = 2, rightLim = this.w - 2
    for (const o of this.opened) {
      if (o === r || o.y >= r.y + r.h || o.y + o.h <= r.y) continue
      if (o.x + o.w <= r.x + 1) leftLim = Math.max(leftLim, o.x + o.w + 2)
      if (o.x >= r.x + r.w - 1) rightLim = Math.min(rightLim, o.x - 2)
    }
    const mL = Math.min(90, r.x - leftLim), mR = Math.min(90, rightLim - (r.x + r.w))
    let split = r.x + r.w / 2
    if (mL < 10 && mR >= 10) split = r.x
    else if (mR < 10 && mL >= 10) split = r.x + r.w
    r.split = split
    const a0 = r.x - Math.max(mL, 1), b0 = r.x + r.w + Math.max(mR, 1)
    const { n, hx, hy, pin } = this
    for (let k = 0; k < n; k++) {
      if (pin[k]) continue
      const Y = hy[k]
      const out = Y < r.y ? r.y - Y : Y > r.y + r.h ? Y - (r.y + r.h) : 0
      const wy = out <= 0 ? 1 : out >= 60 ? 0 : 1 - (out / 60) * (out / 60) * (3 - 2 * (out / 60))
      if (wy <= 0) continue
      const X = hx[k]
      let m
      if (X > a0 && X < split) m = a0 + (X - a0) * Math.max(0, mL - 3) / Math.max(1, split - a0)
      else if (X >= split && X < b0) m = b0 - (b0 - X) * Math.max(0, mR - 3) / Math.max(1, b0 - split)
      else continue
      hx[k] = X + (m - X) * wy
    }
    this.repair = 120
    if (instant || this.reduced) {
      for (let i = 0; i < 120; i++) this.keepOpen()
      this.x.set(hx); this.y.set(hy); this.vx.fill(0); this.vy.fill(0)
    }
    this.moving = 1
  }

  keepOpen() {
    const { n, hx, hy, cols, rows, x, y, pin, opened } = this
    // Stragglers: a rest position on an opened plate moves to the nearest free gutter.
    for (const r of opened) {
      for (let k = 0; k < n; k++) {
        const X = hx[k], Y = hy[k]
        if (pin[k] || X <= r.x || X >= r.x + r.w || Y <= r.y || Y >= r.y + r.h) continue
        const [tx, ty] = outside(r, X, Y, (k * 0.618) % 1 * 8, opened)
        hx[k] += (tx - X) * 0.35; hy[k] += (ty - Y) * 0.35
        if (Math.abs(tx - X) + Math.abs(ty - Y) < 1.5) { hx[k] = tx; hy[k] = ty }
        this.moving = 1
      }
    }
    // For a couple of seconds after an opening, any cell still thick enough to
    // see whose centre is on the plate is pulled apart until it thins out.
    if (this.repair <= 0) return
    this.repair--
    const dens = this.densities()
    const cw = cols - 1
    for (let j = 0; j < rows - 1; j++) {
      for (let i = 0; i < cw; i++) {
        if (dens[j * cw + i] < 0.42) continue
        const a = j * cols + i, c = a + cols + 1
        const cx = (x[a] + x[c]) / 2, cy = (y[a] + y[c]) / 2
        const r = opened.find((o) => cx > o.x && cx < o.x + o.w && cy > o.y && cy < o.y + o.h)
        if (!r) continue
        for (const k of [a, a + 1, c, a + cols]) {
          if (pin[k]) continue
          const X = hx[k], Y = hy[k]
          const d = [X - r.x, r.x + r.w - X, Y - r.y, r.y + r.h - Y]
          const side = d.indexOf(Math.min(...d))
          if (side === 0) hx[k] = Math.max(1, X - 3)
          else if (side === 1) hx[k] = Math.min(this.w - 1, X + 3)
          else if (side === 2) hy[k] = Math.max(1, Y - 3)
          else hy[k] = Math.min(this.h - 1, Y + 3)
          this.moving = 1
        }
      }
    }
  }

  reset() {
    this.hx.set(this.ox); this.hy.set(this.oy)
    this.opened = []
    this.repair = 0
    this.grab = null
    if (this.reduced) { this.x.set(this.ox); this.y.set(this.oy) }
    this.moving = 1
  }

  step(dt, inp) {
    if (inp.pressed) this.press(inp.bx, inp.by)
    if (!inp.down && this.grab) this.release()
    const { n, cols, x, y, vx, vy, hx, hy, pin } = this
    if (this.opened.length) this.keepOpen()

    if (this.reduced) {
      // No springs: the sheet goes exactly where it's put.
      if (this.grab && inp.down && inp.moved) {
        const mx = inp.bx - inp.ax, my = inp.by - inp.ay
        for (const [k, w] of this.grab) { hx[k] += mx * w; hy[k] += my * w }
        this.smoothHomes()
        this.clampHomes()
      }
      x.set(hx); y.set(hy)
      this.moving = 0
      return
    }

    const subs = 2, h = dt / subs
    const kH = 55, kC = 420, c = 3.2, cV = 7, Y = 12, creep = 8
    const Rh = this.brush(false), Rh2 = Rh * Rh
    const hover = inp.hover && inp.moved
    const mx = inp.bx - inp.ax, my = inp.by - inp.ay
    let maxV = 0
    for (let s = 0; s < subs; s++) {
      if (this.grab && inp.down) {
        for (const [k, w, ox, oy] of this.grab) {
          const tx = inp.bx + ox, ty = inp.by + oy
          vx[k] += ((tx - x[k]) * 900 * w - vx[k] * 40 * w) * h
          vy[k] += ((ty - y[k]) * 900 * w - vy[k] * 40 * w) * h
        }
      }
      if (hover && s === 0) {
        for (let k = 0; k < n; k++) {
          if (pin[k]) continue
          const dx = x[k] - inp.bx, dy = y[k] - inp.by
          const d2 = dx * dx + dy * dy
          if (d2 >= Rh2) continue
          const d = Math.sqrt(d2) || 1
          const f = 1 - d / Rh
          // Press the surface aside under the cursor; it springs back once you move on.
          const push = (Rh - d) * 0.28 * f
          x[k] += (dx / d) * push; y[k] += (dy / d) * push
          vx[k] += (dx / d) * push * 12 + mx * f * 5
          vy[k] += (dy / d) * push * 12 + my * f * 5
        }
      }
      for (let k = 0; k < n; k++) {
        if (pin[k]) continue
        const ex = x[k] - hx[k], ey = y[k] - hy[k]
        const l = k - 1, r = k + 1, u = k - cols, d = k + cols
        const lx = x[l] - hx[l] + x[r] - hx[r] + x[u] - hx[u] + x[d] - hx[d] - 4 * ex
        const ly = y[l] - hy[l] + y[r] - hy[r] + y[u] - hy[u] + y[d] - hy[d] - 4 * ey
        const lvx = vx[l] + vx[r] + vx[u] + vx[d] - 4 * vx[k]
        const lvy = vy[l] + vy[r] + vy[u] + vy[d] - 4 * vy[k]
        vx[k] += (-kH * ex + kC * lx - c * vx[k] + cV * lvx) * h
        vy[k] += (-kH * ey + kC * ly - c * vy[k] + cV * lvy) * h
      }
      for (let k = 0; k < n; k++) {
        if (pin[k]) continue
        x[k] += vx[k] * h; y[k] += vy[k] * h
        const v2 = vx[k] * vx[k] + vy[k] * vy[k]
        if (v2 > maxV) maxV = v2
      }
      // Pulled hard, the jelly yields and keeps the new shape.
      if (this.grab && inp.down) {
        const a = Math.min(1, creep * h)
        for (let k = 0; k < n; k++) {
          if (pin[k]) continue
          const ex = x[k] - hx[k], ey = y[k] - hy[k]
          const d = Math.hypot(ex, ey)
          if (d > Y) { const f = ((d - Y) / d) * a; hx[k] += ex * f; hy[k] += ey * f }
        }
        this.clampHomes()
      }
    }
    if (maxV < 1 && !this.grab) {
      let far = 0
      for (let k = 0; k < n; k++) far = Math.max(far, Math.abs(x[k] - hx[k]) + Math.abs(y[k] - hy[k]))
      if (far < 0.3) { x.set(hx); y.set(hy); vx.fill(0); vy.fill(0); this.moving = 0 }
    } else this.moving = 1
  }

  smoothHomes() {
    // Spread a reduced-motion pull to the neighbours so the sheet stays continuous.
    const { n, cols, hx, hy, ox, oy, pin } = this
    for (let it = 0; it < 2; it++) {
      for (let k = 0; k < n; k++) {
        if (pin[k]) continue
        const ex = (hx[k - 1] - ox[k - 1] + hx[k + 1] - ox[k + 1] + hx[k - cols] - ox[k - cols] + hx[k + cols] - ox[k + cols]) / 4
        const ey = (hy[k - 1] - oy[k - 1] + hy[k + 1] - oy[k + 1] + hy[k - cols] - oy[k - cols] + hy[k + cols] - oy[k + cols]) / 4
        const cx = hx[k] - ox[k], cy = hy[k] - oy[k]
        hx[k] = ox[k] + cx + (ex - cx) * 0.25
        hy[k] = oy[k] + cy + (ey - cy) * 0.25
      }
    }
  }

  clampHomes() {
    const { n, hx, hy, w, h, pin } = this
    for (let k = 0; k < n; k++) {
      if (pin[k]) continue
      hx[k] = hx[k] < 1 ? 1 : hx[k] > w - 1 ? w - 1 : hx[k]
      hy[k] = hy[k] < 1 ? 1 : hy[k] > h - 1 ? h - 1 : hy[k]
    }
  }

  busy() {
    return this.moving > 0 || !!this.grab
  }

  densities() {
    const { cols, rows, x, y, dens, A0 } = this
    const L2 = Math.max(this.sx, this.sy) ** 2
    for (let j = 0; j < rows - 1; j++) {
      for (let i = 0; i < cols - 1; i++) {
        const a = j * cols + i, b = a + 1, c = a + cols + 1, d = a + cols
        const area = 0.5 * ((x[c] - x[a]) * (y[d] - y[b]) - (y[c] - y[a]) * (x[d] - x[b]))
        // A folded cell is still just a film; only a crushed one is thick.
        const aa = Math.abs(area)
        let dn = aa < A0 * 0.25 ? 4 : Math.min(4, A0 / aa)
        // A cell drawn out into a long fibre is a film too, however narrow.
        const e1 = (x[b] - x[a]) ** 2 + (y[b] - y[a]) ** 2, e2 = (x[d] - x[a]) ** 2 + (y[d] - y[a]) ** 2
        const e3 = (x[c] - x[b]) ** 2 + (y[c] - y[b]) ** 2, e4 = (x[c] - x[d]) ** 2 + (y[c] - y[d]) ** 2
        const long = Math.max(e1, e2, e3, e4) / L2
        if (long > 4) dn = Math.min(dn, 2.2 / long)
        dens[j * (cols - 1) + i] = dn
      }
    }
    return dens
  }

  coverage(rect) {
    const { cols, rows, x, y, A0 } = this
    const dens = this.densities()
    let cov = 0
    for (let j = 0; j < rows - 1; j++) {
      for (let i = 0; i < cols - 1; i++) {
        const a = j * cols + i, c = a + cols + 1
        const cx = (x[a] + x[c]) / 2, cy = (y[a] + y[c]) / 2
        if (cx < rect.x || cx > rect.x + rect.w || cy < rect.y || cy > rect.y + rect.h) continue
        const dn = dens[j * (cols - 1) + i]
        const t = Math.min(1, Math.max(0, (dn - 0.3) / 0.63))
        const al = t * t * (3 - 2 * t)
        cov += (A0 / dn) * al
      }
    }
    return Math.min(1, cov / (rect.w * rect.h))
  }

  render() {
    const { gl, cols, rows, x, y, ox, oy, buf, n } = this
    const dens = this.densities()
    const cw = cols - 1
    const t = this.t
    for (let j = 0; j < rows; j++) {
      for (let i = 0; i < cols; i++) {
        let s = 0, c = 0
        if (i > 0 && j > 0) { s += dens[(j - 1) * cw + i - 1]; c++ }
        if (i < cw && j > 0) { s += dens[(j - 1) * cw + i]; c++ }
        if (i > 0 && j < rows - 1) { s += dens[j * cw + i - 1]; c++ }
        if (i < cw && j < rows - 1) { s += dens[j * cw + i]; c++ }
        t[j * cols + i] = s / c
      }
    }
    const nn = this.nn
    for (let k = 0; k < n; k++) {
      const i = k % cols, j = (k / cols) | 0
      const tl = t[i > 0 ? k - 1 : k], tr = t[i < cols - 1 ? k + 1 : k]
      const tu = t[j > 0 ? k - cols : k], td = t[j < rows - 1 ? k + cols : k]
      nn[k * 2] = (tl - tr) * 0.5; nn[k * 2 + 1] = (tu - td) * 0.5
    }
    let o = 0
    for (let j = 0; j < rows - 1; j++) {
      for (let i = 0; i < cw; i++) {
        const cd = dens[j * cw + i]
        const a = j * cols + i
        for (const k of [a, a + 1, a + cols + 1, a + cols]) {
          // Stretched cells use a geometric mean so a thin cell stays thin even
          // beside a thick one; everywhere else corners share one smooth value.
          const tk = cd < 0.9 ? Math.sqrt(cd * t[k]) : t[k]
          const thin = Math.min(1, tk)
          buf[o] = x[k]; buf[o + 1] = y[k]; buf[o + 2] = ox[k]; buf[o + 3] = oy[k]
          buf[o + 4] = tk; buf[o + 5] = nn[k * 2] * thin; buf[o + 6] = nn[k * 2 + 1] * thin
          o += 7
        }
      }
    }
    gl.clearColor(0, 0, 0, 0)
    gl.clear(gl.COLOR_BUFFER_BIT)
    gl.bindBuffer(gl.ARRAY_BUFFER, this.vbo)
    gl.bufferSubData(gl.ARRAY_BUFFER, 0, buf)
    gl.useProgram(this.prog.p)
    gl.uniform2f(this.prog.u.u_res, this.w, this.h)
    gl.activeTexture(gl.TEXTURE0)
    gl.bindTexture(gl.TEXTURE_2D, this.markTex)
    gl.uniform1i(this.prog.u.u_mark, 0)
    gl.bindVertexArray(this.vao)
    gl.drawElements(gl.TRIANGLES, this.count, gl.UNSIGNED_INT, 0)
    gl.bindVertexArray(null)
  }

  dispose() {
    const { gl } = this
    gl.deleteBuffer(this.vbo); gl.deleteBuffer(this.ibo); gl.deleteVertexArray(this.vao); gl.deleteProgram(this.prog.p)
  }
}

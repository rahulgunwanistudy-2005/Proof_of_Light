// Light stack: a WebGL2 scene of evidence layers with a camera lens resting on top.
// Raw WebGL keeps the page same-origin under the CSP and avoids a 2 MB library.
// The "light show" mode tints the scene with the capture palette at the same
// photosensitivity-safe pace as the real challenge (2.5 changes per second, crossfaded).

const SHOW_PALETTE = [
  [1, 1, 1], [0.95, 0.24, 0.2], [0.2, 0.85, 0.35], [0.25, 0.45, 1], [1, 0.86, 0.2],
];

const COMMON = `#version 300 es
precision highp float;
uniform mat4 uViewProj;
uniform float uTime;
`;

const LIGHTING = `
uniform vec3 uCamera;
uniform vec3 uFlash;
uniform float uShow;
float hash(vec2 p) { return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453); }
float noise(vec2 p) {
  vec2 i = floor(p), f = fract(p);
  vec2 u = f * f * (3.0 - 2.0 * f);
  return mix(mix(hash(i), hash(i + vec2(1, 0)), u.x), mix(hash(i + vec2(0, 1)), hash(i + vec2(1, 1)), u.x), u.y);
}
vec3 shade(vec3 base, vec3 n, vec3 world, float shininess, float specular) {
  vec3 v = normalize(uCamera - world);
  vec3 key = normalize(vec3(-0.45, 1.0, 0.55));
  vec3 fill = normalize(vec3(0.8, 0.35, -0.4));
  float wrap = max(dot(n, key) * 0.6 + 0.4, 0.0);
  float fillTerm = max(dot(n, fill), 0.0) * 0.25;
  vec3 hemi = mix(vec3(0.42, 0.40, 0.37), vec3(1.0, 0.98, 0.94), n.y * 0.5 + 0.5);
  float spec = pow(max(dot(n, normalize(key + v)), 0.0), shininess) * specular;
  float fresnel = pow(1.0 - max(dot(n, v), 0.0), 3.0);
  vec3 color = base * (hemi * 0.38 + wrap * 0.7 + fillTerm) + spec + fresnel * 0.14;
  // Screen light reflected by near, diffuse surfaces: the idea the product measures.
  color = mix(color, color * (0.55 + uFlash * 0.75), uShow * 0.8) + uFlash * uShow * 0.06;
  return color;
}
`;

const SHEET_VS = `${COMMON}
in vec2 aGrid;
uniform float uLayer;
uniform float uBase;
uniform float uScale;
uniform float uTurn;
uniform float uAmp;
out vec3 vWorld;
out vec3 vNormal;
out vec2 vUv;
float height(vec2 p) {
  float edge = smoothstep(0.25, 1.0, max(abs(p.x), abs(p.y)));
  float t = uTime;
  float w = 0.15 * sin(2.1 * p.x + 1.2 * p.y + t * 0.8 + uLayer * 0.32)
          + 0.09 * sin(3.2 * p.y - 1.6 * p.x + t * 1.15 + uLayer * 0.55)
          + 0.05 * sin(5.3 * p.x + 4.1 * p.y - t * 1.05 + uLayer * 0.9);
  float dent = 0.16 * exp(-dot(p, p) * 3.2);
  return w * (0.25 + edge * 0.75) * uAmp - dent;
}
vec3 place(vec2 g) {
  vec2 p = g * uScale;
  float c = cos(uTurn), s = sin(uTurn);
  p = vec2(c * p.x - s * p.y, s * p.x + c * p.y);
  return vec3(p.x, uBase + height(g), p.y);
}
void main() {
  float e = 0.02;
  vec3 p = place(aGrid);
  vec3 dx = place(aGrid + vec2(e, 0.0)) - p;
  vec3 dz = place(aGrid + vec2(0.0, e)) - p;
  vNormal = normalize(cross(dz, dx));
  vWorld = p;
  vUv = aGrid * 0.5 + 0.5;
  gl_Position = uViewProj * vec4(p, 1.0);
}`;

const SHEET_FS = `#version 300 es
precision highp float;
uniform float uTime;
uniform int uMaterial;
uniform vec3 uColor;
${LIGHTING}
in vec3 vWorld;
in vec3 vNormal;
in vec2 vUv;
out vec4 outColor;
void main() {
  vec3 n = normalize(vNormal);
  if (dot(n, uCamera - vWorld) < 0.0) n = -n;
  vec3 base = uColor;
  float shininess = 40.0;
  float specular = 0.35;
  float grain = noise(vUv * 9.0) * 0.6 + noise(vUv * 31.0) * 0.4;
  if (uMaterial == 0) {          // brushed silver foil
    base *= 0.72 + grain * 0.3;
    shininess = 28.0; specular = 0.55;
  } else if (uMaterial == 1) {   // chartreuse gel
    base *= 0.92 + grain * 0.1;
    shininess = 90.0; specular = 0.9;
  } else if (uMaterial == 2) {   // graphite felt
    base *= 0.75 + grain * 0.45;
    shininess = 12.0; specular = 0.08;
  } else {                       // orange perforated mesh
    vec2 cell = fract(vUv * 70.0) - 0.5;
    base *= mix(0.7, 1.05, smoothstep(0.18, 0.24, length(cell)));
    shininess = 50.0; specular = 0.45;
  }
  vec3 color = shade(base, n, vWorld, shininess, specular);
  float rim = 1.0 - smoothstep(0.0, 0.012, min(min(vUv.x, 1.0 - vUv.x), min(vUv.y, 1.0 - vUv.y)));
  color = mix(color, vec3(0.97, 0.96, 0.93), rim * 0.65);
  outColor = vec4(pow(color, vec3(0.92)), 1.0);
}`;

const MESH_VS = `${COMMON}
in vec3 aPosition;
in vec3 aNormal;
in vec2 aUv;
in float aMaterial;
uniform mat4 uModel;
out vec3 vWorld;
out vec3 vNormal;
out vec2 vUv;
out float vMaterial;
out float vZ;
void main() {
  vec4 world = uModel * vec4(aPosition, 1.0);
  vWorld = world.xyz;
  vNormal = normalize(mat3(uModel) * aNormal);
  vUv = aUv;
  vMaterial = aMaterial;
  vZ = aPosition.z;
  gl_Position = uViewProj * world;
}`;

const MESH_FS = `#version 300 es
precision highp float;
uniform float uTime;
${LIGHTING}
in vec3 vWorld;
in vec3 vNormal;
in vec2 vUv;
in float vMaterial;
in float vZ;
out vec4 outColor;
void main() {
  vec3 n = normalize(vNormal);
  vec3 v = normalize(uCamera - vWorld);
  vec3 color;
  if (vMaterial < 0.5) {                       // barrel
    vec3 base = vec3(0.9, 0.89, 0.86);
    float knurl = step(0.14, vZ) * step(vZ, 0.32) * (0.5 + 0.5 * sin(vUv.x * 520.0));
    base *= 1.0 - knurl * 0.16;
    float band = smoothstep(0.405, 0.41, vZ) * (1.0 - smoothstep(0.425, 0.43, vZ));
    base = mix(base, vec3(0.93, 0.5, 0.18), band);
    color = shade(base, n, vWorld, 60.0, 0.6);
  } else if (vMaterial < 1.5) {                // copper ring
    color = shade(vec3(0.92, 0.52, 0.2), n, vWorld, 80.0, 0.9);
  } else if (vMaterial < 2.5) {                // inner wall
    color = shade(vec3(0.08, 0.08, 0.09), n, vWorld, 30.0, 0.3);
  } else {                                     // coated glass
    float r = length(vUv);
    float a = atan(vUv.y, vUv.x);
    float fresnel = pow(1.0 - max(dot(n, v), 0.0), 2.0);
    float hue = r * 1.5 + fresnel * 0.9 + 0.12 * sin(a * 3.0 + uTime * 0.45);
    vec3 film = 0.5 + 0.5 * cos(6.28318 * (hue + vec3(0.0, 0.33, 0.67)));
    vec3 deep = vec3(0.02, 0.03, 0.09);
    color = mix(deep, film * vec3(0.55, 0.6, 1.0), 0.75 * smoothstep(0.12, 0.95, r));
    float blades = smoothstep(0.0, 0.06, abs(fract(a * 7.0 / 6.28318 + r * 1.3) - 0.5));
    color *= mix(0.55, 1.0, blades * smoothstep(0.2, 0.5, r) + (1.0 - smoothstep(0.2, 0.5, r)));
    color *= smoothstep(0.1, 0.18, r) * 0.85 + 0.15;
    vec2 glint = vUv - vec2(-0.38, 0.4);
    color += vec3(1.0) * exp(-dot(glint, glint) * 55.0) * 0.9;
    color += uFlash * uShow * 0.55 * (1.0 - r * 0.5);
  }
  outColor = vec4(pow(color, vec3(0.92)), 1.0);
}`;

// --- tiny matrix helpers (column-major) ---
const mat = {
  perspective(fov, aspect, near, far) {
    const f = 1 / Math.tan(fov / 2), nf = 1 / (near - far);
    return [f / aspect, 0, 0, 0, 0, f, 0, 0, 0, 0, (far + near) * nf, -1, 0, 0, 2 * far * near * nf, 0];
  },
  lookAt(eye, target, up) {
    const z = norm(sub(eye, target)), x = norm(cross(up, z)), y = cross(z, x);
    return [x[0], y[0], z[0], 0, x[1], y[1], z[1], 0, x[2], y[2], z[2], 0,
      -dot(x, eye), -dot(y, eye), -dot(z, eye), 1];
  },
  multiply(a, b) {
    const out = new Array(16);
    for (let c = 0; c < 4; c++) for (let r = 0; r < 4; r++) {
      out[c * 4 + r] = a[r] * b[c * 4] + a[4 + r] * b[c * 4 + 1] + a[8 + r] * b[c * 4 + 2] + a[12 + r] * b[c * 4 + 3];
    }
    return out;
  },
  translate: (x, y, z) => [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, x, y, z, 1],
  rotateX: (a) => [1, 0, 0, 0, 0, Math.cos(a), Math.sin(a), 0, 0, -Math.sin(a), Math.cos(a), 0, 0, 0, 0, 1],
  rotateY: (a) => [Math.cos(a), 0, -Math.sin(a), 0, 0, 1, 0, 0, Math.sin(a), 0, Math.cos(a), 0, 0, 0, 0, 1],
  rotateZ: (a) => [Math.cos(a), Math.sin(a), 0, 0, -Math.sin(a), Math.cos(a), 0, 0, 0, 0, 1, 0, 0, 0, 0, 1],
};
const sub = (a, b) => [a[0] - b[0], a[1] - b[1], a[2] - b[2]];
const dot = (a, b) => a[0] * b[0] + a[1] * b[1] + a[2] * b[2];
const cross = (a, b) => [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]];
const norm = (a) => { const l = Math.hypot(...a) || 1; return [a[0] / l, a[1] / l, a[2] / l]; };

function compile(gl, vs, fs) {
  const program = gl.createProgram();
  for (const [type, source] of [[gl.VERTEX_SHADER, vs], [gl.FRAGMENT_SHADER, fs]]) {
    const shader = gl.createShader(type);
    gl.shaderSource(shader, source);
    gl.compileShader(shader);
    if (!gl.getShaderParameter(shader, gl.COMPILE_STATUS)) throw new Error(gl.getShaderInfoLog(shader));
    gl.attachShader(program, shader);
  }
  gl.linkProgram(program);
  if (!gl.getProgramParameter(program, gl.LINK_STATUS)) throw new Error(gl.getProgramInfoLog(program));
  const uniforms = {};
  const count = gl.getProgramParameter(program, gl.ACTIVE_UNIFORMS);
  for (let i = 0; i < count; i++) {
    const { name } = gl.getActiveUniform(program, i);
    uniforms[name] = gl.getUniformLocation(program, name);
  }
  return { program, uniforms };
}

function sheetGrid(segments) {
  const positions = [], indices = [];
  for (let z = 0; z <= segments; z++) for (let x = 0; x <= segments; x++) {
    positions.push((x / segments) * 2 - 1, (z / segments) * 2 - 1);
  }
  const row = segments + 1;
  for (let z = 0; z < segments; z++) for (let x = 0; x < segments; x++) {
    const a = z * row + x;
    indices.push(a, a + 1, a + row, a + 1, a + row + 1, a + row);
  }
  return { positions: new Float32Array(positions), indices: new Uint32Array(indices) };
}

// Lens built along +z: barrel, copper front ring, recessed inner wall and glass.
function lensMesh() {
  const data = [], indices = [];
  const R = 0.3, inner = 0.245, length = 0.55, steps = 72;
  const push = (p, n, uv, m) => { data.push(...p, ...n, ...uv, m); return data.length / 9 - 1; };
  const tube = (radius, z0, z1, material, inward) => {
    const start = data.length / 9;
    for (let i = 0; i <= steps; i++) {
      const a = (i / steps) * Math.PI * 2, c = Math.cos(a), s = Math.sin(a);
      const n = inward ? [-c, -s, 0] : [c, s, 0];
      push([c * radius, s * radius, z0], n, [i / steps, 0], material);
      push([c * radius, s * radius, z1], n, [i / steps, 1], material);
    }
    for (let i = 0; i < steps; i++) {
      const a = start + i * 2;
      indices.push(a, a + 2, a + 1, a + 1, a + 2, a + 3);
    }
  };
  const disk = (r0, r1, z, material, uvScale) => {
    const start = data.length / 9;
    for (let i = 0; i <= steps; i++) {
      const a = (i / steps) * Math.PI * 2, c = Math.cos(a), s = Math.sin(a);
      push([c * r0, s * r0, z], [0, 0, 1], [c * r0 * uvScale, s * r0 * uvScale], material);
      push([c * r1, s * r1, z], [0, 0, 1], [c * r1 * uvScale, s * r1 * uvScale], material);
    }
    for (let i = 0; i < steps; i++) {
      const a = start + i * 2;
      indices.push(a, a + 2, a + 1, a + 1, a + 2, a + 3);
    }
  };
  tube(R, 0, length, 0, false);
  disk(inner, R, length, 1, 1);
  tube(inner, length - 0.07, length, 2, true);
  disk(0.0001, inner, length - 0.07, 3, 1 / inner);
  disk(0.0001, R, 0, 0, 1);
  return { data: new Float32Array(data), indices: new Uint32Array(indices) };
}

const PRESETS = {
  hero: {
    lens: true,
    layers: [
      [0, [0.86, 0.86, 0.84]], [2, [0.24, 0.24, 0.25]], [1, [0.86, 0.94, 0.16]],
      [0, [0.9, 0.9, 0.88]], [2, [0.3, 0.3, 0.31]], [0, [0.84, 0.84, 0.82]],
      [3, [1.0, 0.45, 0.1]], [0, [0.92, 0.92, 0.9]],
    ],
    distance: 5.4,
  },
  stack: {
    lens: false,
    layers: [[0, [0.88, 0.88, 0.86]], [1, [0.86, 0.94, 0.16]], [2, [0.26, 0.26, 0.27]], [3, [1.0, 0.45, 0.1]], [0, [0.92, 0.92, 0.9]]],
    distance: 4.2,
  },
};

export function mountLightStack(canvas, { preset = "hero", reducedMotion = false } = {}) {
  const gl = canvas.getContext("webgl2", { antialias: true, alpha: true, premultipliedAlpha: true });
  if (!gl) return null;
  const config = PRESETS[preset] || PRESETS.hero;
  const sheet = compile(gl, SHEET_VS, SHEET_FS);
  const mesh = compile(gl, MESH_VS, MESH_FS);

  const grid = sheetGrid(80);
  const sheetVao = gl.createVertexArray();
  gl.bindVertexArray(sheetVao);
  gl.bindBuffer(gl.ARRAY_BUFFER, gl.createBuffer());
  gl.bufferData(gl.ARRAY_BUFFER, grid.positions, gl.STATIC_DRAW);
  const gridLoc = gl.getAttribLocation(sheet.program, "aGrid");
  gl.enableVertexAttribArray(gridLoc);
  gl.vertexAttribPointer(gridLoc, 2, gl.FLOAT, false, 0, 0);
  gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, gl.createBuffer());
  gl.bufferData(gl.ELEMENT_ARRAY_BUFFER, grid.indices, gl.STATIC_DRAW);

  let lens = null;
  if (config.lens) {
    const geometry = lensMesh();
    const vao = gl.createVertexArray();
    gl.bindVertexArray(vao);
    gl.bindBuffer(gl.ARRAY_BUFFER, gl.createBuffer());
    gl.bufferData(gl.ARRAY_BUFFER, geometry.data, gl.STATIC_DRAW);
    const stride = 9 * 4;
    for (const [name, size, offset] of [["aPosition", 3, 0], ["aNormal", 3, 3], ["aUv", 2, 6], ["aMaterial", 1, 8]]) {
      const loc = gl.getAttribLocation(mesh.program, name);
      gl.enableVertexAttribArray(loc);
      gl.vertexAttribPointer(loc, size, gl.FLOAT, false, stride, offset * 4);
    }
    gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, gl.createBuffer());
    gl.bufferData(gl.ELEMENT_ARRAY_BUFFER, geometry.indices, gl.STATIC_DRAW);
    lens = { vao, count: geometry.indices.length };
  }
  gl.bindVertexArray(null);
  gl.enable(gl.DEPTH_TEST);

  const state = {
    pointer: [0, 0], eased: [0, 0], show: 0, showTarget: 0, flash: [1, 1, 1],
    running: false, visible: true, frame: 0, start: performance.now(), frozenAt: 1.6,
  };
  const spacing = 0.105;
  const top = ((config.layers.length - 1) * spacing) / 2;

  function resize() {
    const ratio = Math.min(window.devicePixelRatio || 1, 2);
    const width = Math.max(1, Math.round(canvas.clientWidth * ratio));
    const height = Math.max(1, Math.round(canvas.clientHeight * ratio));
    if (canvas.width !== width || canvas.height !== height) {
      canvas.width = width;
      canvas.height = height;
    }
  }

  function flashColor(t) {
    const slot = t * 2.5;
    const index = Math.max(0, Math.floor(slot));
    // Hold each color for two thirds of the slot, then crossfade (no hard flashes).
    const blend = Math.max(0, (slot - index - 0.66) * 3);
    const from = SHOW_PALETTE[index % SHOW_PALETTE.length];
    const to = SHOW_PALETTE[(index + 1) % SHOW_PALETTE.length];
    return from.map((value, i) => value + (to[i] - value) * blend);
  }

  function draw(now) {
    resize();
    const t = reducedMotion ? state.frozenAt : Math.max(0, (now - state.start) / 1000);
    state.eased[0] += (state.pointer[0] - state.eased[0]) * 0.06;
    state.eased[1] += (state.pointer[1] - state.eased[1]) * 0.06;
    state.show += (state.showTarget - state.show) * 0.05;
    state.flash = flashColor(t);
    const amp = 1 + state.show * 0.55;

    gl.viewport(0, 0, canvas.width, canvas.height);
    gl.clearColor(0, 0, 0, 0);
    gl.clear(gl.COLOR_BUFFER_BIT | gl.DEPTH_BUFFER_BIT);
    const azimuth = -0.62 + Math.sin(t * 0.25) * 0.12 + state.eased[0] * 0.35;
    const elevation = 0.5 + state.eased[1] * 0.12;
    const d = config.distance;
    const eye = [Math.sin(azimuth) * Math.cos(elevation) * d, Math.sin(elevation) * d, Math.cos(azimuth) * Math.cos(elevation) * d];
    const view = mat.lookAt(eye, [0, 0.05, 0], [0, 1, 0]);
    const proj = mat.perspective(0.56, canvas.width / canvas.height, 0.1, 30);
    const viewProj = mat.multiply(proj, view);

    gl.useProgram(sheet.program);
    const u = sheet.uniforms;
    gl.uniformMatrix4fv(u.uViewProj, false, viewProj);
    gl.uniform1f(u.uTime, t);
    gl.uniform3fv(u.uCamera, eye);
    gl.uniform3fv(u.uFlash, state.flash);
    gl.uniform1f(u.uShow, state.show);
    gl.uniform1f(u.uAmp, amp);
    gl.bindVertexArray(sheetVao);
    config.layers.forEach(([material, color], i) => {
      gl.uniform1f(u.uLayer, i);
      gl.uniform1f(u.uBase, top - i * spacing);
      gl.uniform1f(u.uScale, 1 - Math.abs(Math.sin(i * 1.7)) * 0.07);
      gl.uniform1f(u.uTurn, Math.sin(i * 2.3) * 0.09);
      gl.uniform1i(u.uMaterial, material);
      gl.uniform3fv(u.uColor, color);
      gl.drawElements(gl.TRIANGLES, grid.indices.length, gl.UNSIGNED_INT, 0);
    });

    if (lens) {
      // Rest the lens in the dent of the top sheet and let it ride the wave.
      const bob = (0.15 * Math.sin(t * 0.8) + 0.09 * Math.sin(t * 1.15)) * 0.3 * amp - 0.16;
      const spin = state.show * t * 0.6;
      const model = mat.multiply(
        mat.translate(0.02, top + bob + 0.21, 0.04),
        mat.multiply(mat.rotateY(0.15 + Math.sin(t * 0.4) * 0.08), mat.multiply(mat.rotateX(-0.32), mat.multiply(mat.rotateZ(spin), mat.translate(0, 0, -0.3)))),
      );
      gl.useProgram(mesh.program);
      const m = mesh.uniforms;
      gl.uniformMatrix4fv(m.uViewProj, false, viewProj);
      gl.uniformMatrix4fv(m.uModel, false, model);
      gl.uniform1f(m.uTime, t);
      gl.uniform3fv(m.uCamera, eye);
      gl.uniform3fv(m.uFlash, state.flash);
      gl.uniform1f(m.uShow, state.show);
      gl.bindVertexArray(lens.vao);
      gl.drawElements(gl.TRIANGLES, lens.count, gl.UNSIGNED_INT, 0);
    }
    gl.bindVertexArray(null);
  }

  function loop(now) {
    if (!state.running) return;
    draw(now);
    state.frame = requestAnimationFrame(loop);
  }

  function setRunning() {
    const should = state.visible && !document.hidden && (!reducedMotion || Math.abs(state.show - state.showTarget) > 0.01);
    if (should && !state.running) {
      state.running = true;
      state.frame = requestAnimationFrame(loop);
    } else if (!should && state.running) {
      state.running = false;
      cancelAnimationFrame(state.frame);
    }
  }

  const observer = new IntersectionObserver(([entry]) => {
    state.visible = entry.isIntersecting;
    setRunning();
  });
  observer.observe(canvas);
  document.addEventListener("visibilitychange", setRunning);
  new ResizeObserver(() => { if (!state.running) draw(performance.now()); }).observe(canvas);

  const host = canvas.closest("[data-stage]") || canvas;
  host.addEventListener("pointermove", (event) => {
    const box = host.getBoundingClientRect();
    state.pointer = [((event.clientX - box.left) / box.width) * 2 - 1, ((event.clientY - box.top) / box.height) * 2 - 1];
    if (reducedMotion) draw(performance.now());
  });
  host.addEventListener("pointerleave", () => { state.pointer = [0, 0]; });

  draw(performance.now());
  setRunning();
  return {
    setShow(on) {
      state.showTarget = on ? 1 : 0;
      if (reducedMotion) { state.show = state.showTarget; draw(performance.now()); }
      setRunning();
    },
  };
}

const canvas = document.getElementById("schematicCanvas");
const ctx = canvas.getContext("2d");
const scopeCanvas = document.getElementById("scopeCanvas");
const scopeCtx = scopeCanvas.getContext("2d");

const GRID = 20;
const GMIN = 1e-9;
const VT = 0.02585;

const PARTS = {
  resistor: {
    name: "Resistor",
    prefix: "R",
    pins: [
      { name: "a", x: -48, y: 0 },
      { name: "b", x: 48, y: 0 },
    ],
    defaults: { value: "1k" },
  },
  capacitor: {
    name: "Capacitor",
    prefix: "C",
    pins: [
      { name: "a", x: -42, y: 0 },
      { name: "b", x: 42, y: 0 },
    ],
    defaults: { value: "100n" },
  },
  vsource: {
    name: "V Source",
    prefix: "V",
    pins: [
      { name: "p", x: 0, y: -44 },
      { name: "n", x: 0, y: 44 },
    ],
    defaults: { value: "source", dc: 0, amp: 1, freq: 1000 },
  },
  isource: {
    name: "I Source",
    prefix: "I",
    pins: [
      { name: "p", x: 0, y: -44 },
      { name: "n", x: 0, y: 44 },
    ],
    defaults: { value: "source", dc: 0.001, amp: 0, freq: 1000 },
  },
  diode: {
    name: "Diode",
    prefix: "D",
    pins: [
      { name: "a", x: -46, y: 0 },
      { name: "k", x: 46, y: 0 },
    ],
    defaults: { value: "1N4148" },
  },
  npn: {
    name: "NPN",
    prefix: "Q",
    pins: [
      { name: "c", x: 42, y: -48 },
      { name: "b", x: -42, y: 0 },
      { name: "e", x: 42, y: 48 },
    ],
    defaults: { value: "NPN", gain: 100 },
  },
  pnp: {
    name: "PNP",
    prefix: "Q",
    pins: [
      { name: "c", x: 42, y: 48 },
      { name: "b", x: -42, y: 0 },
      { name: "e", x: 42, y: -48 },
    ],
    defaults: { value: "PNP", gain: 80 },
  },
  opamp: {
    name: "Op Amp",
    prefix: "U",
    pins: [
      { name: "inp", x: -58, y: -24 },
      { name: "inm", x: -58, y: 24 },
      { name: "out", x: 66, y: 0 },
      { name: "vp", x: 0, y: -62 },
      { name: "vm", x: 0, y: 62 },
    ],
    defaults: { value: "ideal", gain: 100000 },
  },
  ground: {
    name: "Ground",
    prefix: "GND",
    pins: [{ name: "g", x: 0, y: -28 }],
    defaults: { value: "0" },
  },
};

const TOOLS = [
  { id: "select", label: "Select" },
  { id: "wire", label: "Wire" },
];

let state = {
  title: "RC low-pass filter",
  components: [],
  wires: [],
  nextId: 1,
};

let activeTool = "select";
let selectedId = null;
let wireStart = null;
let dragging = null;
let lastSim = null;
let selectedProbe = "";

function parseValue(input, fallback = 0) {
  if (typeof input === "number") return input;
  if (!input) return fallback;
  let s = String(input).trim().toLowerCase();
  s = s.replace(/ohms?|hz|farads?|amps?|volts?/g, "");
  s = s.replace(/\s+/g, "");
  s = s.replace("meg", "e6");
  s = s.replace("k", "e3");
  s = s.replace("m", "e-3");
  s = s.replace("u", "e-6");
  s = s.replace("n", "e-9");
  s = s.replace("p", "e-12");
  s = s.replace("g", "e9");
  const value = Number(s);
  return Number.isFinite(value) ? value : fallback;
}

function formatNumber(value, digits = 4) {
  if (!Number.isFinite(value)) return "nan";
  if (Math.abs(value) >= 1000 || (Math.abs(value) > 0 && Math.abs(value) < 0.001)) {
    return value.toExponential(3);
  }
  return value.toFixed(digits).replace(/\.?0+$/, "");
}

function snap(value) {
  return Math.round(value / GRID) * GRID;
}

function makeComponent(type, x, y, overrides = {}) {
  const def = PARTS[type];
  const n = state.components.filter((c) => PARTS[c.type].prefix === def.prefix).length + 1;
  const id = `${def.prefix}${n}`;
  return {
    id,
    type,
    x,
    y,
    value: def.defaults.value || "",
    dc: def.defaults.dc || 0,
    amp: def.defaults.amp || 0,
    freq: def.defaults.freq || 0,
    gain: def.defaults.gain || 0,
    ...overrides,
  };
}

function pinKey(componentId, pinName) {
  return `${componentId}:${pinName}`;
}

function getComponent(id) {
  return state.components.find((c) => c.id === id) || null;
}

function getPins(comp) {
  return PARTS[comp.type].pins.map((pin) => ({
    ...pin,
    componentId: comp.id,
    x: comp.x + pin.x,
    y: comp.y + pin.y,
  }));
}

function componentBounds(comp) {
  const pins = getPins(comp);
  const xs = pins.map((p) => p.x).concat([comp.x - 62, comp.x + 62]);
  const ys = pins.map((p) => p.y).concat([comp.y - 62, comp.y + 62]);
  return {
    x1: Math.min(...xs),
    y1: Math.min(...ys),
    x2: Math.max(...xs),
    y2: Math.max(...ys),
  };
}

function unionFind(keys) {
  const parent = new Map();
  keys.forEach((key) => parent.set(key, key));
  function find(key) {
    if (!parent.has(key)) parent.set(key, key);
    let p = parent.get(key);
    if (p !== key) {
      p = find(p);
      parent.set(key, p);
    }
    return p;
  }
  function union(a, b) {
    const ra = find(a);
    const rb = find(b);
    if (ra !== rb) parent.set(rb, ra);
  }
  return { find, union };
}

function resolveNets() {
  const keys = ["0"];
  for (const comp of state.components) {
    for (const pin of PARTS[comp.type].pins) keys.push(pinKey(comp.id, pin.name));
  }
  const uf = unionFind(keys);
  for (const wire of state.wires) {
    uf.union(pinKey(wire.a.componentId, wire.a.pin), pinKey(wire.b.componentId, wire.b.pin));
  }
  for (const comp of state.components) {
    if (comp.type === "ground") {
      uf.union("0", pinKey(comp.id, "g"));
    }
  }

  const rootToName = new Map();
  rootToName.set(uf.find("0"), "0");
  let count = 1;
  const pinNet = new Map();
  const netPins = new Map();

  for (const comp of state.components) {
    for (const pin of PARTS[comp.type].pins) {
      const key = pinKey(comp.id, pin.name);
      const root = uf.find(key);
      if (!rootToName.has(root)) rootToName.set(root, `N${count++}`);
      const net = rootToName.get(root);
      pinNet.set(key, net);
      if (!netPins.has(net)) netPins.set(net, []);
      netPins.get(net).push(`${comp.id}.${pin.name}`);
    }
  }

  const nodes = [...new Set([...pinNet.values()].filter((n) => n !== "0"))].sort((a, b) =>
    a.localeCompare(b, undefined, { numeric: true }),
  );
  return { pinNet, netPins, nodes };
}

function sourceAt(comp, t, mode) {
  const dc = Number(comp.dc) || 0;
  if (mode === "dc") return dc;
  const amp = Number(comp.amp) || 0;
  const freq = Number(comp.freq) || 0;
  return dc + amp * Math.sin(2 * Math.PI * freq * t);
}

function getVoltage(x, nodeIndex, node) {
  if (node === "0" || !node) return 0;
  return x[nodeIndex.get(node)] || 0;
}

function expLimited(x) {
  return Math.exp(Math.max(-40, Math.min(40, x)));
}

function diodeCurrent(vd) {
  const isat = 1e-12;
  return isat * (expLimited(vd / VT) - 1);
}

function bjtCurrents(type, vc, vb, ve, beta) {
  const isBase = type === "npn" ? 1.2e-15 : 1.6e-15;
  const b = Math.max(8, beta || (type === "npn" ? 100 : 80));
  if (type === "npn") {
    const vbe = vb - ve;
    const vbc = vb - vc;
    const ibe = isBase * (expLimited(vbe / VT) - 1);
    const ibc = 0.08 * isBase * (expLimited(vbc / VT) - 1);
    const ice = b * ibe * Math.max(0.12, Math.min(2.5, 1 + (vc - ve) / 90));
    return {
      c: ice - ibc,
      b: ibe + ibc,
      e: -ibe - ice,
    };
  }
  const veb = ve - vb;
  const vcb = vc - vb;
  const ieb = isBase * (expLimited(veb / VT) - 1);
  const icb = 0.08 * isBase * (expLimited(vcb / VT) - 1);
  const iec = b * ieb * Math.max(0.12, Math.min(2.5, 1 + (ve - vc) / 90));
  return {
    c: icb - iec,
    b: -ieb - icb,
    e: ieb + iec,
  };
}

function branchComponents() {
  return state.components.filter((c) => c.type === "vsource" || c.type === "opamp");
}

function buildCircuit() {
  const nets = resolveNets();
  const nodeIndex = new Map();
  nets.nodes.forEach((node, index) => nodeIndex.set(node, index));
  const branches = branchComponents();
  const branchIndex = new Map();
  branches.forEach((comp, index) => branchIndex.set(comp.id, nets.nodes.length + index));
  return {
    ...nets,
    nodeIndex,
    branches,
    branchIndex,
    size: nets.nodes.length + branches.length,
  };
}

function compNet(circuit, comp, pin) {
  return circuit.pinNet.get(pinKey(comp.id, pin));
}

function residual(x, circuit, t, dt, capPrev, mode) {
  const r = Array(circuit.size).fill(0);
  const stamp = (node, current) => {
    if (node !== "0" && circuit.nodeIndex.has(node)) r[circuit.nodeIndex.get(node)] += current;
  };

  for (const node of circuit.nodes) {
    stamp(node, getVoltage(x, circuit.nodeIndex, node) * GMIN);
  }

  for (const comp of state.components) {
    if (comp.type === "resistor") {
      const a = compNet(circuit, comp, "a");
      const b = compNet(circuit, comp, "b");
      const value = Math.max(parseValue(comp.value, 1000), 1e-6);
      const i = (getVoltage(x, circuit.nodeIndex, a) - getVoltage(x, circuit.nodeIndex, b)) / value;
      stamp(a, i);
      stamp(b, -i);
    } else if (comp.type === "capacitor" && mode === "tran" && dt > 0) {
      const a = compNet(circuit, comp, "a");
      const b = compNet(circuit, comp, "b");
      const value = Math.max(parseValue(comp.value, 100e-9), 0);
      const g = value / dt;
      const vNow = getVoltage(x, circuit.nodeIndex, a) - getVoltage(x, circuit.nodeIndex, b);
      const vPrev = capPrev.get(comp.id) || 0;
      const i = g * (vNow - vPrev);
      stamp(a, i);
      stamp(b, -i);
    } else if (comp.type === "vsource") {
      const p = compNet(circuit, comp, "p");
      const n = compNet(circuit, comp, "n");
      const bi = circuit.branchIndex.get(comp.id);
      const current = x[bi] || 0;
      stamp(p, current);
      stamp(n, -current);
      r[bi] = getVoltage(x, circuit.nodeIndex, p) - getVoltage(x, circuit.nodeIndex, n) - sourceAt(comp, t, mode);
    } else if (comp.type === "isource") {
      const p = compNet(circuit, comp, "p");
      const n = compNet(circuit, comp, "n");
      const i = sourceAt(comp, t, mode);
      stamp(p, i);
      stamp(n, -i);
    } else if (comp.type === "diode") {
      const a = compNet(circuit, comp, "a");
      const k = compNet(circuit, comp, "k");
      const vd = getVoltage(x, circuit.nodeIndex, a) - getVoltage(x, circuit.nodeIndex, k);
      const i = diodeCurrent(vd);
      stamp(a, i);
      stamp(k, -i);
    } else if (comp.type === "npn" || comp.type === "pnp") {
      const c = compNet(circuit, comp, "c");
      const b = compNet(circuit, comp, "b");
      const e = compNet(circuit, comp, "e");
      const currents = bjtCurrents(
        comp.type,
        getVoltage(x, circuit.nodeIndex, c),
        getVoltage(x, circuit.nodeIndex, b),
        getVoltage(x, circuit.nodeIndex, e),
        Number(comp.gain) || 0,
      );
      stamp(c, currents.c);
      stamp(b, currents.b);
      stamp(e, currents.e);
    } else if (comp.type === "opamp") {
      const inp = compNet(circuit, comp, "inp");
      const inm = compNet(circuit, comp, "inm");
      const out = compNet(circuit, comp, "out");
      const vp = compNet(circuit, comp, "vp");
      const vm = compNet(circuit, comp, "vm");
      const bi = circuit.branchIndex.get(comp.id);
      const current = x[bi] || 0;
      stamp(out, current);
      const gain = Math.max(1, Number(comp.gain) || 100000);
      const vd = getVoltage(x, circuit.nodeIndex, inp) - getVoltage(x, circuit.nodeIndex, inm);
      let high = getVoltage(x, circuit.nodeIndex, vp);
      let low = getVoltage(x, circuit.nodeIndex, vm);
      if (Math.abs(high - low) < 1) {
        high = 15;
        low = -15;
      }
      const mid = (high + low) / 2;
      const span = Math.max(0.5, (high - low) / 2 - 0.8);
      const target = mid + span * Math.tanh((gain * vd) / span);
      r[bi] = getVoltage(x, circuit.nodeIndex, out) - target;
    }
  }
  return r;
}

function solveLinear(a, b) {
  const n = b.length;
  const aug = a.map((row, i) => row.slice().concat([b[i]]));
  for (let col = 0; col < n; col += 1) {
    let pivot = col;
    for (let row = col + 1; row < n; row += 1) {
      if (Math.abs(aug[row][col]) > Math.abs(aug[pivot][col])) pivot = row;
    }
    if (Math.abs(aug[pivot][col]) < 1e-18) throw new Error("Singular circuit matrix");
    if (pivot !== col) [aug[pivot], aug[col]] = [aug[col], aug[pivot]];
    const div = aug[col][col];
    for (let j = col; j <= n; j += 1) aug[col][j] /= div;
    for (let row = 0; row < n; row += 1) {
      if (row === col) continue;
      const factor = aug[row][col];
      if (Math.abs(factor) < 1e-24) continue;
      for (let j = col; j <= n; j += 1) aug[row][j] -= factor * aug[col][j];
    }
  }
  return aug.map((row) => row[n]);
}

function maxAbs(values) {
  return values.reduce((m, v) => Math.max(m, Math.abs(v)), 0);
}

function initialGuess(circuit, previous) {
  if (previous && previous.length === circuit.size) return previous.slice();
  const x = Array(circuit.size).fill(0);
  for (const comp of state.components) {
    if (comp.type === "vsource") {
      const p = compNet(circuit, comp, "p");
      const n = compNet(circuit, comp, "n");
      const value = Number(comp.dc) || 0;
      if (n === "0" && circuit.nodeIndex.has(p)) x[circuit.nodeIndex.get(p)] = value;
      if (p === "0" && circuit.nodeIndex.has(n)) x[circuit.nodeIndex.get(n)] = -value;
    }
  }
  return x;
}

function solveNewton(circuit, previous, capPrev, t, dt, mode) {
  if (circuit.size === 0) return [];
  let x = initialGuess(circuit, previous);
  for (let iter = 0; iter < 32; iter += 1) {
    const r0 = residual(x, circuit, t, dt, capPrev, mode);
    const norm = maxAbs(r0);
    if (norm < 1e-7) return x;
    const jac = Array.from({ length: circuit.size }, () => Array(circuit.size).fill(0));
    for (let col = 0; col < circuit.size; col += 1) {
      const step = 1e-5 * Math.max(1, Math.abs(x[col]));
      const trial = x.slice();
      trial[col] += step;
      const rp = residual(trial, circuit, t, dt, capPrev, mode);
      for (let row = 0; row < circuit.size; row += 1) {
        jac[row][col] = (rp[row] - r0[row]) / step;
      }
    }
    let delta;
    try {
      delta = solveLinear(jac, r0.map((v) => -v));
    } catch (err) {
      throw new Error(`${err.message}. Add a ground reference or check floating nodes.`);
    }
    let alpha = 1;
    let accepted = false;
    while (alpha >= 0.03125) {
      const candidate = x.map((v, i) => v + alpha * delta[i]);
      const rn = residual(candidate, circuit, t, dt, capPrev, mode);
      if (maxAbs(rn) < norm * 0.98 || maxAbs(rn) < 1e-6) {
        x = candidate;
        accepted = true;
        break;
      }
      alpha *= 0.5;
    }
    if (!accepted) x = x.map((v, i) => v + 0.05 * delta[i]);
  }
  return x;
}

function nodeVoltages(circuit, x) {
  const out = { 0: 0 };
  for (const node of circuit.nodes) out[node] = getVoltage(x, circuit.nodeIndex, node);
  return out;
}

function updateCapPrev(circuit, x, capPrev) {
  for (const comp of state.components) {
    if (comp.type !== "capacitor") continue;
    const a = compNet(circuit, comp, "a");
    const b = compNet(circuit, comp, "b");
    capPrev.set(comp.id, getVoltage(x, circuit.nodeIndex, a) - getVoltage(x, circuit.nodeIndex, b));
  }
}

function runDc() {
  const circuit = buildCircuit();
  try {
    const x = solveNewton(circuit, null, new Map(), 0, 0, "dc");
    const volts = nodeVoltages(circuit, x);
    lastSim = { type: "dc", circuit, points: [{ t: 0, volts }] };
    selectedProbe = selectedProbe || circuit.nodes[0] || "0";
    renderResults("DC operating point", circuit, [{ t: 0, volts }]);
    updateProbeList(circuit);
    drawScope();
    setStatus("DC solve completed.");
  } catch (err) {
    setStatus(`DC error: ${err.message}`, true);
    document.getElementById("resultsText").value = `DC error:\n${err.stack || err.message}`;
  }
}

function runTransient() {
  const circuit = buildCircuit();
  const duration = Math.max(0.0001, Number(document.getElementById("durationInput").value) || 0.01);
  const steps = Math.max(20, Math.min(1200, Number(document.getElementById("stepsInput").value) || 240));
  const dt = duration / steps;
  const capPrev = new Map();
  let previous = null;
  const points = [];
  try {
    for (let i = 0; i <= steps; i += 1) {
      const t = i * dt;
      previous = solveNewton(circuit, previous, capPrev, t, dt, "tran");
      const volts = nodeVoltages(circuit, previous);
      points.push({ t, volts });
      updateCapPrev(circuit, previous, capPrev);
    }
    lastSim = { type: "tran", circuit, points };
    selectedProbe = selectedProbe || circuit.nodes[0] || "0";
    renderResults("Transient analysis", circuit, points);
    updateProbeList(circuit);
    drawScope();
    setStatus("Transient simulation completed.");
  } catch (err) {
    setStatus(`Transient error: ${err.message}`, true);
    document.getElementById("resultsText").value = `Transient error:\n${err.stack || err.message}`;
  }
}

function renderResults(title, circuit, points) {
  const lines = [`${title}`, "", "Node voltages:"];
  const final = points[points.length - 1].volts;
  for (const node of ["0"].concat(circuit.nodes)) {
    const pins = circuit.netPins.get(node) || [];
    lines.push(`${node.padEnd(4)} ${formatNumber(final[node] || 0, 5).padStart(12)} V    ${pins.join(", ")}`);
  }
  lines.push("", "SPICE-like netlist:", "");
  lines.push(exportNetlist());
  document.getElementById("resultsText").value = lines.join("\n");
}

function updateProbeList(circuit = buildCircuit()) {
  const select = document.getElementById("probeSelect");
  const old = selectedProbe || select.value;
  select.innerHTML = "";
  for (const node of ["0"].concat(circuit.nodes)) {
    const opt = document.createElement("option");
    const pins = circuit.netPins.get(node) || [];
    opt.value = node;
    opt.textContent = `${node}${pins.length ? ` (${pins.slice(0, 3).join(", ")})` : ""}`;
    select.appendChild(opt);
  }
  selectedProbe = circuit.nodes.includes(old) || old === "0" ? old : circuit.nodes[0] || "0";
  select.value = selectedProbe;
}

function exportNetlist() {
  const circuit = buildCircuit();
  const lines = [`* ${state.title}`, "* Exported from Analog Sketch Lab"];
  for (const comp of state.components) {
    const n = (pin) => compNet(circuit, comp, pin) || "NC";
    if (comp.type === "resistor") lines.push(`${comp.id} ${n("a")} ${n("b")} ${comp.value}`);
    if (comp.type === "capacitor") lines.push(`${comp.id} ${n("a")} ${n("b")} ${comp.value}`);
    if (comp.type === "vsource") {
      lines.push(`${comp.id} ${n("p")} ${n("n")} DC ${comp.dc || 0} SIN(${comp.dc || 0} ${comp.amp || 0} ${comp.freq || 0})`);
    }
    if (comp.type === "isource") {
      lines.push(`${comp.id} ${n("p")} ${n("n")} DC ${comp.dc || 0} SIN(${comp.dc || 0} ${comp.amp || 0} ${comp.freq || 0})`);
    }
    if (comp.type === "diode") lines.push(`${comp.id} ${n("a")} ${n("k")} DDEFAULT`);
    if (comp.type === "npn") lines.push(`${comp.id} ${n("c")} ${n("b")} ${n("e")} NPNDEFAULT BF=${comp.gain || 100}`);
    if (comp.type === "pnp") lines.push(`${comp.id} ${n("c")} ${n("b")} ${n("e")} PNPDEFAULT BF=${comp.gain || 80}`);
    if (comp.type === "opamp") lines.push(`E${comp.id} ${n("out")} 0 ${n("inp")} ${n("inm")} ${comp.gain || 100000}`);
  }
  lines.push(".model DDEFAULT D(IS=1e-12 N=1)");
  lines.push(".model NPNDEFAULT NPN(IS=1.2e-15 BF=100 VAF=90)");
  lines.push(".model PNPDEFAULT PNP(IS=1.6e-15 BF=80 VAF=90)");
  lines.push(".tran 0 10m");
  lines.push(".end");
  return lines.join("\n");
}

function setStatus(message, isError = false) {
  const el = document.getElementById("statusLine");
  el.textContent = message;
  el.style.color = isError ? "var(--danger)" : "var(--muted)";
}

function clearCanvas() {
  ctx.clearRect(0, 0, canvas.width, canvas.height);
}

function drawGrid() {
  ctx.save();
  ctx.strokeStyle = "#edf0f3";
  ctx.lineWidth = 1;
  for (let x = 0; x < canvas.width; x += GRID) {
    ctx.beginPath();
    ctx.moveTo(x, 0);
    ctx.lineTo(x, canvas.height);
    ctx.stroke();
  }
  for (let y = 0; y < canvas.height; y += GRID) {
    ctx.beginPath();
    ctx.moveTo(0, y);
    ctx.lineTo(canvas.width, y);
    ctx.stroke();
  }
  ctx.restore();
}

function drawWire(pinA, pinB, active = false) {
  ctx.save();
  ctx.strokeStyle = active ? "#1665d8" : "#111316";
  ctx.lineWidth = active ? 3 : 2;
  ctx.beginPath();
  ctx.moveTo(pinA.x, pinA.y);
  ctx.lineTo(pinB.x, pinB.y);
  ctx.stroke();
  ctx.restore();
}

function findPin(componentId, pinName) {
  const comp = getComponent(componentId);
  if (!comp) return null;
  return getPins(comp).find((p) => p.name === pinName) || null;
}

function drawLabel(comp, yOffset = 72) {
  ctx.fillStyle = "#111316";
  ctx.font = "12px Segoe UI, Arial";
  ctx.textAlign = "center";
  ctx.fillText(comp.id, comp.x, comp.y + yOffset);
  if (comp.type !== "ground" && comp.value) {
    ctx.fillStyle = "#667085";
    ctx.fillText(String(comp.value), comp.x, comp.y + yOffset + 16);
  }
}

function strokeSymbol(selected = false) {
  ctx.strokeStyle = selected ? "#1665d8" : "#111316";
  ctx.fillStyle = "#111316";
  ctx.lineWidth = selected ? 2.7 : 2;
  ctx.lineCap = "round";
  ctx.lineJoin = "round";
}

function drawComponent(comp) {
  const selected = comp.id === selectedId;
  ctx.save();
  ctx.translate(comp.x, comp.y);
  strokeSymbol(selected);
  if (comp.type === "resistor") {
    ctx.beginPath();
    ctx.moveTo(-48, 0);
    ctx.lineTo(-34, 0);
    const pts = [
      [-28, -13],
      [-16, 13],
      [-4, -13],
      [8, 13],
      [20, -13],
      [32, 13],
      [38, 0],
      [48, 0],
    ];
    for (const [x, y] of pts) ctx.lineTo(x, y);
    ctx.stroke();
    drawLabel({ ...comp, x: 0, y: 0 }, 38);
  } else if (comp.type === "capacitor") {
    ctx.beginPath();
    ctx.moveTo(-42, 0);
    ctx.lineTo(-12, 0);
    ctx.moveTo(-12, -30);
    ctx.lineTo(-12, 30);
    ctx.moveTo(12, -30);
    ctx.lineTo(12, 30);
    ctx.moveTo(12, 0);
    ctx.lineTo(42, 0);
    ctx.stroke();
    drawLabel({ ...comp, x: 0, y: 0 }, 48);
  } else if (comp.type === "vsource" || comp.type === "isource") {
    ctx.beginPath();
    ctx.moveTo(0, -44);
    ctx.lineTo(0, -30);
    ctx.moveTo(0, 30);
    ctx.lineTo(0, 44);
    ctx.arc(0, 0, 30, 0, Math.PI * 2);
    ctx.stroke();
    if (comp.type === "vsource") {
      ctx.font = "17px Segoe UI, Arial";
      ctx.fillText("+", -5, -9);
      ctx.fillText("-", -4, 20);
    } else {
      ctx.beginPath();
      ctx.moveTo(0, 18);
      ctx.lineTo(0, -18);
      ctx.moveTo(0, -18);
      ctx.lineTo(-8, -8);
      ctx.moveTo(0, -18);
      ctx.lineTo(8, -8);
      ctx.stroke();
    }
    drawLabel({ ...comp, x: 0, y: 0 }, 60);
  } else if (comp.type === "diode") {
    ctx.beginPath();
    ctx.moveTo(-46, 0);
    ctx.lineTo(-16, 0);
    ctx.moveTo(-16, -24);
    ctx.lineTo(-16, 24);
    ctx.lineTo(18, 0);
    ctx.closePath();
    ctx.moveTo(18, -24);
    ctx.lineTo(18, 24);
    ctx.moveTo(18, 0);
    ctx.lineTo(46, 0);
    ctx.stroke();
    drawLabel({ ...comp, x: 0, y: 0 }, 45);
  } else if (comp.type === "npn" || comp.type === "pnp") {
    ctx.beginPath();
    ctx.arc(0, 0, 42, 0, Math.PI * 2);
    ctx.moveTo(-42, 0);
    ctx.lineTo(-12, 0);
    ctx.moveTo(-12, -26);
    ctx.lineTo(-12, 26);
    if (comp.type === "npn") {
      ctx.moveTo(-12, -14);
      ctx.lineTo(42, -48);
      ctx.moveTo(-12, 14);
      ctx.lineTo(42, 48);
      ctx.moveTo(28, 39);
      ctx.lineTo(42, 48);
      ctx.lineTo(38, 31);
    } else {
      ctx.moveTo(-12, -14);
      ctx.lineTo(42, -48);
      ctx.moveTo(-12, 14);
      ctx.lineTo(42, 48);
      ctx.moveTo(28, -39);
      ctx.lineTo(42, -48);
      ctx.lineTo(38, -31);
    }
    ctx.stroke();
    ctx.font = "11px Segoe UI, Arial";
    ctx.fillText("B", -54, 4);
    ctx.fillText("C", 54, comp.type === "npn" ? -50 : 54);
    ctx.fillText("E", 54, comp.type === "npn" ? 54 : -50);
    drawLabel({ ...comp, x: 0, y: 0 }, 72);
  } else if (comp.type === "opamp") {
    ctx.beginPath();
    ctx.moveTo(-58, -54);
    ctx.lineTo(-58, 54);
    ctx.lineTo(66, 0);
    ctx.closePath();
    ctx.moveTo(-78, -24);
    ctx.lineTo(-58, -24);
    ctx.moveTo(-78, 24);
    ctx.lineTo(-58, 24);
    ctx.moveTo(66, 0);
    ctx.lineTo(88, 0);
    ctx.moveTo(0, -62);
    ctx.lineTo(0, -37);
    ctx.moveTo(0, 62);
    ctx.lineTo(0, 37);
    ctx.stroke();
    ctx.font = "16px Segoe UI, Arial";
    ctx.fillText("+", -43, -18);
    ctx.fillText("-", -40, 31);
    ctx.font = "11px Segoe UI, Arial";
    ctx.fillText("V+", 13, -51);
    ctx.fillText("V-", 13, 58);
    drawLabel({ ...comp, x: 0, y: 0 }, 80);
  } else if (comp.type === "ground") {
    ctx.beginPath();
    ctx.moveTo(0, -28);
    ctx.lineTo(0, 0);
    ctx.moveTo(-25, 0);
    ctx.lineTo(25, 0);
    ctx.moveTo(-16, 12);
    ctx.lineTo(16, 12);
    ctx.moveTo(-8, 24);
    ctx.lineTo(8, 24);
    ctx.stroke();
    ctx.fillStyle = "#667085";
    ctx.font = "12px Segoe UI, Arial";
    ctx.textAlign = "center";
    ctx.fillText("0", 0, 44);
  }
  ctx.restore();

  for (const pin of getPins(comp)) {
    ctx.save();
    ctx.fillStyle = selected || (wireStart && wireStart.componentId === comp.id && wireStart.pin === pin.name) ? "#1665d8" : "#fff";
    ctx.strokeStyle = "#111316";
    ctx.lineWidth = 1.6;
    ctx.beginPath();
    ctx.arc(pin.x, pin.y, 5, 0, Math.PI * 2);
    ctx.fill();
    ctx.stroke();
    ctx.restore();
  }
}

function drawSchematic() {
  clearCanvas();
  drawGrid();
  for (const wire of state.wires) {
    const a = findPin(wire.a.componentId, wire.a.pin);
    const b = findPin(wire.b.componentId, wire.b.pin);
    if (a && b) drawWire(a, b);
  }
  for (const comp of state.components) drawComponent(comp);
  document.getElementById("circuitTitle").textContent = state.title;
}

function drawScope() {
  scopeCtx.clearRect(0, 0, scopeCanvas.width, scopeCanvas.height);
  scopeCtx.fillStyle = "#fff";
  scopeCtx.fillRect(0, 0, scopeCanvas.width, scopeCanvas.height);
  scopeCtx.strokeStyle = "#edf0f3";
  scopeCtx.lineWidth = 1;
  for (let x = 40; x < scopeCanvas.width - 10; x += 60) {
    scopeCtx.beginPath();
    scopeCtx.moveTo(x, 10);
    scopeCtx.lineTo(x, scopeCanvas.height - 30);
    scopeCtx.stroke();
  }
  for (let y = 20; y < scopeCanvas.height - 30; y += 40) {
    scopeCtx.beginPath();
    scopeCtx.moveTo(40, y);
    scopeCtx.lineTo(scopeCanvas.width - 10, y);
    scopeCtx.stroke();
  }
  scopeCtx.strokeStyle = "#111316";
  scopeCtx.beginPath();
  scopeCtx.moveTo(40, 10);
  scopeCtx.lineTo(40, scopeCanvas.height - 30);
  scopeCtx.lineTo(scopeCanvas.width - 10, scopeCanvas.height - 30);
  scopeCtx.stroke();

  if (!lastSim || !lastSim.points.length) return;
  const probe = selectedProbe || "0";
  const values = lastSim.points.map((p) => p.volts[probe] || 0);
  const times = lastSim.points.map((p) => p.t);
  const minV = Math.min(...values, -0.001);
  const maxV = Math.max(...values, 0.001);
  const spanV = Math.max(0.001, maxV - minV);
  const t0 = times[0];
  const t1 = times[times.length - 1] || 1;
  const plotX = (t) => 40 + ((t - t0) / Math.max(1e-12, t1 - t0)) * (scopeCanvas.width - 55);
  const plotY = (v) => 10 + (1 - (v - minV) / spanV) * (scopeCanvas.height - 40);

  scopeCtx.strokeStyle = "#1665d8";
  scopeCtx.lineWidth = 2;
  scopeCtx.beginPath();
  values.forEach((v, i) => {
    const x = plotX(times[i]);
    const y = plotY(v);
    if (i === 0) scopeCtx.moveTo(x, y);
    else scopeCtx.lineTo(x, y);
  });
  scopeCtx.stroke();

  scopeCtx.fillStyle = "#111316";
  scopeCtx.font = "12px Segoe UI, Arial";
  scopeCtx.fillText(`${formatNumber(maxV)} V`, 6, 18);
  scopeCtx.fillText(`${formatNumber(minV)} V`, 6, scopeCanvas.height - 34);
  scopeCtx.fillText(`${formatNumber(t1 * 1000, 3)} ms`, scopeCanvas.width - 78, scopeCanvas.height - 10);
  const rmsValue = Math.sqrt(values.reduce((sum, v) => sum + v * v, 0) / values.length);
  document.getElementById("scopeReadout").textContent = `${probe}: min ${formatNumber(minV)} V, max ${formatNumber(maxV)} V, rms ${formatNumber(rmsValue)} V`;
}

function hitTestPin(x, y) {
  for (let i = state.components.length - 1; i >= 0; i -= 1) {
    const comp = state.components[i];
    for (const pin of getPins(comp)) {
      const d = Math.hypot(pin.x - x, pin.y - y);
      if (d <= 10) return { componentId: comp.id, pin: pin.name, x: pin.x, y: pin.y };
    }
  }
  return null;
}

function hitTestComponent(x, y) {
  for (let i = state.components.length - 1; i >= 0; i -= 1) {
    const comp = state.components[i];
    const b = componentBounds(comp);
    if (x >= b.x1 && x <= b.x2 && y >= b.y1 && y <= b.y2) return comp;
  }
  return null;
}

function canvasPoint(evt) {
  const rect = canvas.getBoundingClientRect();
  return {
    x: (evt.clientX - rect.left) * (canvas.width / rect.width),
    y: (evt.clientY - rect.top) * (canvas.height / rect.height),
  };
}

function selectComponent(id) {
  selectedId = id;
  updateInspector();
  drawSchematic();
}

function addPart(type, x, y) {
  const comp = makeComponent(type, snap(x), snap(y));
  state.components.push(comp);
  selectComponent(comp.id);
  setStatus(`Placed ${PARTS[type].name}.`);
  updateProbeList();
}

function updateInspector() {
  const comp = getComponent(selectedId);
  const empty = document.getElementById("inspectorEmpty");
  const form = document.getElementById("inspectorForm");
  if (!comp) {
    empty.classList.remove("hidden");
    form.classList.add("hidden");
    return;
  }
  empty.classList.add("hidden");
  form.classList.remove("hidden");
  document.getElementById("compLabel").value = comp.id;
  document.getElementById("compValue").value = comp.value || "";
  document.getElementById("compDc").value = comp.dc || 0;
  document.getElementById("compAmp").value = comp.amp || 0;
  document.getElementById("compFreq").value = comp.freq || 0;
  document.getElementById("compGain").value = comp.gain || 0;
}

function applyInspector() {
  const comp = getComponent(selectedId);
  if (!comp) return;
  const newId = document.getElementById("compLabel").value.trim() || comp.id;
  if (newId !== comp.id && state.components.some((c) => c.id === newId)) {
    setStatus("Component label already exists.", true);
    return;
  }
  const oldId = comp.id;
  comp.id = newId;
  comp.value = document.getElementById("compValue").value.trim();
  comp.dc = Number(document.getElementById("compDc").value) || 0;
  comp.amp = Number(document.getElementById("compAmp").value) || 0;
  comp.freq = Number(document.getElementById("compFreq").value) || 0;
  comp.gain = Number(document.getElementById("compGain").value) || 0;
  if (oldId !== newId) {
    for (const wire of state.wires) {
      if (wire.a.componentId === oldId) wire.a.componentId = newId;
      if (wire.b.componentId === oldId) wire.b.componentId = newId;
    }
    selectedId = newId;
  }
  setStatus(`Updated ${comp.id}.`);
  updateProbeList();
  drawSchematic();
}

function deleteSelected() {
  if (!selectedId) return;
  state.components = state.components.filter((c) => c.id !== selectedId);
  state.wires = state.wires.filter((w) => w.a.componentId !== selectedId && w.b.componentId !== selectedId);
  selectedId = null;
  updateInspector();
  updateProbeList();
  drawSchematic();
  setStatus("Component deleted.");
}

function setupButtons() {
  const toolGrid = document.getElementById("toolGrid");
  for (const tool of TOOLS) {
    const btn = document.createElement("button");
    btn.textContent = tool.label;
    btn.dataset.tool = tool.id;
    btn.addEventListener("click", () => setTool(tool.id));
    toolGrid.appendChild(btn);
  }

  const partGrid = document.getElementById("partGrid");
  for (const [type, def] of Object.entries(PARTS)) {
    const btn = document.createElement("button");
    btn.textContent = def.name;
    btn.dataset.part = type;
    btn.addEventListener("click", () => setTool(type));
    partGrid.appendChild(btn);
  }
  refreshToolButtons();
}

function setTool(tool) {
  activeTool = tool;
  wireStart = null;
  refreshToolButtons();
  const label = TOOLS.find((t) => t.id === tool)?.label || PARTS[tool]?.name || tool;
  setStatus(`${label} tool selected.`);
}

function refreshToolButtons() {
  for (const btn of document.querySelectorAll("[data-tool], [data-part]")) {
    const id = btn.dataset.tool || btn.dataset.part;
    btn.classList.toggle("active", id === activeTool);
  }
}

function saveLocal() {
  localStorage.setItem("analogSketchLabCircuit", JSON.stringify(state));
  setStatus("Circuit saved in browser storage.");
}

function restoreLocal() {
  const raw = localStorage.getItem("analogSketchLabCircuit");
  if (!raw) {
    setStatus("No saved circuit in browser storage.", true);
    return;
  }
  state = JSON.parse(raw);
  selectedId = null;
  wireStart = null;
  lastSim = null;
  updateInspector();
  updateProbeList();
  drawSchematic();
  drawScope();
  setStatus("Saved circuit restored.");
}

function exportJson() {
  const data = JSON.stringify(state, null, 2);
  document.getElementById("resultsText").value = data;
  navigator.clipboard?.writeText(data).catch(() => {});
  setStatus("Circuit JSON written to Results and copied when clipboard is available.");
}

function clone(obj) {
  return JSON.parse(JSON.stringify(obj));
}

function exampleRc() {
  const components = [
    makeComponent("vsource", 150, 340, { id: "V1", dc: 0, amp: 1, freq: 1000, value: "1 V sine" }),
    makeComponent("resistor", 340, 270, { id: "R1", value: "1k" }),
    makeComponent("capacitor", 560, 340, { id: "C1", value: "100n" }),
    makeComponent("ground", 150, 470, { id: "GND1" }),
    makeComponent("ground", 560, 470, { id: "GND2" }),
  ];
  return {
    title: "RC low-pass filter",
    components,
    wires: [
      w("V1", "p", "R1", "a"),
      w("R1", "b", "C1", "a"),
      w("C1", "b", "GND2", "g"),
      w("V1", "n", "GND1", "g"),
      w("GND1", "g", "GND2", "g"),
    ],
    nextId: 100,
  };
}

function exampleRectifier() {
  const components = [
    makeComponent("vsource", 150, 350, { id: "V1", dc: 0, amp: 6, freq: 60, value: "6 V sine" }),
    makeComponent("diode", 350, 300, { id: "D1", value: "1N4148" }),
    makeComponent("capacitor", 570, 360, { id: "C1", value: "470u" }),
    makeComponent("resistor", 760, 360, { id: "RLOAD", value: "2k" }),
    makeComponent("ground", 150, 480, { id: "GND1" }),
    makeComponent("ground", 570, 490, { id: "GND2" }),
    makeComponent("ground", 760, 490, { id: "GND3" }),
  ];
  return {
    title: "Half-wave rectifier with reservoir capacitor",
    components,
    wires: [
      w("V1", "p", "D1", "a"),
      w("D1", "k", "C1", "a"),
      w("D1", "k", "RLOAD", "a"),
      w("C1", "b", "GND2", "g"),
      w("RLOAD", "b", "GND3", "g"),
      w("V1", "n", "GND1", "g"),
      w("GND1", "g", "GND2", "g"),
      w("GND2", "g", "GND3", "g"),
    ],
    nextId: 100,
  };
}

function exampleCommonEmitter() {
  const components = [
    makeComponent("vsource", 120, 210, { id: "VCC", dc: 12, amp: 0, freq: 0, value: "12 V" }),
    makeComponent("vsource", 120, 540, { id: "VIN", dc: 0, amp: 0.02, freq: 1000, value: "20 mV sine" }),
    makeComponent("resistor", 330, 170, { id: "RC", value: "2.2k" }),
    makeComponent("resistor", 320, 300, { id: "RB1", value: "82k" }),
    makeComponent("resistor", 320, 480, { id: "RB2", value: "15k" }),
    makeComponent("resistor", 325, 540, { id: "RIN", value: "4.7k" }),
    makeComponent("npn", 560, 360, { id: "Q1", value: "2N3904", gain: 120 }),
    makeComponent("resistor", 690, 470, { id: "RE", value: "680" }),
    makeComponent("ground", 120, 650, { id: "GND1" }),
    makeComponent("ground", 690, 600, { id: "GND2" }),
  ];
  return {
    title: "BJT common-emitter amplifier",
    components,
    wires: [
      w("VCC", "p", "RC", "a"),
      w("VCC", "p", "RB1", "a"),
      w("VCC", "n", "GND1", "g"),
      w("RC", "b", "Q1", "c"),
      w("RB1", "b", "RB2", "a"),
      w("RB1", "b", "RIN", "b"),
      w("RB1", "b", "Q1", "b"),
      w("RB2", "b", "GND1", "g"),
      w("VIN", "p", "RIN", "a"),
      w("VIN", "n", "GND1", "g"),
      w("Q1", "e", "RE", "a"),
      w("RE", "b", "GND2", "g"),
      w("GND1", "g", "GND2", "g"),
    ],
    nextId: 100,
  };
}

function exampleOpamp() {
  const components = [
    makeComponent("vsource", 120, 360, { id: "VIN", dc: 0, amp: 1, freq: 1000, value: "1 V sine" }),
    makeComponent("vsource", 500, 135, { id: "VP", dc: 15, value: "+15 V" }),
    makeComponent("vsource", 500, 595, { id: "VM", dc: -15, value: "-15 V" }),
    makeComponent("resistor", 320, 385, { id: "RIN", value: "10k" }),
    makeComponent("resistor", 570, 250, { id: "RF", value: "100k" }),
    makeComponent("capacitor", 570, 465, { id: "CF", value: "1n" }),
    makeComponent("opamp", 720, 360, { id: "U1", value: "ideal", gain: 100000 }),
    makeComponent("ground", 120, 490, { id: "GND1" }),
    makeComponent("ground", 480, 690, { id: "GND2" }),
    makeComponent("ground", 630, 305, { id: "GND3" }),
  ];
  return {
    title: "Inverting op-amp low-pass amplifier",
    components,
    wires: [
      w("VIN", "p", "RIN", "a"),
      w("VIN", "n", "GND1", "g"),
      w("RIN", "b", "U1", "inm"),
      w("U1", "inp", "GND3", "g"),
      w("RF", "a", "U1", "inm"),
      w("RF", "b", "U1", "out"),
      w("CF", "a", "U1", "inm"),
      w("CF", "b", "U1", "out"),
      w("VP", "p", "U1", "vp"),
      w("VP", "n", "GND2", "g"),
      w("VM", "p", "U1", "vm"),
      w("VM", "n", "GND2", "g"),
      w("GND1", "g", "GND2", "g"),
      w("GND2", "g", "GND3", "g"),
    ],
    nextId: 100,
  };
}

function w(c1, p1, c2, p2) {
  return {
    a: { componentId: c1, pin: p1 },
    b: { componentId: c2, pin: p2 },
  };
}

const EXAMPLES = [
  { id: "rc", name: "RC low-pass", build: exampleRc },
  { id: "rectifier", name: "Diode rectifier", build: exampleRectifier },
  { id: "bjt", name: "BJT common-emitter", build: exampleCommonEmitter },
  { id: "opamp", name: "Op-amp low-pass", build: exampleOpamp },
];

function loadExample(id) {
  const example = EXAMPLES.find((e) => e.id === id) || EXAMPLES[0];
  state = clone(example.build());
  selectedId = null;
  wireStart = null;
  dragging = null;
  lastSim = null;
  selectedProbe = "";
  updateInspector();
  updateProbeList();
  drawSchematic();
  drawScope();
  setStatus(`${example.name} loaded.`);
}

canvas.addEventListener("mousedown", (evt) => {
  const p = canvasPoint(evt);
  if (PARTS[activeTool]) {
    addPart(activeTool, p.x, p.y);
    activeTool = "select";
    refreshToolButtons();
    return;
  }
  if (activeTool === "wire") {
    const hit = hitTestPin(p.x, p.y);
    if (!hit) return;
    if (!wireStart) {
      wireStart = hit;
      setStatus(`Wire started at ${hit.componentId}.${hit.pin}.`);
    } else {
      if (wireStart.componentId !== hit.componentId || wireStart.pin !== hit.pin) {
        state.wires.push({
          a: { componentId: wireStart.componentId, pin: wireStart.pin },
          b: { componentId: hit.componentId, pin: hit.pin },
        });
        setStatus(`Wire added to ${hit.componentId}.${hit.pin}.`);
      }
      wireStart = null;
      updateProbeList();
    }
    drawSchematic();
    return;
  }
  const comp = hitTestComponent(p.x, p.y);
  if (comp) {
    selectComponent(comp.id);
    dragging = { id: comp.id, dx: p.x - comp.x, dy: p.y - comp.y };
  } else {
    selectedId = null;
    updateInspector();
    drawSchematic();
  }
});

canvas.addEventListener("mousemove", (evt) => {
  if (!dragging) return;
  const p = canvasPoint(evt);
  const comp = getComponent(dragging.id);
  if (!comp) return;
  comp.x = snap(p.x - dragging.dx);
  comp.y = snap(p.y - dragging.dy);
  drawSchematic();
});

window.addEventListener("mouseup", () => {
  dragging = null;
});

window.addEventListener("keydown", (evt) => {
  if (evt.key === "Delete" || evt.key === "Backspace") {
    const tag = document.activeElement?.tagName?.toLowerCase();
    if (tag !== "input" && tag !== "textarea") deleteSelected();
  }
  if (evt.key === "Escape") {
    wireStart = null;
    activeTool = "select";
    refreshToolButtons();
    drawSchematic();
  }
});

document.getElementById("applyBtn").addEventListener("click", applyInspector);
document.getElementById("deleteBtn").addEventListener("click", deleteSelected);
document.getElementById("dcBtn").addEventListener("click", runDc);
document.getElementById("tranBtn").addEventListener("click", runTransient);
document.getElementById("saveBtn").addEventListener("click", saveLocal);
document.getElementById("restoreBtn").addEventListener("click", restoreLocal);
document.getElementById("exportBtn").addEventListener("click", exportJson);
document.getElementById("loadExampleBtn").addEventListener("click", () => {
  loadExample(document.getElementById("exampleSelect").value);
});
document.getElementById("probeSelect").addEventListener("change", (evt) => {
  selectedProbe = evt.target.value;
  drawScope();
});
document.getElementById("copyNetlistBtn").addEventListener("click", () => {
  const netlist = exportNetlist();
  document.getElementById("resultsText").value = netlist;
  navigator.clipboard?.writeText(netlist).catch(() => {});
  setStatus("Netlist written to Results and copied when clipboard is available.");
});

function init() {
  setupButtons();
  const select = document.getElementById("exampleSelect");
  for (const example of EXAMPLES) {
    const opt = document.createElement("option");
    opt.value = example.id;
    opt.textContent = example.name;
    select.appendChild(opt);
  }
  loadExample("rc");
}

window.AnalogSketchLab = {
  getState: () => clone(state),
  loadExample,
  runDc,
  runTransient,
  exportNetlist,
};

init();

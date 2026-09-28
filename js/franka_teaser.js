// Interactive teaser: a Franka Panda waits above a sponge and starts pressing it while the pointer is over the canvas.
// Robot: MuJoCo Menagerie franka_emika_panda (Apache-2.0), packed by tools/build_panda.py into assets/panda/.
// The pressing rhythm is the chirp reference used for data collection: z_r(t) = cos(2*pi*h1*(1 + cos(2*pi*h2*t)/20)*t).
import * as THREE from './vendor/three.module.min.js';

const H1 = 0.9, H2 = 0.127;                 // chirp parameters
const SPONGE = { x: 0.45, size: 0.26, height: 0.10 };
const STANDBY_CLEARANCE = 0.13;             // tool tip above the sponge while idle [m]
const DEPTH_MID = 0.024, DEPTH_AMP = 0.016; // press depth = MID - AMP * z_r  ->  8 .. 40 mm

export async function mountFrankaTeaser(el) {
  if (el.dataset.mounted) return;
  el.dataset.mounted = '1';
  const base = el.dataset.assets;
  const [meta, bin] = await Promise.all([
    fetch(base + 'panda.json').then(r => r.json()),
    fetch(base + 'panda.bin').then(r => r.arrayBuffer()),
  ]);

  const transparent = el.dataset.bg === 'transparent';       // robot stands directly on the page, no backdrop
  let renderer;
  try {
    renderer = new THREE.WebGLRenderer({ antialias: true, alpha: transparent, powerPreference: 'low-power' });
  } catch (e) {
    return;                                  // no WebGL: the fallback image stays
  }
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = THREE.PCFSoftShadowMap;
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 1.05;
  el.prepend(renderer.domElement);
  el.classList.add('sim-ready');

  const scene = new THREE.Scene();
  if (transparent) {
    renderer.setClearColor(0x000000, 0);
  } else {
    scene.background = new THREE.Color(0xe9ecf0);
    scene.fog = new THREE.Fog(0xe9ecf0, 3.2, 6.5);
  }

  const camera = new THREE.PerspectiveCamera(30, 16 / 9, 0.05, 20);
  // the transparent variant fades out at the canvas edges, so it keeps the scene a little smaller and higher
  const camTarget = new THREE.Vector3(0.28, transparent ? 0.26 : 0.31, 0);
  const camHome = { radius: transparent ? 1.86 : 1.72, azimuth: 0.72, elevation: 0.36 };

  scene.add(new THREE.HemisphereLight(0xffffff, 0xc9d1da, 1.15));
  const sun = new THREE.DirectionalLight(0xffffff, 2.6);
  sun.position.set(1.4, 2.6, 1.7);
  sun.castShadow = true;
  sun.shadow.mapSize.set(2048, 2048);
  Object.assign(sun.shadow.camera, { left: -1.1, right: 1.1, top: 1.3, bottom: -0.6, near: 0.5, far: 6 });
  sun.shadow.bias = -0.0004;
  sun.shadow.radius = 4;
  scene.add(sun);

  // MuJoCo is z-up, three.js is y-up
  const zup = new THREE.Group();
  zup.rotation.x = -Math.PI / 2;
  scene.add(zup);

  const floor = new THREE.Mesh(new THREE.PlaneGeometry(12, 12), new THREE.ShadowMaterial({ opacity: 0.2 }));
  floor.receiveShadow = true;
  zup.add(floor);

  // ------------------------------------------------------------------ robot
  const mats = {};
  for (const [name, rgb] of Object.entries(meta.materials)) {
    mats[name] = new THREE.MeshStandardMaterial({
      color: new THREE.Color().setRGB(rgb[0], rgb[1], rgb[2], THREE.SRGBColorSpace),
      roughness: name === 'dark_grey' ? 0.6 : 0.42,
      metalness: name === 'dark_grey' ? 0.15 : 0.0,
    });
  }
  const frames = {}, joints = [];
  for (const b of meta.bodies) {
    const frame = new THREE.Group();
    frame.position.fromArray(b.pos);
    frame.quaternion.set(b.quat[1], b.quat[2], b.quat[3], b.quat[0]);   // MuJoCo stores w first
    const link = new THREE.Group();                                     // rotates about local z
    frame.add(link);
    (b.parent ? frames[b.parent] : zup).add(frame);
    frames[b.name] = link;
    if (b.range) joints.push(link);
  }
  for (const m of meta.meshes) {
    const g = new THREE.BufferGeometry();
    g.setAttribute('position', new THREE.BufferAttribute(new Uint16Array(bin, m.pos, m.vertices * 3), 3, true));
    g.setAttribute('normal', new THREE.BufferAttribute(new Int8Array(bin, m.nrm, m.vertices * 3), 3, true));
    const Index = m.idx32 ? Uint32Array : Uint16Array;
    g.setIndex(new THREE.BufferAttribute(new Index(bin, m.idx, m.triangles * 3), 1));
    const mesh = new THREE.Mesh(g, mats[m.material]);
    mesh.position.fromArray(m.min);                                     // positions are quantized to the bbox
    mesh.scale.fromArray(m.span);
    mesh.castShadow = mesh.receiveShadow = true;
    frames[m.body].add(mesh);
  }

  // tool from the lab's MuJoCo model: a shaft with a ball tip on the flange
  const tool = meta.tool;
  const toolMat = new THREE.MeshStandardMaterial({ color: 0xaeb5bc, roughness: 0.35, metalness: 0.65 });
  const shaft = new THREE.Mesh(new THREE.CylinderGeometry(tool.shaftR, tool.shaftR, tool.shaftLen, 24), toolMat);
  shaft.rotation.x = Math.PI / 2;
  shaft.position.z = tool.attachZ + tool.shaftLen / 2;
  const ball = new THREE.Mesh(new THREE.SphereGeometry(tool.tipR, 32, 20), toolMat);
  ball.position.z = tool.attachZ + tool.shaftLen;
  for (const o of [shaft, ball]) { o.castShadow = true; frames.link7.add(o); }

  function setJoints(q) {
    for (let i = 0; i < joints.length; i++) joints[i].rotation.z = q[i];
  }
  // joint angles for a tool-tip height, from the baked IK table (uniform grid in z)
  const ik = meta.ik, z0 = ik.z[0], dz = ik.z[1] - ik.z[0], q = new Array(7);
  function solve(z) {
    const f = Math.min(Math.max((z - z0) / dz, 0), ik.z.length - 1.0001);
    const i = Math.floor(f), t = f - i, a = ik.q[i], b = ik.q[i + 1];
    for (let k = 0; k < 7; k++) q[k] = a[k] + (b[k] - a[k]) * t;
    return q;
  }

  // ------------------------------------------------------------------ sponge
  const SEG = 56;
  const spongeGeo = new THREE.BoxGeometry(SPONGE.size, SPONGE.size, SPONGE.height, SEG, SEG, 1);
  const spongeMat = new THREE.MeshStandardMaterial({ color: 0xf0d452, roughness: 1, metalness: 0, vertexColors: true });
  const pores = poreTexture();
  spongeMat.bumpMap = pores;
  spongeMat.bumpScale = 1.2;
  spongeMat.map = pores;
  const sponge = new THREE.Mesh(spongeGeo, spongeMat);
  sponge.position.set(SPONGE.x, 0, SPONGE.height / 2);
  sponge.castShadow = sponge.receiveShadow = true;
  zup.add(sponge);

  const sp = spongeGeo.attributes.position, top = [];
  for (let i = 0; i < sp.count; i++) if (sp.getZ(i) > SPONGE.height / 2 - 1e-6) top.push(i);
  const topR2 = top.map(i => sp.getX(i) ** 2 + sp.getY(i) ** 2);
  const shade = new THREE.BufferAttribute(new Float32Array(sp.count * 3).fill(1), 3);   // darkens the dent, cheap stand-in for AO
  spongeGeo.setAttribute('color', shade);
  let lastDepth = -1;
  function dent(depth) {                       // depth of the ball's lowest point below the rest surface
    depth = Math.max(depth, 0);
    if (Math.abs(depth - lastDepth) < 1e-5) return;
    lastDepth = depth;
    const R = tool.tipR, h = SPONGE.height / 2;
    const s2 = Math.max(0.03, Math.sqrt(2 * R * depth) * 1.2) ** 2;
    for (let k = 0; k < top.length; k++) {
      const r2 = topR2[k];
      let z = h - depth * Math.exp(-r2 / s2);
      if (r2 < R * R) z = Math.min(z, h - depth + R - Math.sqrt(R * R - r2));   // never poke through the ball
      sp.setZ(top[k], z);
      const c = 1 - 0.45 * Math.min((h - z) / 0.04, 1);
      shade.setXYZ(top[k], c, c, c);
    }
    sp.needsUpdate = shade.needsUpdate = true;
    spongeGeo.computeVertexNormals();
  }

  // ------------------------------------------------------------------ interaction
  const hud = el.querySelector('.sim-state'), hint = el.querySelector('.sim-hint');
  const pointer = { x: 0, y: 0 }, look = { x: 0, y: 0 };
  let hovered = false;
  const setHover = v => {
    hovered = v;
    el.classList.toggle('sim-running', v);
    if (hud) hud.textContent = v ? 'Pressing · chirp reference' : 'Standby';
  };
  el.addEventListener('pointerenter', e => { if (e.pointerType !== 'touch') setHover(true); });
  el.addEventListener('pointerleave', e => { if (e.pointerType !== 'touch') { setHover(false); pointer.x = pointer.y = 0; } });
  el.addEventListener('pointermove', e => {
    const r = el.getBoundingClientRect();
    pointer.x = ((e.clientX - r.left) / r.width) * 2 - 1;
    pointer.y = ((e.clientY - r.top) / r.height) * 2 - 1;
  });
  const tapToggles = el.dataset.touch !== 'link';            // on the homepage the thumbnail is a link: taps navigate
  if (tapToggles) el.addEventListener('pointerup', e => { if (e.pointerType === 'touch') setHover(!hovered); });
  if (hint && matchMedia('(hover: none)').matches) hint.textContent = tapToggles ? 'Tap to start' : '';

  function resize() {
    const w = el.clientWidth, h = el.clientHeight;
    if (!w || !h) return;
    renderer.setSize(w, h, false);
    camera.aspect = w / h;
    camera.updateProjectionMatrix();
  }
  new ResizeObserver(resize).observe(el);
  resize();

  // ------------------------------------------------------------------ loop
  const zTop = SPONGE.height, zIdle = zTop + STANDBY_CLEARANCE;
  let engage = 0, tPress = 0, tAll = 0, last = performance.now(), visible = true, raf = 0;
  function frame(now) {
    raf = 0;
    const dt = Math.min((now - last) / 1000, 0.05);
    last = now;
    tAll += dt;

    engage += ((hovered ? 1 : 0) - engage) * (1 - Math.exp(-dt / 0.28));
    const e = engage * engage * (3 - 2 * engage);
    if (hovered && engage > 0.6) tPress += dt;          // start the chirp once the tip has reached the sponge
    else if (!hovered && engage < 0.02) tPress = 0;

    const zr = Math.cos(2 * Math.PI * H1 * (1 + Math.cos(2 * Math.PI * H2 * tPress) / 20) * tPress);
    const zPress = zTop - (DEPTH_MID - DEPTH_AMP * zr);
    const zStandby = zIdle + 0.004 * Math.sin(2 * Math.PI * 0.22 * tAll);   // idle breathing
    const zTip = zStandby + (zPress - zStandby) * e;
    setJoints(solve(zTip));
    dent(zTop - zTip);

    look.x += (pointer.x - look.x) * (1 - Math.exp(-dt / 0.35));
    look.y += (pointer.y - look.y) * (1 - Math.exp(-dt / 0.35));
    const az = camHome.azimuth - look.x * 0.16, elv = camHome.elevation + look.y * 0.07;
    camera.position.set(
      camTarget.x + camHome.radius * Math.cos(elv) * Math.sin(az),
      camTarget.y + camHome.radius * Math.sin(elv),
      camTarget.z + camHome.radius * Math.cos(elv) * Math.cos(az));
    camera.lookAt(camTarget);

    renderer.render(scene, camera);
    if (visible && !document.hidden) raf = requestAnimationFrame(frame);
  }
  const wake = () => { if (!raf && visible && !document.hidden) { last = performance.now(); raf = requestAnimationFrame(frame); } };
  new IntersectionObserver(es => { visible = es[0].isIntersecting; wake(); }, { rootMargin: '100px' }).observe(el);
  document.addEventListener('visibilitychange', wake);
  wake();

  el.__sim = { setHover, state: () => ({ hovered, engage, tPress, depth: lastDepth, q: [...q] }) };   // for debugging
}

// speckled grey-scale texture: used as colour modulation and bump map so the block reads as foam
function poreTexture() {
  const c = document.createElement('canvas');
  c.width = c.height = 256;
  const g = c.getContext('2d');
  g.fillStyle = '#fff';
  g.fillRect(0, 0, 256, 256);
  let s = 12345;
  const rnd = () => (s = (s * 1664525 + 1013904223) >>> 0) / 4294967296;
  for (let i = 0; i < 2600; i++) {
    const r = 0.6 + rnd() * 2.2, v = 165 + Math.floor(rnd() * 60);
    g.fillStyle = `rgb(${v},${v},${v})`;
    g.beginPath();
    g.arc(rnd() * 256, rnd() * 256, r, 0, 6.2832);
    g.fill();
  }
  const t = new THREE.CanvasTexture(c);
  t.wrapS = t.wrapT = THREE.RepeatWrapping;
  t.repeat.set(3, 3);
  t.colorSpace = THREE.SRGBColorSpace;
  return t;
}

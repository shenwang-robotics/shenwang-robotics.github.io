#!/usr/bin/env python3
"""Pack the MuJoCo Menagerie Franka Panda into a small web asset.

Reads panda_nohand.xml + assets/*.obj (Apache-2.0, DeepMind / Franka Robotics), decimates the visual
meshes by vertex clustering, merges them per (body, material), recomputes crease-aware normals and
writes  assets/panda/panda.bin + panda.json.  Also bakes an IK table (tool tip height -> joint angles)
for a vertical press at a fixed x, so the page needs no IK solver.

usage: python3 tools/build_panda.py /path/to/franka_panda  [cell_mm]
"""
import json, math, struct, sys
import xml.etree.ElementTree as ET
from pathlib import Path
import numpy as np

SRC = Path(sys.argv[1])
CELL = float(sys.argv[2]) / 1000 if len(sys.argv) > 2 else 0.004
OUT = Path(__file__).resolve().parent.parent / "assets" / "panda"
CREASE_COS = math.cos(math.radians(40))

# tool defined in the lab's panda_nohand.xml: shaft capsule r=12 mm, 50 mm long, ball tip r=20 mm
ATTACH_Z, SHAFT_LEN, SHAFT_R, TIP_R = 0.107, 0.05, 0.012, 0.02
TIP_OFFSET = ATTACH_Z + SHAFT_LEN + TIP_R          # link7 origin -> lowest point of the ball

root = ET.parse(SRC / "panda_nohand.xml").getroot()
materials = {m.get("name"): [float(x) for x in m.get("rgba").split()[:3]]
             for m in root.find("asset").findall("material")}

def load_obj(path):
    vs, fs = [], []
    for line in open(path):
        if line.startswith("v "):
            vs.append([float(x) for x in line.split()[1:4]])
        elif line.startswith("f "):
            idx = [int(t.split("/")[0]) - 1 for t in line.split()[1:]]
            for k in range(1, len(idx) - 1):
                fs.append([idx[0], idx[k], idx[k + 1]])
    return np.array(vs, dtype=np.float64), np.array(fs, dtype=np.int64)

def cluster(v, f, cell):
    key = np.floor(v / cell).astype(np.int64)
    _, inv = np.unique(key, axis=0, return_inverse=True)
    inv = inv.ravel()
    n = inv.max() + 1
    cnt = np.bincount(inv, minlength=n).astype(np.float64)
    nv = np.stack([np.bincount(inv, weights=v[:, k], minlength=n) / cnt for k in range(3)], axis=1)
    nf = inv[f]
    ok = (nf[:, 0] != nf[:, 1]) & (nf[:, 1] != nf[:, 2]) & (nf[:, 0] != nf[:, 2])
    nf = nf[ok]
    # drop duplicate triangles (same vertex set)
    _, first = np.unique(np.sort(nf, axis=1), axis=0, return_index=True)
    return nv, nf[np.sort(first)]

def crease_normals(v, f):
    """Return (positions, normals, faces) with vertices split where faces meet at > 40 deg."""
    raw = np.cross(v[f[:, 1]] - v[f[:, 0]], v[f[:, 2]] - v[f[:, 0]])
    area = np.linalg.norm(raw, axis=1)
    keep = area > 1e-14
    f, raw, area = f[keep], raw[keep], area[keep]
    unit = raw / area[:, None]
    adj = [[] for _ in range(len(v))]
    for fi, tri in enumerate(f):
        for vi in tri:
            adj[vi].append(fi)
    out_p, out_n, remap, out_f = [], [], {}, np.empty_like(f)
    for fi, tri in enumerate(f):
        for k, vi in enumerate(tri):
            fa = adj[vi]
            m = unit[fa] @ unit[fi] > CREASE_COS
            nrm = raw[fa][m].sum(axis=0)
            nrm /= np.linalg.norm(nrm) + 1e-20
            q = tuple(np.round(nrm * 127).astype(int))
            key = (vi, q)
            if key not in remap:
                remap[key] = len(out_p)
                out_p.append(v[vi]); out_n.append(q)
            out_f[fi, k] = remap[key]
    return np.array(out_p), np.array(out_n, dtype=np.int8), out_f

# ---------------------------------------------------------------- kinematic tree + geometry
bodies, groups = [], {}
def walk(el, parent):
    name = el.get("name")
    if not name.startswith("link"):
        return
    pos = [float(x) for x in el.get("pos", "0 0 0").split()]
    quat = np.array([float(x) for x in el.get("quat", "1 0 0 0").split()])
    quat = (quat / np.linalg.norm(quat)).tolist()            # w x y z
    j = el.find("joint")
    rng = None
    if j is not None:
        rng = [float(x) for x in j.get("range", "-2.8973 2.8973").split()]
    bodies.append({"name": name, "parent": parent, "pos": pos, "quat": quat, "range": rng})
    for g in el.findall("geom"):
        if g.get("class") == "panda/visual":
            groups.setdefault((name, g.get("material")), []).append(g.get("mesh"))
    for child in el.findall("body"):
        walk(child, name)
walk(root.find("worldbody").find("body"), None)

blob, meshes, tot_in, tot_out = bytearray(), [], 0, 0
def push(arr):
    while len(blob) % 4:
        blob.append(0)
    off = len(blob)
    blob.extend(arr.tobytes())
    return off

for (body, mat), names in groups.items():
    vs, fs, base = [], [], 0
    for n in names:
        v, f = load_obj(SRC / "assets" / f"{n}.obj")
        vs.append(v); fs.append(f + base); base += len(v)
    v, f = np.concatenate(vs), np.concatenate(fs)
    tot_in += len(f)
    if len(f) > 1500:                                          # small parts (markings, screws) stay as they are
        v, f = cluster(v, f, CELL)
    else:
        v, f = cluster(v, f, 1e-5)                             # weld only
    p, nrm, f = crease_normals(v, f)
    tot_out += len(f)
    lo, hi = p.min(axis=0), p.max(axis=0)
    span = np.where(hi - lo > 1e-9, hi - lo, 1.0)
    q = np.round((p - lo) / span * 65535).astype(np.uint16)
    big = len(p) > 65535
    meshes.append({
        "body": body, "material": mat, "vertices": int(len(p)), "triangles": int(len(f)),
        "min": lo.tolist(), "span": span.tolist(),
        "pos": push(q), "nrm": push(nrm), "idx": push(f.astype(np.uint32 if big else np.uint16).ravel()),
        "idx32": bool(big),
    })

# ---------------------------------------------------------------- IK table for a vertical press
def rotz(a):
    c, s = math.cos(a), math.sin(a)
    return np.array([[c, -s, 0, 0], [s, c, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1.0]])
def frame(pos, quat):
    w, x, y, z = quat
    R = np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
                  [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
                  [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]])
    T = np.eye(4); T[:3, :3] = R; T[:3, 3] = pos
    return T
chain = [b for b in bodies if b["range"] is not None]
def fk(q):
    T = frame(bodies[0]["pos"], bodies[0]["quat"])
    for b, a in zip(chain, q):
        T = T @ frame(b["pos"], b["quat"]) @ rotz(a)
    tip = T @ np.array([0, 0, TIP_OFFSET, 1.0])
    return tip[:3], T[:3, 2]                                   # tip point, tool axis

HOME = [0, 0, 0, -1.57079, 0, 1.57079, -0.7853]
def solve(x, z, seed):
    q = np.array(seed, dtype=float)
    free = [1, 3, 5]                                           # motion stays in the x-z plane
    def err(qq):
        p, a = fk(qq)
        return np.array([p[0] - x, p[2] - z, a[0]])            # a[0]=0 with a[2]<0  <=>  tool points down
    for _ in range(60):
        e = err(q)
        if np.abs(e).max() < 1e-9:
            break
        J = np.zeros((3, 3))
        for c, j in enumerate(free):
            d = q.copy(); d[j] += 1e-6
            J[:, c] = (err(d) - e) / 1e-6
        q[free] -= np.linalg.solve(J, e)
    p, a = fk(q)
    assert np.abs(err(q)).max() < 1e-6 and a[2] < -0.999 and abs(p[1]) < 1e-9, (x, z, err(q))
    for b, a_ in zip(chain, q):
        assert b["range"][0] <= a_ <= b["range"][1], ("joint limit", b["name"], a_)
    return q

PRESS_X = 0.45
zs = [round(0.02 + 0.005 * k, 4) for k in range(0, 75)]        # tip height 0.02 .. 0.39 m
seed = HOME
order = sorted(range(len(zs)), key=lambda i: -zs[i])
sol = {}
for i in order:
    seed = solve(PRESS_X, zs[i], seed)
    sol[i] = seed.copy()
ik = {"x": PRESS_X, "z": zs, "q": [[round(float(a), 5) for a in sol[i]] for i in range(len(zs))]}

while len(blob) % 4:
    blob.append(0)
OUT.mkdir(parents=True, exist_ok=True)
(OUT / "panda.bin").write_bytes(blob)
(OUT / "panda.json").write_text(json.dumps({
    "source": "MuJoCo Menagerie franka_emika_panda (Apache-2.0), decimated by vertex clustering",
    "cell": CELL, "materials": materials, "bodies": bodies, "meshes": meshes,
    "tool": {"attachZ": ATTACH_Z, "shaftLen": SHAFT_LEN, "shaftR": SHAFT_R, "tipR": TIP_R},
    "home": HOME, "ik": ik,
}, separators=(",", ":")))
print(f"triangles {tot_in} -> {tot_out};  draw groups {len(meshes)};  bin {len(blob)/1e6:.2f} MB")
print("tip at home:", fk(HOME)[0].round(4), " q(z=0.10):", np.round(sol[zs.index(0.1)], 3))

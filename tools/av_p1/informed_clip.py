"""Draw the homepage Informed RRT* clip from informed_frames.mat (written by informed_frames.m).

    python3 tools/av_p1/informed_clip.py      (make.sh runs it)

Every frame shows the planner's exact state at that iteration: the tree with its current
parents, the best path so far (dashed: the straight step from the accepting node into the goal),
the ellipse the next samples are drawn from, and the most recent samples.
Writes images/av_projects/p1_informed.mp4 and p1_informed_poster.jpg.
"""
import subprocess
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.collections import LineCollection
from matplotlib.patches import Polygon
from scipy.io import loadmat

HERE = Path(__file__).resolve().parent
OUT = HERE.parents[1] / "images" / "av_projects"
SIZE, FPS = 720, 20
WINDOW = 300                      # recent samples shown
HOLD_FIRST, HOLD_END = 14, 40     # extra frames on the first path and on the final state
POSTER_ITER = 8000

FREE, OBST = (1.0, 1.0, 1.0), (0.37, 0.40, 0.43)
TREE, SAMPLE, ELLIPSE = "#8796a5", "#e08a00", "#7b3fa0"
START, GOAL, INK = "#1b9e77", "#d52929", "#222222"

m = loadmat(HERE / "informed_frames.mat", squeeze_me=True, struct_as_record=False)
frames = np.atleast_1d(m["frames"])
nodes, samples = m["nodes"], m["samples"]
c_min, C, centre = float(m["c_min"]), m["ellipse_C"], m["ellipse_centre"]
start, goal, free = m["start_xy"], m["goal_xy"], m["free"].astype(bool)
n = free.shape[0]

fig = plt.figure(figsize=(SIZE / 100, SIZE / 100), dpi=100, facecolor="white")
side = 0.85
ax = fig.add_axes([(1 - side) / 2, 0.02, side, side])
img = np.where(free[..., None], FREE, OBST)
ax.imshow(img, extent=(0.5, n + 0.5, n + 0.5, 0.5), interpolation="nearest", zorder=0)
ax.set_xlim(0.5, n + 0.5); ax.set_ylim(n + 0.5, 0.5)
ax.set_xticks([]); ax.set_yticks([])
for s in ax.spines.values():
    s.set_color("#999999")

tree = LineCollection([], colors=TREE, linewidths=0.55, alpha=0.6, zorder=1)
ax.add_collection(tree)
ell_fill = Polygon(np.zeros((1, 2)), closed=True, facecolor=ELLIPSE, alpha=0.07, edgecolor="none", zorder=2)
ell_edge, = ax.plot([], [], color=ELLIPSE, lw=2.2, zorder=5)
ax.add_patch(ell_fill)
recent = ax.scatter([], [], s=18, linewidths=0, zorder=3)
path, = ax.plot([], [], color="black", lw=2.6, zorder=6, solid_capstyle="round")
step, = ax.plot([], [], color="black", lw=2.0, ls=(0, (3, 2)), zorder=6)
ax.plot(*start, "o", ms=11, mfc=START, mec="black", mew=1, zorder=7)
ax.plot(*goal, "s", ms=11, mfc=GOAL, mec="black", mew=1, zorder=7)

line1 = fig.text(0.5, 0.945, "", ha="center", va="center", fontsize=17, fontweight="bold", color=INK)
line2 = fig.text(0.5, 0.897, "", ha="center", va="center", fontsize=15, color=INK)

th = np.linspace(0, 2 * np.pi, 241)
fade = np.linspace(0.35, 1.0, WINDOW)
rgb = np.array(matplotlib.colors.to_rgb(SAMPLE))


def draw(f):
    k, nn = int(f.iter), int(f.n_nodes)
    par = np.atleast_1d(f.parent).astype(int)
    child = np.flatnonzero(par > 0)
    seg = np.stack([nodes[:, child].T, nodes[:, par[child] - 1].T], axis=1)
    tree.set_segments(seg)

    lo = max(0, k - WINDOW)
    pts = samples[:, lo:k].T
    recent.set_offsets(pts if len(pts) else np.zeros((0, 2)))
    colours = np.column_stack([np.tile(rgb, (len(pts), 1)), fade[WINDOW - len(pts):]])
    recent.set_facecolors(colours)

    cb = float(f.c_best)
    if np.isfinite(cb):
        a, b = cb / 2, np.sqrt(max(cb ** 2 - c_min ** 2, 0)) / 2
        e = (C @ np.vstack([a * np.cos(th), b * np.sin(th)])).T + centre
        ell_edge.set_data(e[:, 0], e[:, 1]); ell_fill.set_xy(e); ell_fill.set_visible(True)
        p = np.atleast_2d(f.path_xy)
        path.set_data(p[:, 0], p[:, 1])
        step.set_data([p[-1, 0], goal[0]], [p[-1, 1], goal[1]])
        line1.set_text("Path found: samples now come only from the ellipse")
        line2.set_text(f"iteration {k:,}  ·  path length {cb:.1f}  ·  straight line {c_min:.1f}")
    else:
        ell_edge.set_data([], []); ell_fill.set_visible(False)
        path.set_data([], []); step.set_data([], [])
        line1.set_text("No path yet: samples come from the whole map")
        line2.set_text(f"iteration {k:,}")
    fig.canvas.draw()
    return np.asarray(fig.canvas.buffer_rgba())[..., :3].copy()


first = next(i for i, f in enumerate(frames) if np.isfinite(float(f.c_best)))
order = []
for i in range(len(frames)):
    order += [i] * (1 + (HOLD_FIRST if i == first else 0) + (HOLD_END if i == len(frames) - 1 else 0))
poster = min(range(len(frames)), key=lambda i: abs(int(frames[i].iter) - POSTER_ITER))

OUT.mkdir(parents=True, exist_ok=True)
enc = subprocess.Popen(
    ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{SIZE}x{SIZE}",
     "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-crf", "26", "-preset", "slow",
     "-pix_fmt", "yuv420p", "-movflags", "+faststart", "-an", str(OUT / "p1_informed.mp4")],
    stdin=subprocess.PIPE)
cache = {}
for i in order:
    if i not in cache:
        cache = {i: draw(frames[i])}
        if i == poster:
            plt.imsave(OUT / "p1_informed_poster.jpg", cache[i], pil_kwargs={"quality": 88})
    enc.stdin.write(cache[i].tobytes())
enc.stdin.close()
assert enc.wait() == 0
print(f"{len(order)} frames ({len(order) / FPS:.1f} s), first path at frame {first}, "
      f"poster at iteration {int(frames[poster].iter)}")

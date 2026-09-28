# assets/panda

Franka Panda visual model for the interactive teaser (`js/franka_teaser.js`).

- Source: MuJoCo Menagerie `franka_emika_panda` (© DeepMind Technologies Limited, Apache License 2.0 — see `LICENSE`;
  robot design © Franka Robotics).
- **Modified**: visual meshes decimated by 4 mm vertex clustering (126 562 → 62 421 triangles), merged per body/material,
  positions quantized to 16 bit, normals recomputed; packed into `panda.bin` + `panda.json` by `tools/build_panda.py`.
- `panda.json` also holds the kinematic tree, the tool geometry (shaft + ball tip, as in the lab's `panda_nohand.xml`)
  and a baked IK table: tool-tip height → joint angles for a vertical press at x = 0.45 m.

Rebuild:

    python3 tools/build_panda.py /path/to/mujoco_models/franka_panda 4

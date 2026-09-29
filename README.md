# homepage

Personal academic homepage of Shen Wang. Plain static site: HTML + one stylesheet + a little JavaScript, no framework
and no build step. Layout adapted from the [Jon Barron](https://jonbarron.info/) /
[Deepak Pathak](https://www.cs.cmu.edu/~dpathak/) academic template, rebuilt with flexbox so it works on phones.

## Layout

```
index.html            home: bio, news, project rows, education, honors
projects/<id>/        one detail page per project (index.html); the home row's title and thumbnail link here
css/style.css         all styles
js/site.js            show/hide toggles, e-mail assembly, lazy video playback (on screen or on hover), lazy mount of the 3D teaser,
                      time-on-page event and owner opt-out for the analytics
js/franka_teaser.js   interactive three.js teaser: a Franka Panda presses a sponge while the pointer hovers
js/vendor/            three.js r180 (MIT), vendored so the site runs offline
assets/panda/         decimated Franka Panda model + baked IK table (see assets/panda/README.md)
tools/build_panda.py  regenerates assets/panda/ from the MuJoCo Menagerie model
images/               photos, figures and clips, one sub-folder per project
data/                 PDFs (CV, reports)
.nojekyll             tells GitHub Pages not to run Jekyll
robots.txt            asks AI-training crawlers not to crawl; search engines and AI search stay allowed
```

## Preview locally

```bash
python3 -m http.server 8137
```

Then open <http://localhost:8137>. A server is needed (not `file://`) because the teaser loads ES modules and binary assets.

## Add a project

1. In `index.html`, copy the commented *template B* block in the Projects section and paste it at the top (newest first).
2. Replace every `PROJECTID` with a short id, e.g. `dl_lab`.
3. Copy `projects/dl_lab/` to `projects/<id>/` and edit its `index.html`. The home row keeps only the title, people,
   course line, a one-sentence summary and links.
4. Put the looping clip at `images/<id>/teaser.mp4`; without a clip, use an `<img>` instead of the `<video>`.
   `data-autoplay` plays it while on screen; `data-hover` plays it only while the pointer is over the thumbnail and
   shows the poster otherwise (touch screens fall back to on-screen playback).

Clips should be 10–20 s, 1–2 MB, no audio:

```bash
ffmpeg -i input.mp4 -ss 00:00:05 -t 15 -vf "scale=-2:480,fps=24" -c:v libx264 -crf 28 -preset slow -pix_fmt yuv420p -movflags +faststart -an images/<id>/teaser.mp4
```

After editing `css/style.css` or `js/site.js`, bump the `?v=…` query on their `<link>` / `<script>` tags in every HTML
file, otherwise browsers keep serving the cached copy.

## Interactive teaser

- Idle: the tool tip hovers about 13 cm above the sponge. Pointer over the canvas (tap on touch screens): the arm comes
  down and presses with the chirp reference `z_r(t) = cos(2π·h1·(1 + cos(2π·h2·t)/20)·t)`; pointer out: back to idle.
- It is an illustration, not a physics simulation: joint angles come from an IK table baked offline, and the dent in
  the sponge is a Gaussian deformation of the top surface.
- Mount it anywhere with `<div class="sim" data-assets="<path>/assets/panda/">`; `js/site.js` fetches three.js and the
  model only when the element nears the viewport. Add `class="sim-transparent" data-bg="transparent"` for the version
  without a backdrop. On an `<a>` element, `data-touch="link"` makes taps follow the link instead of toggling.
- Tunables (press depth, idle height, camera) are the constants at the top of `js/franka_teaser.js`.
- Rendering pauses while the element is off screen or the tab is hidden; without WebGL the fallback `<img>` stays.

## Analytics

[Umami Cloud](https://umami.is/) (cookieless). The tag sits in every page's `<head>`; `data-domains` limits it to the live
site, so local previews are not counted. `js/site.js` sends a `time-on-page` event (visible time only) when a visitor
leaves a page, and the CV link carries `data-umami-event="cv-click"`. Open any page once with `?notrack` to stop
counting your own visits in that browser; `?track` undoes it.

## Third-party material

- Franka Panda model: [MuJoCo Menagerie](https://github.com/google-deepmind/mujoco_menagerie) `franka_emika_panda`,
  Apache-2.0, modified (decimated and repacked) — see `assets/panda/`.
- [three.js](https://threejs.org/) r180, MIT — see `js/vendor/three.LICENSE`.
- Typeface: Titillium Web via Google Fonts.

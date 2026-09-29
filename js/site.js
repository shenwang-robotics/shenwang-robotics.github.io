// Analytics opt-out for the owner: open any page once with ?notrack to stop counting this browser (?track undoes it).
// This file runs before the deferred Umami script, which sends nothing while umami.disabled is set.
(function () {
  try {
    var q = new URLSearchParams(location.search);
    if (q.has('notrack')) localStorage.setItem('umami.disabled', '1');
    if (q.has('track')) localStorage.removeItem('umami.disabled');
  } catch (e) {} // storage blocked: nothing to switch
})();

// Show/hide blocks: any element with data-toggle="<id>" flips the `hidden` attribute of #<id>.
// Used for "details" and "bibtex" links in project rows and "show more" in News.
document.addEventListener('click', function (e) {
  var t = e.target.closest('[data-toggle]');
  if (!t) return;
  e.preventDefault();
  var block = document.getElementById(t.dataset.toggle);
  if (block) block.hidden = !block.hidden;
});

// Email is assembled at runtime so the full address never sits in the HTML for scrapers.
// <a class="email" data-user="name" data-domain="example.com">Email</a>
// Add data-show to also replace the text with "name [AT] example.com".
document.querySelectorAll('.email').forEach(function (el) {
  var user = el.dataset.user, domain = el.dataset.domain;
  if (!user || !domain) return;
  if (el.tagName === 'A') el.href = 'mailto:' + user + '@' + domain;
  if ('show' in el.dataset) el.textContent = user + ' [AT] ' + domain;
});

// Project videos: <video data-autoplay data-src="images/x/teaser.mp4" ...>
// Load + play only while on screen, so 20 clips don't all download and decode at once.
// <video data-hover ...> instead plays only while the pointer is over its .project-media box and shows the poster
// otherwise; it is still fetched when near the viewport so the hover starts at once. Touch screens have no hover,
// so there it behaves like data-autoplay.
(function () {
  var canHover = !!(window.matchMedia && matchMedia('(hover: hover)').matches);
  var videos = document.querySelectorAll('video[data-autoplay], video[data-hover]');
  function onHover(v) { return canHover && 'hover' in v.dataset; }
  function load(v) {
    if (!v.getAttribute('src') && v.dataset.src) v.src = v.dataset.src;
  }
  function start(v) {
    load(v);
    var p = v.play();
    if (p && p.catch) p.catch(function () {});
  }
  function near(v) {
    if (!onHover(v)) return start(v);
    v.preload = 'auto';
    load(v);
  }
  videos.forEach(function (v) {
    if (!onHover(v)) return;
    var box = v.closest('.project-media') || v;
    box.addEventListener('mouseenter', function () { start(v); });
    box.addEventListener('mouseleave', function () { v.pause(); v.load(); }); // load() brings the poster back
  });
  if (!('IntersectionObserver' in window)) {
    videos.forEach(near);
    return;
  }
  var io = new IntersectionObserver(function (entries) {
    entries.forEach(function (en) {
      if (en.isIntersecting) near(en.target);
      else en.target.pause();
    });
  }, { rootMargin: '200px' });
  videos.forEach(function (v) { io.observe(v); });
})();

// Interactive Franka teaser: <div class="sim" data-assets="assets/panda/">. The three.js module (~1.5 MB with the
// model) is only fetched once the element is near the viewport.
document.querySelectorAll('.sim[data-assets]').forEach(function (el) {
  if (!('IntersectionObserver' in window)) return;
  var io = new IntersectionObserver(function (entries) {
    if (!entries[0].isIntersecting) return;
    io.disconnect();
    import('./franka_teaser.js').then(function (m) { return m.mountFrankaTeaser(el); }).catch(function (e) { console.error('franka teaser:', e); });
  }, { rootMargin: '300px' });
  io.observe(el);
});

// Time on page for the analytics. Umami gives a one-page visit a duration of 0, so count the time the tab is
// actually visible and send one "time-on-page" event when the visitor leaves (close, reload, link, back).
(function () {
  var visible = 0, since = document.visibilityState === 'visible' ? Date.now() : null;
  function pause() {
    if (since !== null) { visible += Date.now() - since; since = null; }
  }
  function range(s) {
    return s < 10 ? '0-10 s' : s < 30 ? '10-30 s' : s < 60 ? '30-60 s'
      : s < 180 ? '1-3 min' : s < 600 ? '3-10 min' : '10+ min';
  }
  document.addEventListener('visibilitychange', function () {
    if (document.visibilityState === 'hidden') pause();
    else if (since === null) since = Date.now();
  });
  window.addEventListener('pagehide', function () {
    pause();
    var s = Math.round(visible / 1000);
    visible = 0;
    if (s < 1 || !window.umami || typeof window.umami.track !== 'function') return;
    window.umami.track('time-on-page', { page: location.pathname, seconds: s, range: range(s) });
  });
  // Back/forward cache can show the same page again after pagehide: start a fresh count.
  window.addEventListener('pageshow', function (e) {
    if (e.persisted) since = document.visibilityState === 'visible' ? Date.now() : null;
  });
})();

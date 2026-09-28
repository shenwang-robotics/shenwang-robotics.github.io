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

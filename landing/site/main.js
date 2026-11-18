(function () {
  'use strict';

  var calm = document.documentElement.classList.contains('calm');
  var $ = function (id) { return document.getElementById(id); };
  var clamp = function (v) { return Math.min(1, Math.max(0, v)); };
  var seg = function (p, a, b) { return clamp((p - a) / (b - a)); };
  var smooth = function (t) { return t * t * (3 - 2 * t); };
  var money = function (v) { return '₹' + v.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 }); };

  /* ---------- Demo dialog works in every mode ---------- */

  var dialog = $('filmDialog'), video = $('filmVideo');
  document.querySelectorAll('[data-film-open]').forEach(function (b) {
    b.addEventListener('click', function () {
      dialog.showModal();
      video.play().catch(function () { /* controls remain available */ });
    });
  });
  $('filmClose').addEventListener('click', function () { dialog.close(); });
  dialog.addEventListener('click', function (e) { if (e.target === dialog) dialog.close(); });
  dialog.addEventListener('close', function () { video.pause(); });

  /* ---------- Read-along words ---------- */

  var lit = $('lit');
  var hot = { your: 1, 'catalog.': 1 };
  lit.innerHTML = lit.textContent.split(' ').map(function (w) {
    return '<span' + (hot[w] ? ' class="hot"' : '') + '>' + w + '</span>';
  }).join(' ');
  var litWords = lit.querySelectorAll('span');

  if (calm) { litWords.forEach(function (w) { w.classList.add('on'); }); return; }

  /* ---------- Writes only when a value changes, so idle frames cost nothing ---------- */

  function setStyle(el, prop, value) {
    var key = '_s' + prop;
    if (el[key] !== value) { el[key] = value; el.style[prop] = value; }
  }
  function setText(el, value) {
    if (el._text !== value) { el._text = value; el.textContent = value; }
  }

  /* ---------- Frame sequences ----------
     Compressed frames download coarse to fine and stay in memory as small blobs.
     A short window around the current frame is decoded off the main thread ahead of time,
     so drawing never stalls scrolling. Decoded frames are large, so only that window is kept. */

  var COUNTS = { a: 230, b: 105 };
  var SETS = {
    hd: { size: [2560, 1440], keep: 14 },
    wide: { size: [1920, 1080], keep: 20 },
    phone: { size: [1080, 1200], keep: 24 }
  };
  var LOOK_AHEAD = 8, MAX_DECODES = 3, DOWNLOADS = 6;
  var narrowMedia = matchMedia('(max-aspect-ratio: 3/2)');

  function chooseSet() {
    if (narrowMedia.matches) return 'phone';
    var coveredWidth = Math.max(innerWidth, innerHeight * 16 / 9) * (devicePixelRatio || 1);
    return coveredWidth > 2000 ? 'hd' : 'wide';
  }

  function Sequence(canvas) {
    this.canvas = canvas;
    this.ctx = canvas.getContext('2d', { alpha: false });
    this.name = canvas.dataset.seq;
    this.count = COUNTS[this.name];
    this.want = 0;
    this.direction = 1;
    this.begun = false;
    this.bitmaps = new Map();
    this.decoding = new Set();
    this.reset();
  }
  Sequence.prototype.reset = function () {
    this.bitmaps.forEach(function (b) { b.close(); });
    this.bitmaps.clear();
    this.decoding.clear();
    this.set = chooseSet();
    var size = SETS[this.set].size;
    this.canvas.width = size[0];
    this.canvas.height = size[1];
    this.blobs = new Array(this.count);
    this.drawn = -1;
    this.generation = (this.generation || 0) + 1;
    this.canvas.classList.remove('ready');
    if (this.begun) { this.begun = false; this.begin(); }
  };
  Sequence.prototype.url = function (i) {
    return 'assets/frames/' + this.set + '-' + this.name + '/f' + String(i + 1).padStart(3, '0') + '.webp';
  };
  Sequence.prototype.seek = function (i) {
    if (i !== this.want) this.direction = i > this.want ? 1 : -1;
    this.want = i;
    this.prepare();
    this.draw();
  };
  Sequence.prototype.draw = function () {
    for (var d = 0; d < this.count; d++) {
      var behind = this.want - this.direction * d, ahead = this.want + this.direction * d;
      var i = this.bitmaps.has(behind) ? behind : (this.bitmaps.has(ahead) ? ahead : -1);
      if (i < 0) continue;
      if (i !== this.drawn) {
        this.ctx.drawImage(this.bitmaps.get(i), 0, 0);
        this.drawn = i;
        this.canvas.classList.add('ready');
      }
      return;
    }
  };
  Sequence.prototype.prepare = function () {
    for (var o = 0; o <= LOOK_AHEAD && this.decoding.size < MAX_DECODES; o++) {
      this.decode(this.want + this.direction * o);
      if (o && o <= 2) this.decode(this.want - this.direction * o);
    }
  };
  Sequence.prototype.decode = function (i) {
    var self = this, blob = this.blobs[i], generation = this.generation;
    if (!blob || this.bitmaps.has(i) || this.decoding.has(i) || this.decoding.size >= MAX_DECODES) return;
    this.decoding.add(i);
    createImageBitmap(blob).then(function (bitmap) {
      if (generation !== self.generation) { bitmap.close(); return; }
      self.decoding.delete(i);
      self.bitmaps.set(i, bitmap);
      self.evict();
      self.draw();
      self.prepare();
    }).catch(function () { self.decoding.delete(i); });
  };
  Sequence.prototype.evict = function () {
    var keep = SETS[this.set].keep, want = this.want;
    while (this.bitmaps.size > keep) {
      var farthest = -1, distance = -1;
      this.bitmaps.forEach(function (b, i) {
        var away = Math.abs(i - want);
        if (away > distance) { distance = away; farthest = i; }
      });
      this.bitmaps.get(farthest).close();
      this.bitmaps.delete(farthest);
    }
  };
  Sequence.prototype.begin = function () {
    if (this.begun) return;
    this.begun = true;
    var self = this, generation = this.generation, coarse = [], requested = {};
    // A coarse pass first so the whole scene has something to show, then whatever is closest to the visitor.
    [32, 16, 8].forEach(function (step) {
      for (var i = 0; i < self.count; i += step) if (!requested['c' + i]) { requested['c' + i] = 1; coarse.push(i); }
    });
    function pick() {
      while (coarse.length) {
        var c = coarse.shift();
        if (!requested[c]) return c;
      }
      for (var d = 0; d < self.count; d++) {
        var ahead = self.want + self.direction * d, behind = self.want - self.direction * d;
        if (ahead >= 0 && ahead < self.count && !requested[ahead]) return ahead;
        if (behind >= 0 && behind < self.count && !requested[behind]) return behind;
      }
      return -1;
    }
    function next() {
      if (generation !== self.generation) return;
      var i = pick();
      if (i < 0) return;
      requested[i] = 1;
      fetch(self.url(i)).then(function (r) { return r.blob(); }).then(function (blob) {
        if (generation !== self.generation) return;
        self.blobs[i] = blob;
        self.prepare();
        next();
      }).catch(next);
    }
    for (var w = 0; w < DOWNLOADS; w++) next();
  };

  var seqs = {};
  document.querySelectorAll('canvas[data-seq]').forEach(function (c) {
    var s = new Sequence(c);
    seqs[s.name] = s;
    new IntersectionObserver(function (es, io) {
      if (es[0].isIntersecting) { s.begin(); io.disconnect(); }
    }, { rootMargin: '150% 0px' }).observe(c);
  });
  function resetAll() {
    Object.keys(seqs).forEach(function (k) { seqs[k].reset(); });
    ask();
  }
  narrowMedia.addEventListener('change', resetAll);

  /* ---------- Scene renderers: p is 0 to 1 across the pinned scroll ---------- */

  function copyAt(el, p, a, b) {
    var inn = smooth(seg(p, a, a + .05)), out = smooth(seg(p, b - .05, b));
    var o = inn * (1 - out);
    setStyle(el, 'opacity', o.toFixed(3));
    setStyle(el, 'transform', 'translateY(' + ((1 - inn) * 24 - out * 16).toFixed(1) + 'px)');
    setStyle(el, 'visibility', o < .01 ? 'hidden' : 'visible');
  }

  function grow(section, p, end) {
    var frame = section.querySelector('[data-frame]'), g = smooth(seg(p, 0, end));
    var narrow = narrowMedia.matches, from = narrow ? .92 : .74;
    // The wide frame is right-anchored once full size, so the small tile is shifted back to centre.
    var dx = narrow ? 0 : (innerWidth - frame.offsetWidth) / 2 * (1 - g);
    setStyle(frame, 'transform', g === 1 ? 'none' : 'translateX(' + dx.toFixed(1) + 'px) scale(' + (from + (1 - from) * g).toFixed(4) + ')');
    setStyle(frame, 'borderRadius', (narrow ? 20 : (1 - g) * 28).toFixed(1) + 'px');
  }

  var quote = document.querySelector('[data-study="quote"]');
  var dash = document.querySelector('[data-study="dash"]');
  var copyType = quote.querySelector('[data-copy="type"]');
  var copyFill = quote.querySelector('[data-copy="fill"]');
  var copyDash = dash.querySelector('[data-copy="dash"]');
  var toNight = quote.querySelector('[data-to-night]');
  var toDay = document.querySelector('[data-to-day]');
  var heroImg = document.querySelector('#heroShot img');
  var swapCol = $('swapCol');
  var litOn = -1;

  var render = {
    swap: function (p) {
      var t = p * 2.2 - .1, whole = Math.floor(clamp(t / 2) * 2), frac = t - whole;
      var pos = Math.min(2, whole + smooth(seg(frac, .25, .85)));
      setStyle(swapCol, 'transform', 'translateY(' + (-pos * 1.15).toFixed(4) + 'em)');
    },
    quote: function (p) {
      grow(quote, p, .1);
      seqs.a.seek(Math.round(seg(p, .08, .93) * (COUNTS.a - 1)));
      copyAt(copyType, p, .05, .6);         // the film's 5.5 to 14.5 s
      copyAt(copyFill, p, .66, .9);         // catalog close-up
      setStyle(toNight, 'opacity', smooth(seg(p, .93, 1)).toFixed(3));
    },
    lit: function (p) {
      var on = Math.round(seg(p, .08, .85) * litWords.length);
      if (on === litOn) return;
      litOn = on;
      litWords.forEach(function (w, i) { w.classList.toggle('on', i < on); });
    },
    inv: function (p) {
      var isInvoice = p > .14;
      setText($('invType'), isInvoice ? 'Tax invoice' : 'Quotation');
      setText($('invNo'), (isInvoice ? 'INV-202611-001' : 'Q-202611-001') + ' · Ramesh Traders');
      setStyle($('cgst'), 'opacity', (.22 + .78 * seg(p, .18, .32)).toFixed(3));
      setStyle($('sgst'), 'opacity', (.22 + .78 * seg(p, .3, .44)).toFixed(3));
      setText($('total'), money(580 + 104.4 * smooth(seg(p, .44, .72))));
      setText($('stock'), 'Stock ' + Math.round(2500 - 10 * smooth(seg(p, .74, .86))).toLocaleString('en-IN') + ' kg');
      setStyle(toDay, 'opacity', smooth(seg(p, .92, 1)).toFixed(3));
    },
    dash: function (p) {
      grow(dash, 1, 1);
      seqs.b.seek(Math.round(seg(p, .02, .95) * (COUNTS.b - 1)));
      copyAt(copyDash, p, .1, 1.2);
    }
  };

  /* ---------- Scroll loop ----------
     The page scrolls natively. Animation eases toward the scroll position, so a mouse wheel's
     100 px jumps read as continuous motion. Time-based easing behaves the same at 60 and 120 Hz. */

  var EASE_MS = 85;
  var studies = Array.prototype.map.call(document.querySelectorAll('[data-study]'), function (el) {
    return { el: el, name: el.dataset.study, top: 0, height: 0 };
  });
  var nav = $('nav'), viewport = innerHeight;
  var current = scrollY, running = false, lastTime = 0;

  function measure() {
    viewport = innerHeight;
    studies.forEach(function (s) {
      s.top = s.el.getBoundingClientRect().top + scrollY;
      s.height = s.el.offsetHeight;
    });
  }

  function paint(y) {
    var night = false;
    if (y < viewport * 1.2) setStyle(heroImg, 'transform', 'scale(' + (1 + .06 * clamp(y / viewport)).toFixed(4) + ')');
    studies.forEach(function (s) {
      var top = s.top - y, bottom = top + s.height;
      if (bottom < -viewport || top > viewport * 1.2) return;
      var p = clamp(-top / (s.height - viewport));
      render[s.name](p);
      if (top <= 24 && bottom > 24) {
        if (s.name === 'lit') night = true;
        if (s.name === 'inv') night = p < .96;
        if (s.name === 'quote') night = p > .96;
      }
    });
    if (nav._night !== night) { nav._night = night; nav.classList.toggle('on-night', night); }
  }

  function loop(now) {
    var dt = Math.min(64, now - lastTime);
    lastTime = now;
    var target = scrollY;
    current += (target - current) * (1 - Math.exp(-dt / EASE_MS));
    if (Math.abs(target - current) < .3) current = target;
    paint(current);
    if (current !== target) { requestAnimationFrame(loop); } else { running = false; }
  }
  function ask() {
    if (running) return;
    running = true;
    lastTime = performance.now();
    requestAnimationFrame(loop);
  }

  addEventListener('scroll', ask, { passive: true });
  var lastSet = chooseSet();
  addEventListener('resize', function () {
    measure();
    var set = chooseSet();
    if (set !== lastSet) { lastSet = set; if (!narrowMedia.matches) resetAll(); }
    ask();
  });
  if (window.ResizeObserver) new ResizeObserver(function () { measure(); ask(); }).observe(document.body);
  measure();
  current = scrollY;
  paint(current);

  /* ---------- Bento reveal, staggered per row ---------- */

  document.querySelectorAll('.reveal').forEach(function (el, i) { el.style.setProperty('--i', i % 4); });
  var revealer = new IntersectionObserver(function (es) {
    es.forEach(function (e) {
      if (e.isIntersecting) { e.target.classList.add('in'); revealer.unobserve(e.target); }
    });
  }, { rootMargin: '0px 0px -8% 0px' });
  document.querySelectorAll('.reveal').forEach(function (el) { revealer.observe(el); });
})();

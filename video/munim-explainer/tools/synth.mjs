// Original, deterministic soundtrack for the Munim film: 120 BPM drum-driven electronic bed + UI SFX.
// Writes assets/audio/music.wav and assets/audio/sfx.wav (48 kHz, stereo, 16-bit). No third-party audio.
import {writeFileSync, mkdirSync} from 'node:fs';

const SR = 48000, DUR = 45, N = SR * DUR;
const BEAT = 0.5, BAR0 = 1.0; // bars start at 1 s, 3 s, 5 s, ...
let seed = 1234567;
const rnd = () => { seed = (seed * 1664525 + 1013904223) >>> 0; return seed / 4294967296; };
const noise = () => rnd() * 2 - 1;
const midi = m => 440 * Math.pow(2, (m - 69) / 12);

function buffers() { return [new Float32Array(N), new Float32Array(N)]; }
function add(buf, t0, len, fn, pan = 0, gain = 1) {
  const s0 = Math.round(t0 * SR), n = Math.round(len * SR);
  const gl = gain * Math.cos((pan + 1) * Math.PI / 4), gr = gain * Math.sin((pan + 1) * Math.PI / 4);
  for (let i = 0; i < n; i++) { const j = s0 + i; if (j < 0 || j >= N) continue; const v = fn(i / SR, i); buf[0][j] += v * gl; buf[1][j] += v * gr; }
}
const env = (t, a, d) => (t < a ? t / a : Math.exp(-(t - a) / d));

// ── instruments ──────────────────────────────────────────────────────────────
const kick = (b, t0, g = 1) => { let ph = 0; add(b, t0, .45, t => { const f = 45 + 95 * Math.exp(-t / .045); ph += 2 * Math.PI * f / SR; return Math.sin(ph) * env(t, .002, .16) * .95 + noise() * env(t, .0005, .004) * .2; }, 0, g); };
const clap = (b, t0, g = 1) => { let lp = 0; add(b, t0, .3, t => { const n = noise(); lp += .35 * (n - lp); const hp = n - lp; const burst = t < .03 ? (Math.floor(t / .01) % 2 ? .6 : 1) : 1; return hp * env(t, .001, .07) * burst; }, .05, g * .55); };
const hat = (b, t0, g = 1, open = false, pan = .25) => { let lp = 0; add(b, t0, open ? .25 : .06, t => { const n = noise(); lp += .6 * (n - lp); return (n - lp) * env(t, .0005, open ? .08 : .018); }, pan, g * .32); };
const bass = (b, t0, len, m, g = 1) => { const f = midi(m); let lp = 0; add(b, t0, len, (t) => { const ph = 2 * Math.PI * f * t; const saw = Math.sin(ph) + .5 * Math.sin(2 * ph) + .25 * Math.sin(3 * ph) + .12 * Math.sin(4 * ph); lp += .18 * (saw - lp); const e = Math.min(1, t / .005) * Math.min(1, (len - t) / .02) * (.7 + .3 * Math.exp(-t / .08)); return lp * e; }, 0, g * .42); };
const pluck = (b, t0, m, g = 1, pan = 0) => { const f = midi(m); add(b, t0, .5, t => { const ph = 2 * Math.PI * f * t; return (Math.sin(ph) + .35 * Math.sin(2 * ph + .3) + .12 * Math.sin(3 * ph)) * env(t, .002, .11); }, pan, g * .16); };
const pad = (b, t0, len, notes, g = 1) => { for (const [k, m] of notes.entries()) { const f = midi(m); add(b, t0, len, t => { const e = Math.min(1, t / .5) * Math.min(1, (len - t) / .5); const v = Math.sin(2 * Math.PI * f * t + Math.sin(2 * Math.PI * .3 * t) * .4) + .3 * Math.sin(2 * Math.PI * f * 2.003 * t); return v * e; }, k % 2 ? .35 : -.35, g * .045); } };
const riser = (b, t0, len, g = 1) => { let lp = 0; add(b, t0, len, t => { const p = t / len; const n = noise(); lp += (.02 + .5 * p * p) * (n - lp); return lp * p * p; }, 0, g * .9); };
const crash = (b, t0, g = 1) => { let lp = 0; add(b, t0, 2.2, t => { const n = noise(); lp += .7 * (n - lp); return (n - lp) * env(t, .002, .55); }, 0, g * .28); };

// ── music arrangement ────────────────────────────────────────────────────────
// Am – F – C – G, one chord per bar (2 s).
const CH = [[57, 60, 64, 69], [53, 57, 60, 65], [48, 55, 60, 64], [55, 59, 62, 67]];
const ROOT = [45, 41, 48, 43];
const music = buffers();
const barCount = Math.ceil((DUR - BAR0) / 2);
pad(music, 0, BAR0 + .3, [57, 64, 69], .8);
for (let bar = 0; bar < barCount; bar++) {
  const t = BAR0 + bar * 2, ch = CH[bar % 4], root = ROOT[bar % 4];
  const end = t >= 43; // tail
  const intro = t < 5, full = t >= 5 && t < 43, build = t >= 21 && t < 25, outro = t >= 39;
  pad(music, t, 2.05, ch.slice(0, 3).map(m => m + 12), end ? 1.2 : intro ? 1 : .7);
  if (end) continue;
  for (let s = 0; s < 4; s++) {
    const bt = t + s * BEAT;
    if (full && !(t === 25 && s >= 2)) kick(music, bt, s === 0 ? 1 : .9);
    if (full && (s === 1 || s === 3) && !(t === 25 && s === 3)) clap(music, bt);
    hat(music, bt + BEAT / 2, intro ? .6 : 1, !intro && s === 3, .3);
    if (!intro) hat(music, bt, .45, false, -.25);
    if (build) { hat(music, bt + BEAT / 4, .5, false, -.4); hat(music, bt + 3 * BEAT / 4, .5, false, .4); }
    if (full) { bass(music, bt, .22, root, .9); bass(music, bt + BEAT / 2, .2, root + (s === 3 ? 7 : 12), .7); }
  }
  // 16th arpeggio; quieter in intro, thinned in outro
  const arp = [ch[0] + 12, ch[1] + 12, ch[2] + 12, ch[3] + 12, ch[2] + 12, ch[1] + 12, ch[3] + 12, ch[2] + 24];
  for (let k = 0; k < 16; k++) { if (outro && k % 2) continue; pluck(music, t + k * BEAT / 4, arp[k % 8], intro ? .55 : 1, k % 2 ? .4 : -.4); }
}
riser(music, 24.0, 2.0, .5);
kick(music, 26.0, 1.1); crash(music, 26.0, 1);
riser(music, 37.5, 1.5, .35);
kick(music, 39.0, 1.15); crash(music, 39.0, .9);
pad(music, 39, 6, [57, 64, 69, 76], 1.1);
// Master fade at the very end so the tail resolves before 45 s.
for (let i = 0; i < N; i++) { const t = i / SR; const f = t > 43 ? Math.max(0, (45 - t) / 2) : 1; const fi = Math.min(1, t / .25); music[0][i] *= f * fi; music[1][i] *= f * fi; }

// ── SFX (aligned to on-screen actions in film.tsx) ───────────────────────────
const sfx = buffers();
const blip = (t0, f0, f1, len, g, pan = 0) => { let ph = 0; add(sfx, t0, len, t => { const f = f0 + (f1 - f0) * Math.min(1, t / len); ph += 2 * Math.PI * f / SR; return Math.sin(ph) * env(t, .002, len / 4); }, pan, g); };
const keyClick = (t0, g) => { let lp = 0; add(sfx, t0, .03, t => { const n = noise(); lp += .5 * (n - lp); return (n - lp) * env(t, .0003, .006) + Math.sin(2 * Math.PI * 1900 * t) * env(t, .0003, .004) * .4; }, (rnd() - .5) * .3, g); };
const whoosh = (t0, len, g) => { let lp = 0; add(sfx, t0, len, t => { const p = t / len; lp += (.04 + .25 * Math.sin(Math.PI * p)) * (noise() - lp); return lp * Math.sin(Math.PI * p); }, 0, g); };
const thump = (t0, g) => { let ph = 0; add(sfx, t0, .2, t => { const f = 70 + 110 * Math.exp(-t / .03); ph += 2 * Math.PI * f / SR; return Math.sin(ph) * env(t, .002, .05); }, 0, g); };
const chime = (t0, g) => { for (const [f, d] of [[1568, .35], [2093, .3], [3136, .18]]) add(sfx, t0, 1.2, t => Math.sin(2 * Math.PI * f * t) * env(t, .003, d), 0, g * .5); };

// hook word swaps
for (const [t, f] of [[.95, 1400], [2.0, 1600], [3.0, 1800]]) blip(t, f, f * .7, .12, .35);
// typing
const typing = (a, b, chars) => { const step = (b - a) / chars; for (let k = 0; k < chars; k += 2) keyClick(a + k * step + (rnd() - .5) * .012, .22 + rnd() * .12); };
typing(6.0, 7.85, 52); typing(21.7, 23.35, 45);
// send + bubble fly + card pop
for (const t of [8.2, 23.7]) { blip(t, 620, 310, .09, .55); thump(t, .4); }
for (const t of [8.3, 23.8]) whoosh(t, .35, .35);
for (const t of [9.8, 25.05]) { blip(t, 880, 1320, .1, .4); blip(t + .03, 1760, 2200, .06, .15, .2); }
// catalog callouts
for (const [i, t] of [16.25, 16.85, 17.45].entries()) blip(t, 1200 + i * 200, 1500 + i * 200, .08, .3, (i - 1) * .3);
// invoice total done + stock chip
chime(26.8, .45); blip(27.6, 1300, 1700, .08, .28);
// dashboard: nav switch, card flight, landing, badge
blip(31.7, 900, 1100, .07, .2); whoosh(31.9, 1.0, .45); thump(33.0, .55); blip(33.0, 1046, 1046, .15, .25); blip(33.45, 1568, 1568, .1, .18);

// ── write ────────────────────────────────────────────────────────────────────
function peak(b) { let p = 0; for (const ch of b) for (const v of ch) p = Math.max(p, Math.abs(v)); return p; }
function writeWav(path, b, target) {
  const p = peak(b), k = target / p, data = Buffer.alloc(N * 4);
  for (let i = 0; i < N; i++) for (let c = 0; c < 2; c++) data.writeInt16LE(Math.round(Math.max(-1, Math.min(1, b[c][i] * k)) * 32767), (i * 2 + c) * 2);
  const h = Buffer.alloc(44);
  h.write('RIFF', 0); h.writeUInt32LE(36 + data.length, 4); h.write('WAVE', 8); h.write('fmt ', 12); h.writeUInt32LE(16, 16); h.writeUInt16LE(1, 20); h.writeUInt16LE(2, 22);
  h.writeUInt32LE(SR, 24); h.writeUInt32LE(SR * 4, 28); h.writeUInt16LE(4, 32); h.writeUInt16LE(16, 34); h.write('data', 36); h.writeUInt32LE(data.length, 40);
  writeFileSync(path, Buffer.concat([h, data])); console.log(path, 'peak', p.toFixed(3), '->', target);
}
mkdirSync('assets/audio', {recursive: true});
writeWav('assets/audio/music.wav', music, .55);
writeWav('assets/audio/sfx.wav', sfx, .38);

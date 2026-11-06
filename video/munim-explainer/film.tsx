import React from 'react';
import {defineFilm, secondsAt} from '@launch-video-maker/runtime';
import {AssetImage} from '@launch-video-maker/runtime/react';

// Text-free footage for the landing page. 'none' is the finished film; tools/render-plates.mjs
// renders throwaway copies of this file with this line changed to 'wide' or 'phone'.
const PLATE = 'none' as 'none' | 'wide' | 'phone';
const STAGE = PLATE === 'phone' ? {w: 1080, h: 1200} : {w: 1920, h: 1080};
// Plates keep only the two stretches the page scrubs: quote + catalog, then the dashboard landing.
const PLATE_QUOTE = [165, 624], PLATE_DASH = [930, 1140];
const PLATE_FRAMES = PLATE_QUOTE[1] - PLATE_QUOTE[0] + PLATE_DASH[1] - PLATE_DASH[0];
const plateSource = (f: number) => {
  const first = PLATE_QUOTE[1] - PLATE_QUOTE[0];
  return f < first ? f + PLATE_QUOTE[0] : f - first + PLATE_DASH[0];
};

// Munim explainer · direction A "Warm Studio" · 45 s @ 30 fps · music grid 120 BPM (bar = 60 frames).
export const film = defineFilm({
  width: STAGE.w, height: STAGE.h, fps: {num: 30, den: 1}, durationInFrames: PLATE === 'none' ? 1350 : PLATE_FRAMES, seed: 7,
  scenes: PLATE !== 'none' ? [] : [
    {id: 'hook', start: 0, end: 150},
    {id: 'quote', start: 150, end: 450},
    {id: 'catalog', start: 450, end: 630},
    {id: 'invoice', start: 630, end: 930},
    {id: 'dashboard', start: 930, end: 1140},
    {id: 'end', start: 1140, end: 1350},
  ],
  assets: [
    {id: 'mark', kind: 'image', src: 'assets/brand/munim-mark.png'},
    {id: 'j500', kind: 'font', family: 'J500', src: 'assets/fonts/jakarta-500.woff2'},
    {id: 'j600', kind: 'font', family: 'J600', src: 'assets/fonts/jakarta-600.woff2'},
    {id: 'j700', kind: 'font', family: 'J700', src: 'assets/fonts/jakarta-700.woff2'},
    {id: 'j800', kind: 'font', family: 'J800', src: 'assets/fonts/jakarta-800.woff2'},
    {id: 'i400', kind: 'font', family: 'I400', src: 'assets/fonts/inter-400.woff2'},
    {id: 'i500', kind: 'font', family: 'I500', src: 'assets/fonts/inter-500.woff2'},
    {id: 'i600', kind: 'font', family: 'I600', src: 'assets/fonts/inter-600.woff2'},
    {id: 'i700', kind: 'font', family: 'I700', src: 'assets/fonts/inter-700.woff2'},
    {id: 'music', kind: 'audio', src: 'assets/audio/music.wav'},
    {id: 'sfx', kind: 'audio', src: 'assets/audio/sfx.wav'},
  ],
  audio: PLATE !== 'none' ? [] : [
    {id: 'music', asset: 'music', start: 0, end: 1350, gain: 1.45},
    {id: 'sfx', asset: 'sfx', start: 0, end: 1350, gain: 1.28},
  ],
  markers: PLATE !== 'none' ? {} : {send1: 246, card1: 294, send2: 711, total: 780, land: 990, logo: 1163},
});

// ─── time helpers (pure functions of t) ──────────────────────────────────────
const clamp = (x: number, a = 0, b = 1) => Math.max(a, Math.min(b, x));
const lerp = (a: number, b: number, p: number) => a + (b - a) * p;
const prog = (t: number, a: number, b: number) => clamp((t - a) / (b - a));
const inOut = (x: number) => { x = clamp(x); return x < .5 ? 4 * x * x * x : 1 - Math.pow(-2 * x + 2, 3) / 2; };
const out = (x: number) => 1 - Math.pow(1 - clamp(x), 3);
const outQuint = (x: number) => 1 - Math.pow(1 - clamp(x), 5);
function spring(t: number, omega = 16, zeta = .78) {
  if (t <= 0) return 0;
  const wd = omega * Math.sqrt(1 - zeta * zeta);
  return 1 - Math.exp(-zeta * omega * t) * (Math.cos(wd * t) + zeta * omega / wd * Math.sin(wd * t));
}
const inr = (v: number) => '₹' + v.toLocaleString('en-IN', {minimumFractionDigits: 2, maximumFractionDigits: 2});
const typed = (text: string, t: number, a: number, b: number) => text.slice(0, Math.round(text.length * clamp((t - a) / (b - a))));

// ─── palette & type ──────────────────────────────────────────────────────────
const C = {o500: '#f97316', o600: '#ea580c', o50: '#fff7ed', o100: '#ffedd5', o200: '#fed7aa', ink: '#0f172a', s800: '#1e293b', s600: '#475569', s500: '#64748b', s400: '#94a3b8', s200: '#e2e8f0', s100: '#f1f5f9', s50: '#f8fafc', g600: '#059669', g50: '#ecfdf5', amber: '#b45309', amberBg: '#fef3c7'};
const F = (family: string, size: number, extra: React.CSSProperties = {}): React.CSSProperties => ({fontFamily: `${family}, sans-serif`, fontSize: size, ...extra});
const abs = (s: React.CSSProperties): React.CSSProperties => ({position: 'absolute', ...s});

// ─── layout constants (stage px) ─────────────────────────────────────────────
const WIN = {x: 760, y: 96, w: 1080, h: 888};
const SIDE = 232, HEAD = 76, COMPOSER = 112, PAD = 36;
const MAIN_W = WIN.w - SIDE;
const CARD_W = 580;
const Q_H = {head: 88, line: 84, sub: 58, pdf: 58};
const I_TOT = 190;
const QUOTE_H = Q_H.head + Q_H.line + Q_H.sub + Q_H.pdf;
const INV_H = Q_H.head + Q_H.line + I_TOT + Q_H.pdf;
const Y = {bubble1: 28, card1: 112};
const B2 = Y.card1 + QUOTE_H + 30, CARD2 = B2 + 84;
const SCROLL_MAX = CARD2 + INV_H - (WIN.h - HEAD - COMPOSER) + 24;

const PROMPT1 = 'Quotation for Ramesh Traders, 10 TMT Steel Rod 12mm';
const PROMPT2 = 'Convert quotation Q-202611-001 to an invoice';

// key moments (seconds)
const T = {
  winIn: 4.35, cap1: 5.5, type1: [6.0, 7.85], send1: 8.2, fly1: 8.3, dots1: [8.85, 9.75], card1: 9.8,
  zoomIn: [15.0, 16.1], call: [16.25, 16.85, 17.45], zoomOut: [19.7, 20.8],
  cap3: 20.9, type2: [21.7, 23.35], send2: 23.7, fly2: 23.8, scroll: [23.9, 25.9], dots2: [24.35, 25.05], card2: 25.05,
  total: 26.0, pushTot: [25.95, 27.0], stock: 27.6, pullTot: [30.2, 31.0],
  toDash: 31.4, fly: [31.9, 33.0], land: 33.0, out: [37.95, 38.75], logo: 38.75,
};

// ─── small UI pieces ─────────────────────────────────────────────────────────
const Mark = ({w, style}: {w: number; style?: React.CSSProperties}) =>
  <AssetImage asset="mark" style={{width: w, height: w * 178 / 233, display: 'block', ...style}} />;

function Icon({d, size = 22, color = C.s500, sw = 1.9}: {d: string; size?: number; color?: string; sw?: number}) {
  return <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth={sw} strokeLinecap="round" strokeLinejoin="round"><path d={d} /></svg>;
}
const ICON = {
  home: 'M3 10.5 12 3l9 7.5V20a1 1 0 0 1-1 1h-5v-6H9v6H4a1 1 0 0 1-1-1z',
  chat: 'M21 12a8 8 0 0 1-11.6 7.1L3 21l1.9-6.4A8 8 0 1 1 21 12z',
  file: 'M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8zM14 3v5h5M9 13h6M9 17h4',
  receipt: 'M6 3h12v18l-3-2-3 2-3-2-3 2zM9 8h6M9 12h6M9 16h3',
  users: 'M16 20v-1a4 4 0 0 0-4-4H7a4 4 0 0 0-4 4v1M9.5 11a3.5 3.5 0 1 0 0-7 3.5 3.5 0 0 0 0 7zM21 20v-1a4 4 0 0 0-3-3.9M16 4.1a3.5 3.5 0 0 1 0 6.8',
  box: 'M21 8 12 3 3 8v8l9 5 9-5zM3 8l9 5 9-5M12 13v8',
  gear: 'M12 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6zM19.4 15a1.7 1.7 0 0 0 .3 1.8l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.7 1.7 0 0 0-1.8-.3 1.7 1.7 0 0 0-1 1.5V21a2 2 0 1 1-4 0v-.1a1.7 1.7 0 0 0-1.1-1.5 1.7 1.7 0 0 0-1.8.3l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1a1.7 1.7 0 0 0 .3-1.8 1.7 1.7 0 0 0-1.5-1H3a2 2 0 1 1 0-4h.1a1.7 1.7 0 0 0 1.5-1.1 1.7 1.7 0 0 0-.3-1.8l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1a1.7 1.7 0 0 0 1.8.3H9a1.7 1.7 0 0 0 1-1.5V3a2 2 0 1 1 4 0v.1a1.7 1.7 0 0 0 1 1.5 1.7 1.7 0 0 0 1.8-.3l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1a1.7 1.7 0 0 0-.3 1.8V9a1.7 1.7 0 0 0 1.5 1H21a2 2 0 1 1 0 4h-.1a1.7 1.7 0 0 0-1.5 1z',
  send: 'M5 12h14M13 6l6 6-6 6',
  download: 'M12 4v11M7 10l5 5 5-5M5 20h14',
  alert: 'M12 9v4M12 17h.01M10.3 3.9 1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0z',
  check: 'M20 6 9 17l-5-5',
};

function Badge({label}: {label: 'Draft' | 'Unpaid' | 'Invoiced'}) {
  const s = {Draft: [C.s100, C.s600, 'transparent'], Unpaid: [C.amberBg, C.amber, '#fcd34d'], Invoiced: [C.g50, C.g600, '#a7f3d0']}[label];
  return <span style={F('I500', 13, {background: s[0], color: s[1], border: `1px solid ${s[2]}`, borderRadius: 999, padding: '2px 10px', marginLeft: 10})}>{label}</span>;
}

// Annotation highlight on a card value (S03 only).
function Hl({t, at, children}: {t: number; at: number; children: React.ReactNode}) {
  const v = at < 0 ? 0 : out(prog(t, at, at + .25)) * (1 - prog(t, T.zoomOut[0], T.zoomOut[0] + .3));
  return <span style={{background: `rgba(254,215,170,${v})`, color: v > .5 ? C.o600 : undefined, borderRadius: 5, padding: '1px 4px', margin: '0 -4px', boxShadow: `0 0 0 ${2 * v}px rgba(249,115,22,${.35 * v})`}}>{children}</span>;
}

// ─── document card (redraw of DocumentResultCard.tsx) ────────────────────────
function DocCard({kind, t0, t, total = 0}: {kind: 'quotation' | 'invoice'; t0: number; t: number; total?: number}) {
  const inv = kind === 'invoice';
  const lt = t - t0;
  const open = spring(lt, 14, .86);
  const row = (i: number) => ({opacity: out(prog(lt, .1 + i * .16, .36 + i * .16)), transform: `translateY(${lerp(10, 0, out(prog(lt, .1 + i * .16, .4 + i * .16)))}px)`});
  const h = inv ? INV_H : QUOTE_H;
  const tax = (i: number) => out(prog(lt, .55 + i * .2, .85 + i * .2));
  const tp = prog(t, T.total, T.total + .8);
  const shown = inv ? total * outQuint(tp) : 0;
  return (
    <div style={{width: CARD_W, height: h * lerp(.6, 1, open), opacity: clamp(lt / .14), transformOrigin: '0 0', transform: `scale(${lerp(.94, 1, open)})`, background: '#fff', borderRadius: 22, border: `1px solid ${C.s200}`, boxShadow: '0 18px 50px rgba(15,23,42,.10), 0 2px 6px rgba(15,23,42,.05)', overflow: 'hidden'}}>
      <div style={{height: Q_H.head, display: 'flex', alignItems: 'center', gap: 16, padding: '0 24px', borderBottom: `1px solid ${C.s100}`, ...row(0)}}>
        <span style={{width: 48, height: 48, borderRadius: 14, background: inv ? C.g50 : C.o50, display: 'flex', alignItems: 'center', justifyContent: 'center'}}>
          <Icon d={inv ? ICON.receipt : ICON.file} size={24} color={inv ? C.g600 : C.o600} />
        </span>
        <div>
          <div style={F('I600', 13, {letterSpacing: '.08em', color: C.s500, textTransform: 'uppercase'})}>{inv ? 'Tax invoice' : 'Quotation'}</div>
          <div style={F('I600', 21, {color: C.ink, marginTop: 3})}>{inv ? 'INV-202611-001' : 'Q-202611-001'} · Ramesh Traders</div>
        </div>
      </div>
      <div style={{height: Q_H.line, display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '0 24px', ...row(1)}}>
        <div>
          <div style={F('I600', 19, {color: C.s800})}>TMT Steel Rod 12mm</div>
          <div style={F('I400', 15, {color: C.s500, marginTop: 5})}>10 kg × <Hl t={t} at={inv ? -1 : T.call[0]}>₹58.00</Hl> · <Hl t={t} at={inv ? -1 : T.call[1]}>HSN 7213</Hl></div>
        </div>
        <div style={F('I600', 19, {color: C.ink})}>₹580.00</div>
      </div>
      {inv ? (
        <div style={{height: I_TOT, background: C.s50, borderTop: `1px solid ${C.s100}`, padding: '16px 24px', ...row(2)}}>
          {[['Subtotal', 580], ['CGST 9%', 52.2], ['SGST 9%', 52.2]].map(([l, v], i) => (
            <div key={l as string} style={{display: 'flex', justifyContent: 'space-between', height: 34, alignItems: 'center', ...F('I500', 17, {color: C.s600}), opacity: i ? tax(i - 1) : 1, transform: `translateX(${i ? lerp(-12, 0, tax(i - 1)) : 0}px)`}}>
              <span>{l}</span><span>{inr(v as number)}</span>
            </div>
          ))}
          <div style={{display: 'flex', justifyContent: 'space-between', alignItems: 'center', height: 56, marginTop: 6, borderTop: `1px solid ${C.s200}`, ...F('I700', 24, {color: C.ink}), opacity: out(prog(t, T.total - .15, T.total + .1))}}>
            <span>Total</span><span style={{color: tp > 0 && tp < 1 ? C.o600 : C.ink}}>{inr(Math.round(shown * 100) / 100)}</span>
          </div>
        </div>
      ) : (
        <div style={{height: Q_H.sub, display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '0 24px', background: C.s50, borderTop: `1px solid ${C.s100}`, ...F('I700', 20, {color: C.ink}), ...row(2)}}>
          <span>Subtotal</span><span>₹580.00</span>
        </div>
      )}
      <div style={{height: Q_H.pdf, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 10, borderTop: `1px solid ${C.s100}`, ...F('I600', 17, {color: C.o600}), ...row(inv ? 4.6 : 3)}}>
        <Icon d={ICON.download} size={20} color={C.o600} /> Download PDF
      </div>
    </div>
  );
}

function UserBubble({text}: {text: string}) {
  return <div style={{background: C.o500, color: '#fff', borderRadius: '22px 22px 8px 22px', padding: '15px 22px', whiteSpace: 'nowrap', boxShadow: '0 6px 18px rgba(234,88,12,.22)', ...F('I500', 20)}}>{text}</div>;
}

function TypingDots({t, a, b}: {t: number; a: number; b: number}) {
  const v = out(prog(t, a, a + .15)) * (1 - prog(t, b - .1, b));
  return (
    <div style={{display: 'flex', gap: 8, padding: '18px 22px', background: '#fff', border: `1px solid ${C.s200}`, borderRadius: '22px 22px 22px 8px', opacity: v, transform: `scale(${lerp(.9, 1, v)})`, transformOrigin: '0 100%', width: 'fit-content'}}>
      {[0, 1, 2].map(i => <span key={i} style={{width: 10, height: 10, borderRadius: 5, background: '#cbd5e1', transform: `translateY(${-6 * Math.max(0, Math.sin(t * Math.PI * 3.2 - i * .9))}px)`}} />)}
    </div>
  );
}

function Composer({t, text, pressAt, typing}: {t: number; text: string; pressAt: number[]; typing: boolean}) {
  const caretOn = typing || Math.floor(t * 2.2) % 2 === 0;
  const press = pressAt.reduce((m, p) => Math.max(m, t >= p ? 1 - spring(t - p, 26, .55) : 0), 0);
  const active = text.length > 0;
  return (
    <div style={abs({left: PAD, right: PAD, top: 18, height: 76, display: 'flex', alignItems: 'center', gap: 12, background: C.s50, border: `1.5px solid ${active ? '#fdba74' : C.s200}`, borderRadius: 20, padding: '0 10px 0 22px', boxShadow: active ? '0 0 0 4px rgba(255,237,213,.9)' : 'none'})}>
      <div style={{flex: 1, ...F('I400', 20, {color: text ? C.ink : C.s400}), whiteSpace: 'nowrap', overflow: 'hidden'}}>
        {text || 'e.g. Quotation for Ramesh Traders, 10 TMT Steel Rod 12mm'}
        {caretOn && <span style={{display: 'inline-block', width: 2.5, height: 24, background: C.o500, verticalAlign: -5, marginLeft: 2}} />}
      </div>
      <div style={{width: 54, height: 54, borderRadius: 15, background: active ? C.o500 : C.s200, display: 'flex', alignItems: 'center', justifyContent: 'center', transform: `scale(${1 - press * .14})`, boxShadow: active ? '0 6px 16px rgba(249,115,22,.35)' : 'none'}}>
        <Icon d={ICON.send} size={24} color="#fff" sw={2.4} />
      </div>
    </div>
  );
}

function Sidebar({t}: {t: number}) {
  const items: [string, string][] = [['Home', ICON.home], ['Assistant', ICON.chat], ['Documents', ICON.file], ['Customers', ICON.users], ['Stock', ICON.box], ['Settings', ICON.gear]];
  const sel = lerp(1, 0, inOut(prog(t, T.toDash + .25, T.toDash + .7)));
  return (
    <div style={abs({left: 0, top: 0, width: SIDE, bottom: 0, background: '#fff', borderRight: `1px solid ${C.s100}`})}>
      <div style={abs({left: 22, top: 26, display: 'flex', alignItems: 'center', gap: 12})}>
        <Mark w={42} /><span style={F('J700', 23, {color: C.ink})}>Munim</span>
      </div>
      <div style={abs({left: 14, right: 14, top: 98 + sel * 50, height: 44, borderRadius: 12, background: C.o50})} />
      {items.map(([label, d], i) => {
        const on = clamp(1 - Math.abs(sel - i));
        const col = on > .5 ? C.o600 : C.s600;
        return (
          <div key={label} style={abs({left: 28, top: 98 + i * 50, height: 44, display: 'flex', alignItems: 'center', gap: 14, ...F('I500', 17, {color: col})})}>
            <Icon d={d} size={20} color={col} />{label}
          </div>
        );
      })}
      <div style={abs({left: 14, right: 14, bottom: 16, height: 60, borderRadius: 14, background: C.s50, display: 'flex', alignItems: 'center', gap: 10, padding: '0 12px'})}>
        <span style={{width: 36, height: 36, borderRadius: 18, background: '#fff', border: `1px solid ${C.s200}`, display: 'flex', alignItems: 'center', justifyContent: 'center', ...F('I600', 13, {color: C.s600})}}>VI</span>
        <div style={{minWidth: 0}}>
          <div style={F('I600', 14, {color: C.ink, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', width: 150})}>Vaidya Industrial S…</div>
          <div style={F('I400', 12, {color: C.s500})}>GSTIN 27AABCV1234A…</div>
        </div>
      </div>
    </div>
  );
}

// Callout pill used for annotations (not product UI).
function Callout({t, at, label, value, style}: {t: number; at: number; label: string; value: string; style: React.CSSProperties}) {
  const p = spring(t - at, 18, .8), v = clamp((t - at) / .12);
  return (
    <div style={abs({...style, opacity: v, transform: `translateY(${lerp(8, 0, p)}px) scale(${lerp(.9, 1, p)})`, transformOrigin: '50% 100%', background: C.ink, color: '#fff', borderRadius: 12, padding: '7px 12px', whiteSpace: 'nowrap', boxShadow: '0 8px 20px rgba(15,23,42,.25)'})}>
      <span style={F('I500', 11, {color: '#fdba74', letterSpacing: '.08em', textTransform: 'uppercase', display: 'block'})}>{label}</span>
      <span style={F('I600', 15)}>{value}</span>
    </div>
  );
}

// ─── assistant (chat) view ───────────────────────────────────────────────────
function AssistantView({t}: {t: number}) {
  const scroll = SCROLL_MAX * inOut(prog(t, T.scroll[0], T.scroll[1]));
  const composerY = WIN.h - HEAD - COMPOSER + 30; // composer text row, thread coords
  const fly = (at: number, y: number) => {
    const p = spring(t - at, 15, .84);
    return {opacity: clamp((t - at) / .1), transform: `translate(${lerp(-180, 0, p)}px, ${lerp(composerY - (y - scroll), 0, p)}px) scale(${lerp(.92, 1, p)})`, transformOrigin: '100% 100%'};
  };
  let text = '', typing = false;
  if (t >= T.type1[0] && t < T.fly1) { text = typed(PROMPT1, t, T.type1[0], T.type1[1]); typing = t < T.type1[1]; }
  if (t >= T.type2[0] && t < T.fly2) { text = typed(PROMPT2, t, T.type2[0], T.type2[1]); typing = t < T.type2[1]; }
  return (
    <>
      <div style={abs({left: 0, right: 0, top: 0, height: HEAD, background: '#fff', borderBottom: `1px solid ${C.s200}`, padding: '17px 28px'})}>
        <div style={F('J600', 19, {color: C.ink})}>Assistant</div>
        <div style={F('I400', 14, {color: C.s500, marginTop: 2})}>Quotations, GST invoices and stock checks</div>
      </div>
      <div style={abs({left: 0, right: 0, top: HEAD, bottom: COMPOSER, overflow: 'hidden', background: C.s50})}>
        <div style={abs({left: 0, right: 0, top: -scroll, height: 2000})}>
          {t >= T.fly1 && <div style={abs({right: PAD, top: Y.bubble1, ...fly(T.fly1, Y.bubble1)})}><UserBubble text={PROMPT1} /></div>}
          {t >= T.dots1[0] && t < T.card1 && <div style={abs({left: PAD, top: Y.card1})}><TypingDots t={t} a={T.dots1[0]} b={T.dots1[1]} /></div>}
          {t >= T.card1 && <div style={abs({left: PAD, top: Y.card1})}><DocCard kind="quotation" t0={T.card1} t={t} /></div>}
          {t < T.zoomOut[1] + .3 && <>
            <Callout t={t} at={T.call[0]} label="Price · from your catalog" value="₹58.00 per kg" style={{left: PAD + CARD_W + 20, top: Y.card1 + 14}} />
            <Callout t={t} at={T.call[1]} label="HSN code" value="7213 · steel bars & rods" style={{left: PAD + CARD_W + 20, top: Y.card1 + 14 + 66}} />
            <Callout t={t} at={T.call[2]} label="GST rate" value="18% · applied by Munim" style={{left: PAD + CARD_W + 20, top: Y.card1 + 14 + 132}} />
          </>}
          {t >= T.fly2 && <div style={abs({right: PAD, top: B2, ...fly(T.fly2, B2)})}><UserBubble text={PROMPT2} /></div>}
          {t >= T.dots2[0] && t < T.card2 && <div style={abs({left: PAD, top: CARD2})}><TypingDots t={t} a={T.dots2[0]} b={T.dots2[1]} /></div>}
          {t >= T.card2 && t < T.fly[0] && <div style={abs({left: PAD, top: CARD2})}><DocCard kind="invoice" t0={T.card2} t={t} total={684.4} /></div>}
          {t >= T.stock && t < T.fly[0] && (() => {
            const p = spring(t - T.stock, 16, .8);
            return <div style={abs({left: PAD + CARD_W + 18, top: CARD2 + Q_H.head + 18, opacity: clamp((t - T.stock) / .12), transform: `translateX(${lerp(-14, 0, p)}px)`, background: '#fff', border: `1px solid ${C.s200}`, borderRadius: 16, padding: '12px 16px', boxShadow: '0 10px 26px rgba(15,23,42,.10)'})}>
              <div style={F('I600', 11, {color: C.g600, letterSpacing: '.08em', textTransform: 'uppercase', display: 'flex', alignItems: 'center', gap: 6})}><Icon d={ICON.box} size={15} color={C.g600} /> Stock updated</div>
              <div style={F('I700', 19, {color: C.ink, marginTop: 6})}>2,500 → {Math.round(lerp(2500, 2490, out(prog(t, T.stock + .2, T.stock + .9)))).toLocaleString('en-IN')} kg</div>
              <div style={F('I400', 12, {color: C.s500, marginTop: 2})}>TMT Steel Rod 12mm</div>
            </div>;
          })()}
        </div>
      </div>
      <div style={abs({left: 0, right: 0, bottom: 0, height: COMPOSER, background: '#fff', borderTop: `1px solid ${C.s200}`})}>
        <Composer t={t} text={text} pressAt={[T.send1, T.send2]} typing={typing} />
      </div>
    </>
  );
}

// ─── dashboard view ──────────────────────────────────────────────────────────
const ROW_H = 64, LIST_TOP = 384, ROW_X = PAD, ROW_W = MAIN_W - 2 * PAD;
type Doc = {n: string; who: string; kind: string; amt: number; badge: 'Draft' | 'Unpaid' | 'Invoiced'; inv?: boolean};
const DOCS: Doc[] = [
  {n: 'Q-202611-003', who: 'Ramesh Traders', kind: 'Quotation', amt: 624, badge: 'Draft'},
  {n: 'Q-202611-002', who: 'Sri Salasar Insulations', kind: 'Quotation', amt: 8, badge: 'Draft'},
  {n: 'Q-202611-001', who: 'Ramesh Traders', kind: 'Quotation', amt: 580, badge: 'Draft'},
  {n: 'Q-202610-005', who: 'Ganesh Engineering Works', kind: 'Quotation', amt: 1160, badge: 'Draft'},
  {n: 'INV-202610-004', who: 'Ganesh Engineering Works', kind: 'Tax invoice', amt: 1368.8, badge: 'Unpaid', inv: true},
];
const NEW_DOC: Doc = {n: 'INV-202611-001', who: 'Ramesh Traders', kind: 'Tax invoice', amt: 684.4, badge: 'Unpaid', inv: true};

function DocRow({d, date, badge}: {d: Doc; date: string; badge?: Doc['badge']}) {
  return (
    <div style={{height: ROW_H, display: 'flex', alignItems: 'center', gap: 14, padding: '0 18px'}}>
      <span style={{width: 40, height: 40, borderRadius: 12, background: d.inv ? C.g50 : C.o50, display: 'flex', alignItems: 'center', justifyContent: 'center', flex: 'none'}}>
        <Icon d={d.inv ? ICON.receipt : ICON.file} size={20} color={d.inv ? C.g600 : C.o600} />
      </span>
      <div style={{flex: 1, minWidth: 0}}>
        <div style={{display: 'flex', alignItems: 'center', ...F('I600', 17, {color: C.ink})}}>{d.n}<Badge label={badge ?? d.badge} /></div>
        <div style={F('I400', 13, {color: C.s500, marginTop: 3})}>{d.who} · {d.kind} · {date}</div>
      </div>
      <div style={F('I700', 17, {color: C.ink})}>{inr(d.amt)}</div>
      <span style={{width: 36, height: 36, borderRadius: 10, border: `1px solid ${C.s200}`, display: 'flex', alignItems: 'center', justifyContent: 'center'}}><Icon d={ICON.download} size={18} color={C.s600} /></span>
    </div>
  );
}

function Swap({t, at, a, b, style}: {t: number; at: number; a: string; b: string; style: React.CSSProperties}) {
  const p = inOut(prog(t, at, at + .45));
  return <span style={{position: 'relative', display: 'inline-block', ...style}}>
    <span style={{opacity: 1 - p, display: 'inline-block', transform: `translateY(${-10 * p}px)`}}>{a}</span>
    <span style={abs({left: 0, top: 0, opacity: p, transform: `translateY(${10 * (1 - p)}px)`})}>{b}</span>
  </span>;
}

function DashboardView({t}: {t: number}) {
  const shift = ROW_H * inOut(prog(t, T.land - .45, T.land - .05));
  const statsAt = T.land + .25;
  const stats: [string, string, string, string, string, string][] = [
    ['Total sales', '₹5,886', '₹6,570', 'All invoices', 'All invoices', ICON.receipt],
    ['To collect', '₹5,886', '₹6,570', '6 unpaid invoices', '7 unpaid invoices', ICON.alert],
    ['Open quotations', '9', '8', '₹3,502 quoted', '₹2,922 quoted', ICON.file],
    ['Customers', '9', '9', '12 catalog items', '12 catalog items', ICON.users],
  ];
  const sw = (MAIN_W - 2 * PAD - 3 * 14) / 4;
  return (
    <div style={abs({inset: 0, background: C.s50})}>
      <div style={abs({left: PAD, top: 30, ...F('I500', 15, {color: C.s500})})}>Good morning</div>
      <div style={abs({left: PAD, top: 52, ...F('J700', 32, {color: C.ink, letterSpacing: '-.02em'})})}>Vaidya Industrial Supplies</div>
      {[['New quotation', ICON.file], ['New GST invoice', ICON.receipt], ['Check stock', ICON.box]].map(([l, d], i) => (
        <div key={l} style={abs({left: PAD + i * ((ROW_W - 28) / 3 + 14), top: 112, width: (ROW_W - 28) / 3, height: 64, background: '#fff', border: `1px solid ${C.s200}`, borderRadius: 16, display: 'flex', alignItems: 'center', gap: 12, padding: '0 14px', ...F('I600', 16, {color: C.ink})})}>
          <span style={{width: 38, height: 38, borderRadius: 11, background: C.o500, display: 'flex', alignItems: 'center', justifyContent: 'center'}}><Icon d={d} size={19} color="#fff" /></span>{l}
        </div>
      ))}
      {stats.map(([l, a, b, sa, sb, d], i) => (
        <div key={l} style={abs({left: PAD + i * (sw + 14), top: 196, width: sw, height: 116, background: '#fff', border: `1px solid ${C.s200}`, borderRadius: 16, padding: '14px 16px'})}>
          <div style={{display: 'flex', justifyContent: 'space-between', ...F('I500', 14, {color: C.s500})}}>{l}<Icon d={d} size={17} color={i === 1 ? '#dc2626' : i === 0 ? C.o600 : C.s500} /></div>
          <Swap t={t} at={statsAt + i * .08} a={a} b={b} style={F('I700', 26, {color: C.ink, marginTop: 14})} />
          <div style={{marginTop: 4}}><Swap t={t} at={statsAt + i * .08} a={sa} b={sb} style={F('I400', 12, {color: C.s500})} /></div>
        </div>
      ))}
      <div style={abs({left: PAD, top: 328, width: ROW_W, height: 56 + ROW_H * 6 + 4, background: '#fff', border: `1px solid ${C.s200}`, borderRadius: 18, overflow: 'hidden'})}>
        <div style={{height: 56, display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '0 18px', borderBottom: `1px solid ${C.s100}`, ...F('I600', 17, {color: C.ink})}}>
          Recent documents<span style={F('I600', 15, {color: C.o600})}>View all</span>
        </div>
        {DOCS.map((d, i) => (
          <div key={d.n} style={abs({left: 0, right: 0, top: 56 + i * ROW_H + shift, borderTop: i ? `1px solid ${C.s100}` : 'none'})}>
            <DocRow d={d} date={i < 3 ? '3 Nov 2026' : '1 Oct 2026'} badge={d.n === 'Q-202611-001' && t >= T.land + .45 ? 'Invoiced' : undefined} />
          </div>
        ))}
        {t >= T.land && <div style={abs({left: 0, right: 0, top: 56, background: lerp(1, 0, prog(t, T.land, T.land + 1.2)) > 0 ? `rgba(255,247,237,${lerp(1, 0, prog(t, T.land + .2, T.land + 1.4))})` : 'transparent'})}><DocRow d={NEW_DOC} date="3 Nov 2026" /></div>}
      </div>
    </div>
  );
}

// Invoice card travelling from the chat thread into the dashboard's first row.
function FlyingCard({t}: {t: number}) {
  if (t < T.fly[0] || t >= T.land + .02) return null;
  const p = inOut(prog(t, T.fly[0], T.fly[1]));
  const scroll = SCROLL_MAX;
  const from = {x: SIDE + PAD, y: HEAD + CARD2 - scroll, w: CARD_W, h: INV_H, r: 22};
  const to = {x: SIDE + PAD, y: LIST_TOP, w: ROW_W, h: ROW_H, r: 10};
  const g = (k: keyof typeof from) => lerp(from[k], to[k], p);
  const lift = Math.sin(p * Math.PI) * 18;
  return (
    <div style={abs({left: g('x'), top: g('y') - lift, width: g('w'), height: g('h'), borderRadius: g('r'), background: '#fff', overflow: 'hidden', border: `1px solid ${C.s200}`, boxShadow: `0 ${lerp(18, 6, p) + lift}px ${lerp(50, 16, p) + lift * 2}px rgba(15,23,42,${lerp(.12, .08, p)})`})}>
      <div style={abs({left: 0, top: 0, opacity: 1 - prog(p, .15, .55), transformOrigin: '0 0', transform: `scale(${lerp(1, .55, p)})`})}><DocCard kind="invoice" t0={-10} t={100} total={684.4} /></div>
      <div style={abs({left: 0, right: 0, top: 0, opacity: prog(p, .45, .85)})}><DocRow d={NEW_DOC} date="3 Nov 2026" /></div>
    </div>
  );
}

// ─── captions (left column) ──────────────────────────────────────────────────
function Caption({t, a, b, lines, sub, top = 380}: {t: number; a: number; b: number; lines: React.ReactNode[]; sub?: string; top?: number}) {
  if (t < a - .01 || t > b + .6) return null;
  const exit = inOut(prog(t, b, b + .45));
  return (
    <div style={abs({left: 120, top, width: 590})}>
      {lines.map((l, i) => {
        const p = spring(t - a - i * .14, 15, .86), v = clamp((t - a - i * .14) / .16);
        return <div key={i} style={{...F('J800', 70, {color: C.ink, lineHeight: 1.04, letterSpacing: '-.035em'}), opacity: v * (1 - exit), transform: `translateY(${lerp(26, 0, p) - exit * 18}px)`}}>{l}</div>;
      })}
      {sub && <div style={{...F('I400', 27, {color: C.s500, lineHeight: 1.4, marginTop: 24}), opacity: clamp((t - a - .45) / .3) * (1 - exit)}}>{sub}</div>}
    </div>
  );
}
const O = ({children}: {children: React.ReactNode}) => <span style={{color: C.o600}}>{children}</span>;

// ─── camera for the app window ───────────────────────────────────────────────
type Cam = {s: number; fx: number; fy: number; tx: number; ty: number};
const REST: Cam = {s: 1, fx: 960, fy: 540, tx: 960, ty: 540};
const winPt = (x: number, y: number) => ({x: WIN.x + x, y: WIN.y + y});
const threadFocus = winPt(SIDE + MAIN_W / 2, HEAD + 250);
const cardFocus = winPt(SIDE + (PAD + PAD + CARD_W + 20 + 190) / 2, HEAD + Y.card1 + 120);
const totalFocus = winPt(SIDE + PAD + CARD_W / 2, HEAD + CARD2 - SCROLL_MAX + Q_H.head + Q_H.line + I_TOT - 40);
const THREAD: Cam = {s: 1.1, fx: threadFocus.x, fy: threadFocus.y, tx: 1450, ty: 450};
const ZOOM: Cam = {s: 1.6, fx: cardFocus.x, fy: cardFocus.y, tx: 1010, ty: 430};
const TOT: Cam = {s: 1.22, fx: totalFocus.x, fy: totalFocus.y, tx: totalFocus.x - 60, ty: totalFocus.y - 40};
const mix = (a: Cam, b: Cam, p: number): Cam => ({s: lerp(a.s, b.s, p), fx: lerp(a.fx, b.fx, p), fy: lerp(a.fy, b.fy, p), tx: lerp(a.tx, b.tx, p), ty: lerp(a.ty, b.ty, p)});
// Hold each key until the next; ease between consecutive keys.
const CAM_KEYS: [number, Cam][] = [
  [0, REST], [8.0, REST], [9.5, THREAD], [T.zoomIn[0], THREAD], [T.zoomIn[1], ZOOM], [T.zoomOut[0], ZOOM], [T.zoomOut[1], REST],
  [T.pushTot[0], REST], [T.pushTot[1], TOT], [T.pullTot[0], TOT], [T.pullTot[1], REST],
];
// Phone plate: a portrait stage has no room for the whole window, so the camera follows the action.
const paneCam = (s: number, px: number, wy: number, ty: number): Cam => {
  const p = winPt(SIDE + px, wy);
  return {s, fx: p.x, fy: p.y, tx: STAGE.w / 2, ty};
};
const P_TYPE = paneCam(1.55, 380, WIN.h - COMPOSER + 56, 1100);
const P_BUBBLE = paneCam(1.28, MAIN_W / 2, HEAD + Y.bubble1 + 25, 260);
const P_CARD = paneCam(1.55, 348, HEAD + Y.card1 + 144, 520);
const P_CALLOUTS = paneCam(1.3, 431, HEAD + Y.card1 + 120, 440);
const P_DASH = paneCam(1.32, MAIN_W / 2, 480, 650);
const PHONE_KEYS: [number, Cam][] = [
  [0, P_TYPE], [8.1, P_TYPE], [9.0, P_BUBBLE], [9.8, P_BUBBLE], [10.7, P_CARD], [T.zoomIn[0], P_CARD], [T.zoomIn[1], P_CALLOUTS],
  [30, P_CALLOUTS], [31, P_DASH], [99, P_DASH],
];
function camera(t: number): Cam {
  const keys = PLATE === 'phone' ? PHONE_KEYS : CAM_KEYS;
  for (let i = 1; i < keys.length; i++) {
    const [t1, c1] = keys[i], [t0, c0] = keys[i - 1];
    if (t < t1) return mix(c0, c1, inOut(prog(t, t0, t1)));
  }
  return REST;
}

// ─── frame ───────────────────────────────────────────────────────────────────
export default function Frame({frame}: {frame: number}) {
  const t = secondsAt(film, PLATE === 'none' ? frame : plateSource(frame));
  const cam = camera(t);

  // S01 hook
  const hookOut = inOut(prog(t, 4.0, 4.6));
  const word = (w: string, a: number, b: number) => {
    const pin = spring(t - a, 17, .8), pout = inOut(prog(t, b, b + .3));
    return <span key={w} style={abs({left: 0, right: 0, textAlign: 'center', opacity: clamp((t - a) / .12) * (1 - pout), transform: `translateY(${lerp(70, 0, pin) - pout * 60}px)`})}>{w}</span>;
  };

  // window entrance / exit
  const winIn = spring(t - T.winIn, 11, .9);
  const winOut = inOut(prog(t, T.out[0], T.out[1]));
  const dash = inOut(prog(t, T.toDash + .45, T.toDash + .8));

  // end card
  const lt = t - T.logo;
  const mk = spring(lt, 12, .62);

  return (
    <div style={{width: STAGE.w, height: STAGE.h, position: 'relative', overflow: 'hidden', background: 'linear-gradient(160deg,#ffffff 0%,#fff7ed 45%,#ffedd5 100%)'}}>
      <div style={abs({left: 1080 + Math.sin(t * .35) * 60, top: -260 + Math.cos(t * .3) * 40, width: 1200, height: 1200, borderRadius: '50%', background: 'radial-gradient(circle, rgba(249,115,22,.16), rgba(249,115,22,0) 64%)'})} />
      <div style={abs({left: -380, top: 620, width: 900, height: 900, borderRadius: '50%', background: 'radial-gradient(circle, rgba(251,146,60,.12), rgba(251,146,60,0) 64%)'})} />

      {/* S01 hook */}
      {t < 4.7 && (
        <div style={abs({left: 0, right: 0, top: 395, opacity: 1 - hookOut, transform: `translateY(${-90 * hookOut}px) scale(${lerp(1, .96, hookOut)})`})}>
          <div style={{textAlign: 'center', ...F('J800', 118, {color: C.ink, letterSpacing: '-.045em', lineHeight: 1})}}>
            {['Every order', 'needs a'].map((g, i) => {
              const p = spring(t - .2 - i * .32, 15, .85);
              return <span key={g} style={{display: 'inline-block', marginRight: i ? 0 : 34, opacity: clamp((t - .2 - i * .32) / .14), transform: `translateY(${lerp(40, 0, p)}px)`}}>{g}</span>;
            })}
          </div>
          <div style={{position: 'relative', height: 150, marginTop: 14, overflow: 'hidden', ...F('J800', 128, {color: C.o600, letterSpacing: '-.045em', lineHeight: 1.12})}}>
            {word('quotation.', .95, 1.95)}
            {word('GST invoice.', 2.0, 2.95)}
            {word('PDF.', 3.0, 99)}
          </div>
        </div>
      )}

      {/* app window under the camera */}
      {t >= T.winIn - .05 && t < T.out[1] + .05 && (
        <div style={abs({inset: 0, transformOrigin: '0 0', transform: `translate(${cam.tx - cam.fx * cam.s}px, ${cam.ty - cam.fy * cam.s}px) scale(${cam.s})`})}>
          <div style={abs({left: WIN.x, top: WIN.y, width: WIN.w, height: WIN.h, borderRadius: 28, overflow: 'hidden', background: '#fff',
            boxShadow: '0 40px 100px rgba(124,45,18,.16), 0 0 0 1px rgba(15,23,42,.06)',
            opacity: clamp((t - T.winIn) / .2) * (1 - winOut),
            transform: `translateY(${lerp(140, 0, winIn) + winOut * 30}px) scale(${lerp(.96, 1, winIn) - winOut * .06})`,
            filter: winOut > 0 ? `blur(${winOut * 10}px)` : 'none'})}>
            <Sidebar t={t} />
            <div style={abs({left: SIDE, top: 0, width: MAIN_W, height: WIN.h, overflow: 'hidden'})}>
              <div style={abs({inset: 0, opacity: 1 - dash})}><AssistantView t={t} /></div>
              {dash > 0 && <div style={abs({inset: 0, opacity: dash, transform: `translateY(${lerp(16, 0, dash)}px)`})}><DashboardView t={t} /></div>}
            </div>
            <FlyingCard t={t} />
          </div>
        </div>
      )}

      {/* captions (plates leave these to the page's live text) */}
      {PLATE === 'none' && <>
      <Caption t={t} a={T.cap1} b={14.55} lines={['Type it the way', <>you'd <O>say it.</O></>]} sub="English or Hinglish. Munim turns your message into a GST-ready quotation." />
      {t > 15.2 && t < 20.6 && (() => {
        const v = out(prog(t, 15.55, 15.95)) * (1 - inOut(prog(t, 19.55, 19.95)));
        return <div style={abs({left: 120, top: 806, padding: '26px 34px', borderRadius: 26, background: 'rgba(255,255,255,.86)', boxShadow: '0 20px 60px rgba(15,23,42,.14)', border: '1px solid rgba(255,255,255,.9)', opacity: v, transform: `translateY(${lerp(24, 0, v)}px)`})}>
          <div style={F('J800', 44, {color: C.ink, letterSpacing: '-.03em'})}>Prices, GST and stock come from <O>your catalog.</O></div>
          <div style={F('I500', 24, {color: C.s500, marginTop: 8})}>Nothing is guessed.</div>
        </div>;
      })()}
      <Caption t={t} a={T.cap3} b={31.2} lines={['One message.', <O key="g">GST invoice.</O>]} sub="CGST and SGST worked out exactly, and stock updated in the same step." />
      <Caption t={t} a={T.toDash + .6} b={37.75} lines={['Every document,', <O key="p">in one place.</O>]} sub="Quotations, invoices and what's left to collect, on one dashboard." />
      </>}

      {/* S06 end card */}
      {t >= T.logo - .05 && (
        <div style={abs({inset: 0, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center'})}>
          <div style={{opacity: clamp(lt / .18), transform: `translateY(${lerp(30, 0, mk)}px) scale(${lerp(.6, 1, mk)})`}}><Mark w={250} /></div>
          <div style={{marginTop: 34, ...F('J800', 112, {color: C.ink, letterSpacing: '-.045em', lineHeight: 1}), opacity: clamp((lt - .35) / .2), transform: `translateY(${lerp(24, 0, spring(lt - .35, 14, .86))}px)`}}>
            Munim<span style={{color: C.o600}}>.ai</span>
          </div>
          <div style={{marginTop: 28, ...F('I500', 34, {color: C.s600}), opacity: clamp((lt - .85) / .3), transform: `translateY(${lerp(14, 0, out(prog(lt, .85, 1.3)))}px)`}}>
            Quotations and GST invoices from <span style={{color: C.o600, fontFamily: 'I600, sans-serif'}}>one message.</span>
          </div>
        </div>
      )}
    </div>
  );
}

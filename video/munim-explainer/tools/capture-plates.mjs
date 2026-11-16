// Captures the text-free footage the landing page scrubs, as lossless PNGs at high pixel density.
// There is no video step: landing/build-assets.sh encodes each frame once from these PNGs.
// film.tsx itself is never changed: each variant runs in a throwaway copy under .lvm/plates.
//
//   node tools/capture-plates.mjs                 capture wide and phone
//   node tools/capture-plates.mjs --only phone    just one variant
import {copyFileSync, cpSync, existsSync, mkdirSync, readFileSync, rmSync, symlinkSync, writeFileSync} from 'node:fs';
import {join, resolve} from 'node:path';
import {pathToFileURL} from 'node:url';
import {chromium} from 'playwright';

const root = resolve(import.meta.dirname, '..');
const {startServer} = await import(pathToFileURL(join(root, 'node_modules/@launch-video-maker/runtime/runtime/dist/server.js')));

const LINE = "const PLATE = 'none' as";
const source = readFileSync(join(root, 'film.tsx'), 'utf8');
if (!source.includes(LINE)) throw new Error('PLATE line not found in film.tsx');

// Plate frames 0-458 are the quotation and catalog; 459-668 are the dashboard. Every second frame is 15 fps.
const RANGES = {a: [0, 458], b: [459, 668]};
const STEP = 2;
// Stage is 1920x1080 (wide) or 1080x1200 (phone), so these give 2560x1440 and 1296x1440.
const DENSITY = {wide: 4 / 3, phone: 1.2};

const onlyAt = process.argv.indexOf('--only');
const variants = onlyAt > -1 ? [process.argv[onlyAt + 1]] : ['wide', 'phone'];

for (const variant of variants) {
  const dir = join(root, '.lvm', 'plates', variant);
  mkdirSync(join(dir, '.lvm'), {recursive: true});
  if (!existsSync(join(dir, 'node_modules'))) symlinkSync(join(root, 'node_modules'), join(dir, 'node_modules'), 'junction');
  // The renderer refuses linked project folders, so these are real copies.
  for (const shared of ['assets', 'vendor', 'brand-kit']) cpSync(join(root, shared), join(dir, shared), {recursive: true});
  copyFileSync(join(root, 'package.json'), join(dir, 'package.json'));
  copyFileSync(join(root, '.lvm', 'tools.json'), join(dir, '.lvm', 'tools.json'));
  writeFileSync(join(dir, 'film.tsx'), source.replace(LINE, `const PLATE = '${variant}' as`));

  const server = await startServer(dir);
  const {film, version} = server.prepared;
  const browser = await chromium.launch({headless: true, args: ['--force-color-profile=srgb']});
  const page = await browser.newPage({viewport: {width: film.width, height: film.height}, deviceScaleFactor: DENSITY[variant]});
  await page.goto(server.url + '/?capture');
  await page.waitForFunction(() => Boolean(window.__LVM__?.ready || window.__LVM__?.error), {}, {timeout: 60000});
  const failure = await page.evaluate(() => window.__LVM__.error);
  if (failure) throw new Error(failure);

  let requestId = 0;
  for (const [name, [first, last]] of Object.entries(RANGES)) {
    const out = join(root, 'exports', 'plates', variant, name);
    rmSync(out, {recursive: true, force: true});
    mkdirSync(out, {recursive: true});
    let n = 0;
    for (let frame = first; frame <= last; frame += STEP) {
      const ready = await page.evaluate(({frame, version, requestId}) => window.__LVM__.acquire(frame, version, requestId), {frame, version, requestId: ++requestId});
      if (ready.frame !== frame) throw new Error(`Frame mismatch at ${frame}`);
      await page.locator('#stage').screenshot({type: 'png', animations: 'allow', path: join(out, `f${String(++n).padStart(3, '0')}.png`)});
      await page.evaluate(() => window.__LVM__.release());
    }
    console.log(`[plates] ${variant}-${name}: ${n} frames`);
  }
  await browser.close();
  await server.close?.();
}
process.exit(0);

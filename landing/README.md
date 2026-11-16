# Munim landing page

`site/` is the page. It is plain HTML, CSS and JS with no build step, so any static host can serve that folder as is. `moodboard/` is the design reference and should not be deployed.

## Run it locally

```bash
python -m http.server 5510 --directory landing/site
```

## Before launch

Create a form on a form service that accepts JSON (for example Formspree), then paste its submission URL into `data-endpoint` on `#accessForm` in `site/index.html`. Until then the form validates but tells visitors requests aren't open, because nothing receives them. It sends `POST {"email": "...", "business": "..."}` as JSON with `Accept: application/json`, and treats any 2xx response as success.

## Rebuilding the footage

The page scrubs text-free footage captured from `video/munim-explainer/film.tsx`. Headlines are live text in the page. Frames go straight from lossless PNG to WebP with no video step, which keeps interface text sharp.

```bash
cd video/munim-explainer
node tools/capture-plates.mjs
cd ../..
bash landing/build-assets.sh
```

There are three sets: `hd` (2560 px) for sharp desktop screens, `wide` (1920 px) for standard ones, and `phone` (1080 px). Each has sequence `a` (quotation and catalog, 5.5 to 20.8 s of the film) and `b` (dashboard, 31 to 38 s), at 15 frames per second. `COUNTS` in `site/main.js` must match the frame counts.

## Deploying

The page is its own Vercel project, separate from the app and API:

```bash
npx vercel deploy landing/site --prod
```

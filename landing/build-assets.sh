#!/usr/bin/env bash
# Builds site/assets from the lossless captures (video/munim-explainer/tools/capture-plates.mjs)
# and the finished film. Run from the repo root.
set -euo pipefail

PLATES=video/munim-explainer/exports/plates
FILM=video/munim-explainer/exports/munim-explainer-45s-final.mp4
OUT=landing/site/assets
Q="${Q:-84}"

rm -rf "$OUT/frames"
mkdir -p "$OUT"/frames/{hd-a,hd-b,wide-a,wide-b,phone-a,phone-b}

encode() { # source plate/range, output dir, scale filter
  ffmpeg -v error -y -i "$PLATES/$1/f%03d.png" -vf "$3" -c:v libwebp -preset text -q:v "$Q" -compression_level 5 "$OUT/frames/$2/f%03d.webp"
}
encode wide/a  hd-a    "scale=2560:-2"
encode wide/b  hd-b    "scale=2560:-2"
encode wide/a  wide-a  "scale=1920:-2:flags=lanczos"
encode wide/b  wide-b  "scale=1920:-2:flags=lanczos"
encode phone/a phone-a "scale=1080:-2:flags=lanczos"
encode phone/b phone-b "scale=1080:-2:flags=lanczos"

# Hero and share image: the app window at 12 s, cropped clear of the empty caption column.
HERO="$PLATES/wide/a/f099.png"
ffmpeg -v error -y -i "$HERO" -vf "crop=1600:1027:940:60" -frames:v 1 -update 1 -c:v libwebp -preset text -q:v 88 "$OUT/hero.webp"
ffmpeg -v error -y -i "$HERO" -vf "crop=1600:840:940:60,scale=1200:-2:flags=lanczos" -frames:v 1 -update 1 -q:v 3 "$OUT/og.jpg"

# Full film for the Watch demo dialog, with its opening frame as poster.
rm -f "$OUT/munim-film.mp4"
cp "$FILM" "$OUT/munim-demo.mp4"
ffmpeg -v error -y -ss 2.5 -i "$FILM" -frames:v 1 -update 1 -vf "scale=1280:-2" -c:v libwebp -q:v 72 "$OUT/film-poster.webp"

cp video/munim-explainer/assets/brand/munim-mark.png "$OUT/munim-mark.png"

for d in "$OUT"/frames/*; do echo "$d: $(ls "$d" | wc -l) frames, $(du -sh "$d" | cut -f1)"; done
du -sh "$OUT"

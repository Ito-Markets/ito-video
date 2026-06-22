#!/bin/bash
# Contact-sheet generator for ItoMarkets brand film.
# Robust: probes duration, -nostdin so ffmpeg never eats the caller's stdin.
cd "$(dirname "$0")" || exit 1
OUT="sheets"
mkdir -p "$OUT"

for f in "$@"; do
  [ -f "$f" ] || { echo "MISSING $f"; continue; }
  base="$(basename "${f%.*}")"
  dur=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$f" 2>/dev/null)
  [ -z "$dur" ] && { echo "NODUR $f"; continue; }
  N=$(awk -v d="$dur" 'BEGIN{n=int(d*2.5+0.5); if(n<12)n=12; if(n>48)n=48; print n}')
  rate=$(awk -v n="$N" -v d="$dur" 'BEGIN{printf "%.5f", n/d}')
  rows=$(awk -v n="$N" 'BEGIN{print int((n+5)/6)}')
  ffmpeg -nostdin -y -loglevel error -i "$f" \
    -vf "fps=${rate},scale=300:-1,tile=6x${rows}" -frames:v 1 -update 1 \
    "$OUT/${base}.jpg" </dev/null 2>/dev/null
  if [ -f "$OUT/${base}.jpg" ]; then
    printf "OK   %-38s dur=%6.2fs  N=%-3s grid=6x%s\n" "$base" "$dur" "$N" "$rows"
  else
    printf "FAIL %-38s\n" "$base"
  fi
done

#!/bin/sh
# Render images/og_card.jpg (1200x630) from tools/og/card.html. Needs the site served locally:
#   python3 -m http.server 8137   (in the repo root)
set -e
cd "$(dirname "$0")/../.."
out=$(mktemp --suffix=.png)
google-chrome --headless=new --use-angle=swiftshader --enable-unsafe-swiftshader \
  --hide-scrollbars --window-size=1200,630 --virtual-time-budget=${WAIT_MS:-15000} \
  --screenshot="$out" "http://localhost:${PORT:-8137}/tools/og/card.html"
python3 -c "import sys; from PIL import Image; Image.open(sys.argv[1]).convert('RGB').save('images/og_card.jpg', quality=88, optimize=True)" "$out"
rm -f "$out"
echo images/og_card.jpg

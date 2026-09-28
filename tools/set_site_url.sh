#!/bin/sh
# Fill in the absolute site URL used by the link-preview (Open Graph) tags, e.g.
#   tools/set_site_url.sh https://username.github.io
set -e
[ -n "$1" ] || { echo "usage: $0 https://your.site" >&2; exit 1; }
cd "$(dirname "$0")/.."
url=${1%/}
grep -rl --include='*.html' 'https://SITE_URL' . | xargs sed -i "s|https://SITE_URL|$url|g"
grep -rn --include='*.html' 'SITE_URL' . || echo "done: $url"

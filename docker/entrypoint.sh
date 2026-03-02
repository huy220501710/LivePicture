#!/bin/sh
set -e

MEDIA_NOTAUTH="/fastapi/media/notauth"
ASSETS_NOTAUTH="/fastapi/assets/notauth"

mkdir -p "$MEDIA_NOTAUTH"

if [ -d "$ASSETS_NOTAUTH" ]; then
  for file in "$ASSETS_NOTAUTH"/*; do
    name=$(basename "$file")
    if [ ! -f "$MEDIA_NOTAUTH/$name" ]; then
      cp "$file" "$MEDIA_NOTAUTH/$name"
    fi
  done
fi

exec "$@"

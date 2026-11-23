#!/bin/bash
# Clear Gatekeeper quarantine and launch Image Labeler 2D.
cd "$(dirname "$0")"
xattr -cr . 2>/dev/null || true
chmod +x ./ImageLabeler2D 2>/dev/null || true
exec ./ImageLabeler2D "$@"

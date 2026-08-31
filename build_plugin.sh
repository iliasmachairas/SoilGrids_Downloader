#!/usr/bin/env bash
#
# build_plugin.sh — package the SoilGrids Downloader QGIS plugin into a clean
# ZIP, commit + push the source to git, and drop the ZIP in your Downloads
# folder ready to upload at https://plugins.qgis.org/plugins/add/
#
# Usage:
#   ./build_plugin.sh            # build zip + git commit/push
#   ./build_plugin.sh --no-git   # just build the zip, skip all git steps
#
set -euo pipefail

# --- locate ourselves (works no matter where it's called from) ---
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

PLUGIN_DIR_NAME="$(basename "$SCRIPT_DIR")"          # e.g. SoilGrids_Downloader
VERSION="$(grep -E '^version=' metadata.txt | head -1 | cut -d= -f2 | tr -d '[:space:]')"
ZIP_NAME="SoilGrids-Downloader-${VERSION}.zip"
DEST_DIR="${HOME}/Downloads"
DEST_ZIP="${DEST_DIR}/${ZIP_NAME}"

DO_GIT=1
[ "${1:-}" = "--no-git" ] && DO_GIT=0

echo ">> Plugin : ${PLUGIN_DIR_NAME}"
echo ">> Version: ${VERSION}"
echo ">> Output : ${DEST_ZIP}"
echo

# --- 1. build a clean ZIP via a throwaway staging copy ---
# Files/dirs never shipped to end users (kept in sync with .gitignore).
# "test" is dev-only (run via plain pytest per the README) — also keeps the
# QGIS plugin repo's Bandit scan from flagging every `assert` in the test
# files as B101. build_plugin.sh itself is excluded too: it's a dev-only
# packaging tool, never run by QGIS, and a .sh file inside the plugin trips
# the plugin repo's "suspicious file type" scan (which also flags hidden
# files, hence .gitignore below — it's dev-only and QGIS never reads it at
# runtime). source/ and .readthedocs.yaml are the Sphinx/Read the Docs
# source — built and hosted separately at readthedocs.org, not needed inside
# QGIS. help/ is the unused Plugin Builder Sphinx scaffold, superseded by
# source/. scripts/ is dev-only tooling (translation compile/update helpers)
# and, like build_plugin.sh, made entirely of .sh files that trip the same
# scanner. build/ is generated Sphinx HTML output, never committed for the
# same reason. Root make.bat/Makefile are Plugin Builder's dev-only
# compile/deploy/package helpers (and drive the Sphinx build) — QGIS never
# reads them at runtime, and the .bat trips the same "suspicious file type"
# scan.
EXCLUDES=(
    "__pycache__" "*.pyc" ".git" ".gitignore" ".claude" "CLAUDE.md" "*.zip"
    "build" "dist" ".pytest_cache" "test" "build_plugin.sh" "source" ".readthedocs.yaml"
    "help" "scripts" "test_point_shp" "make.bat" "Makefile" "symbology-style.db"
)

STAGE="$(mktemp -d)"
trap 'rm -rf "$STAGE"' EXIT

cp -r "$SCRIPT_DIR" "$STAGE/$PLUGIN_DIR_NAME"

pushd "$STAGE/$PLUGIN_DIR_NAME" >/dev/null
for pat in "${EXCLUDES[@]}"; do
  find . -name "$pat" -exec rm -rf {} + 2>/dev/null || true
done
# pyrcc5 always regenerates resources.py with `from PyQt5 import QtCore`, which
# breaks under Qt6-based QGIS builds — patch it here so a forgotten manual fix
# after recompiling never ships in a release.
if [ -f resources.py ]; then
  sed -i 's/^from PyQt5 import QtCore$/from qgis.PyQt import QtCore/' resources.py
fi
popd >/dev/null

mkdir -p "$DEST_DIR"
rm -f "$DEST_ZIP"

pushd "$STAGE" >/dev/null
if command -v zip >/dev/null 2>&1; then
  zip -r -q "$DEST_ZIP" "$PLUGIN_DIR_NAME"
elif command -v python3 >/dev/null 2>&1 || command -v python >/dev/null 2>&1; then
  # Fallback: Python's zipfile, which always writes forward-slash entry
  # names. PowerShell's Compress-Archive stores backslashes in nested
  # entry names on Windows, which fails the QGIS plugin repo's strict
  # ZIP-spec validation ("cannot contain backslashes in file names").
  PY="$(command -v python3 || command -v python)"
  "$PY" -c '
import os, sys, zipfile
root, dest = sys.argv[1], sys.argv[2]
with zipfile.ZipFile(dest, "w", zipfile.ZIP_DEFLATED) as zf:
    for dirpath, _, filenames in os.walk(root):
        for name in filenames:
            full = os.path.join(dirpath, name)
            arcname = os.path.relpath(full, os.path.dirname(root)).replace(os.sep, "/")
            zf.write(full, arcname)
' "$PLUGIN_DIR_NAME" "$DEST_ZIP"
else
  # Last resort: PowerShell's Compress-Archive on Windows. Known to emit
  # backslashes in nested entry names, which the QGIS plugin repo rejects —
  # only used if neither zip nor python is available.
  powershell.exe -NoProfile -Command \
    "Compress-Archive -Path '${PLUGIN_DIR_NAME}' -DestinationPath '$(cygpath -w "$DEST_ZIP")' -Force"
fi
popd >/dev/null

echo ">> ZIP built: ${DEST_ZIP}"
echo ">> Contents:"
if command -v unzip >/dev/null 2>&1; then
  unzip -l "$DEST_ZIP" | sed 's/^/     /'
fi
echo

# --- 2. git commit + push ---
if [ "$DO_GIT" -eq 1 ]; then
  if [ ! -d .git ]; then
    echo ">> No git repo yet — initialising."
    git init -b main
  fi

  git add -A
  if git diff --cached --quiet; then
    echo ">> Nothing new to commit."
  else
    git commit -m "Release ${VERSION}"
    echo ">> Committed release ${VERSION}."
  fi

  if git remote get-url origin >/dev/null 2>&1; then
    echo ">> Pushing to origin..."
    git push -u origin HEAD
    echo ">> Pushed."
  else
    echo
    echo ">> No 'origin' remote set. Repo: https://github.com/iliasmachairas/SoilGrids_Downloader"
    echo "   Run:"
    echo "     git remote add origin https://github.com/iliasmachairas/SoilGrids_Downloader.git"
    echo "     git push -u origin main"
  fi
else
  echo ">> --no-git: skipped all git steps."
fi

echo
echo ">> DONE. Upload this file at https://plugins.qgis.org/plugins/add/ :"
echo "     ${DEST_ZIP}"

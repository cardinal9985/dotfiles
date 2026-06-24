#!/usr/bin/env bash
# One-shot: move every album from /mnt/storage/media/music back into the
# refinery inbox so it gets fresh tags / cover / spectrogram / lyrics via
# the normal approval flow.
#
# This nukes Navidrome's per-track play counts + ratings (state is keyed
# on file path; refinery rewrites names). Stats DB indexes by MBID so its
# listen history survives.
#
# Installed as a system binary on ishimura. Run:
#   ssh -p 36475 maxwell@ishimura sudo refinery-reprocess-library

set -euo pipefail

SRC="/mnt/storage/media/music"
DST="/mnt/storage/downloads/slskd/complete"

[ "$EUID" -eq 0 ] || { echo "run with sudo"; exit 1; }
[ -d "$SRC" ]    || { echo "SRC missing: $SRC"; exit 1; }
[ -d "$DST" ]    || { echo "DST missing: $DST"; exit 1; }

mapfile -d '' -t albums < <(find "$SRC" -mindepth 2 -maxdepth 2 -type d -print0)
count=${#albums[@]}
[ "$count" -gt 0 ] || { echo "Nothing to move under $SRC"; exit 0; }

echo "Found $count album folder(s) under $SRC."
echo "Each will be moved to $DST as: '<Artist> - <Album>/'"
echo "Services ishimura-refinery + podman-slskd will be stopped during the move."
echo -n "Continue? [y/N]: "
read -r ans
[ "$ans" = "y" ] || { echo "aborted"; exit 0; }

# Stop refinery (so it doesn't scan mid-move) and slskd (so it doesn't write
# into the inbox while we're moving). Use || true so a missing unit doesn't
# abort under `set -e` - slskd in particular runs as a podman unit on
# ishimura, but might not exist on other hosts.
echo ">>> Stopping ishimura-refinery + podman-slskd"
systemctl stop ishimura-refinery.service || true
systemctl stop podman-slskd.service      || true

moved=0
skipped=0
for album_dir in "${albums[@]}"; do
    rel="${album_dir#$SRC/}"          # "Mazzy Star/1996 - Among My Swan"
    artist="${rel%%/*}"
    album="${rel#*/}"
    target="$DST/$artist - $album"

    if [ -e "$target" ]; then
        echo "SKIP (dest exists): $target"
        skipped=$((skipped+1))
        continue
    fi
    mv "$album_dir" "$target"
    moved=$((moved+1))
    if [ $((moved % 25)) -eq 0 ]; then
        echo "... moved $moved / $count"
    fi
done

# Remove now-empty artist directories
find "$SRC" -mindepth 1 -maxdepth 1 -type d -empty -delete

# Refinery's ACL service ensures the moved files get u:refinery:rwx via the
# default ACL on /downloads/slskd, but already-moved files inherit only at
# mkdir time. Re-apply the ACL so existing files become writable too.
if command -v setfacl >/dev/null; then
    echo ">>> Re-applying ACL on $DST so refinery can rewrite tags + move out"
    setfacl -R    -m u:refinery:rwx,m::rwx "$DST"
    setfacl -d -R -m u:refinery:rwx,m::rwx "$DST"
fi

echo ">>> Starting ishimura-refinery (podman-slskd stays off until you say so)"
systemctl start ishimura-refinery.service

cat <<EOF

DONE. Moved=$moved skipped=$skipped (count=$count).
Watch progress:
  ssh ishimura sudo journalctl -u ishimura-refinery -f

Then in the refinery UI:
  - Hit SCAN NOW (or wait <60s for the periodic scan)
  - Items roll into PENDING APPROVAL as workers chew through (~30-90s each)
  - For most lossless rips: APPROVE ALL VERIFIED handles the bulk
  - Review any non-VERIFIED ones manually

When you're done re-importing, bring slskd back:
  ssh ishimura sudo systemctl start podman-slskd.service

If anything goes wrong mid-move, the source folders are still present at
$SRC for whatever didn't move, and the moved folders are intact at
$DST. Re-run this script - it skips dests that already exist.
EOF

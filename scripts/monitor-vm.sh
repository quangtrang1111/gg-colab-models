#!/usr/bin/env bash
# Poll the Colab server log once a minute; emit only when it changes.
# Each poll also counts as kernel activity, keeping the Colab session alive.
export PATH="$HOME/.local/bin:$PATH"
export LD_LIBRARY_PATH="$HOME/.nix-profile/lib:$LD_LIBRARY_PATH"
export PYTHONUNBUFFERED=1
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
last=""
while true; do
  out=$(colab --auth oauth2 exec -s qwen -f "$HERE/vm-tail.py" < /dev/null 2>&1 \
        | tr '\r' '\n' | grep -vE '^[[:space:]]*$' | tail -2)
  if [ -n "$out" ] && [ "$out" != "$last" ]; then
    echo "$out"
    last="$out"
  fi
  case "$out" in
    *"serving on :8000"*) echo "SERVER READY"; break;;
    *Traceback*) echo "SERVER ERROR - stopping monitor"; break;;
  esac
  sleep 60
done
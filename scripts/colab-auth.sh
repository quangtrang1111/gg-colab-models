#!/usr/bin/env bash
export PATH="$HOME/.local/bin:$PATH"
export LD_LIBRARY_PATH="$HOME/.nix-profile/lib:$LD_LIBRARY_PATH"
export PYTHONUNBUFFERED=1
rm -f /tmp/cfifo /tmp/colab_auth.log
mkfifo /tmp/cfifo
( sleep 3600 > /tmp/cfifo & )
colab --auth oauth2 sessions < /tmp/cfifo > /tmp/colab_auth.log 2>&1
echo "colab auth exited: $?"
tail -5 /tmp/colab_auth.log
#!/usr/bin/env bash
# Run inside WSL: provision a T4 Colab VM and show its status.
# For the full deployment (build + serve + tunnel + keep-alive) run scripts/restorer.py.
set -e
export PATH="$HOME/.local/bin:$PATH"
export LD_LIBRARY_PATH="$HOME/.nix-profile/lib:$LD_LIBRARY_PATH"
export PYTHONUNBUFFERED=1

colab --auth oauth2 new -s qwen --gpu T4 < /dev/null
colab --auth oauth2 status -s qwen < /dev/null
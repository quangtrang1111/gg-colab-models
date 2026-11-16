#!/usr/bin/env bash
# Headless Windows colab OAuth: hold a FIFO open so colab waits for the code.
export PYTHONUNBUFFERED=1
rm -f /tmp/cfifo_win
mkfifo /tmp/cfifo_win
( sleep 7200 > /tmp/cfifo_win & )
colab --auth oauth2 sessions < /tmp/cfifo_win > /tmp/colab_auth_win.log 2>&1
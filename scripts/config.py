"""Shared configuration for the LOCAL test scripts.

These scripts run on your machine and talk to the llama-server either through the
Colab tunnel or directly on the VM. Everything is resolved at import time and can
be overridden with environment variables:

  TUNNEL_URL              base URL of the server
                          (default: the live baseURL in Command Code's providers.json,
                           falling back to http://127.0.0.1:8000)
  MODEL                   model id served by llama-server
  COMMAND_CODE_PROVIDERS  path to Command Code's providers.json
"""
import glob
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(HERE)

DEFAULT_MODEL = "qwen3-coder-30b"
DEFAULT_URL = "http://127.0.0.1:8000"
PROVIDERS_KEY = "colab-t4"


def providers_path():
    """Locate Command Code's providers.json without hardcoding a username."""
    override = os.environ.get("COMMAND_CODE_PROVIDERS")
    if override:
        return override
    home = os.path.expanduser("~/.commandcode/providers.json")
    if os.path.exists(home):
        return home
    # WSL: the Windows home lives under /mnt/c/Users/<name>/
    for candidate in sorted(glob.glob("/mnt/c/Users/*/.commandcode/providers.json")):
        return candidate
    return home


def _url_from_providers():
    try:
        with open(providers_path(), encoding="utf-8") as fh:
            data = json.load(fh)
        return data["provider"][PROVIDERS_KEY]["baseURL"]
    except Exception:
        return None


def _model_from_providers():
    try:
        with open(providers_path(), encoding="utf-8") as fh:
            data = json.load(fh)
        models = data["provider"][PROVIDERS_KEY]["models"]
        return next(iter(models))
    except Exception:
        return None


TUNNEL_URL = (os.environ.get("TUNNEL_URL")
              or _url_from_providers()
              or DEFAULT_URL).rstrip("/")
MODEL = os.environ.get("MODEL") or _model_from_providers() or DEFAULT_MODEL
CHAT_URL = f"{TUNNEL_URL}/v1/chat/completions"

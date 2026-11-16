"""Client config locations for OpenAI-compatible clients.

The Colab quick tunnel gets a new random URL on every redeploy, so any client
config pointing at it must be rewritten. This module knows where the common
clients keep their base URL and rewrites the ones that exist on disk.

Command Code is the primary, tested target; the others are best-effort. Point
at your own config with the CLIENT_CONFIGS environment variable (os.pathsep
separated list of paths or globs).
"""
import glob
import os
import re

TUNNEL_RE = re.compile(r"https://[a-z0-9-]+\.trycloudflare\.com")

PATTERNS = [
    # Command Code (BYOK provider config)
    "~/.commandcode/providers.json",
    # Continue (IDE assistant)
    "~/.continue/config.json",
    # Aider
    "~/.aider.conf.yml",
    # LiteLLM proxy
    "~/.config/litellm/config.yaml",
    # Cursor (MCP servers)
    "~/.cursor/mcp.json",
    # Windsurf
    "~/.codeium/windsurf/mcp_config.json",
    # Open WebUI
    "~/.config/open-webui/config.json",
    # VS Code extensions that host OpenAI-compatible endpoints (Cline, Roo, ...)
    "~/AppData/Roaming/Code/User/globalStorage/*/settings/*.json",
    # Windows home reached from WSL
    "/mnt/c/Users/*/.commandcode/providers.json",
    "/mnt/c/Users/*/.continue/config.json",
    "/mnt/c/Users/*/.aider.conf.yml",
]


def _expand(patterns):
    for pattern in patterns:
        for path in glob.glob(os.path.expanduser(pattern)):
            if os.path.isfile(path):
                yield path


def candidates():
    """Known client config files that exist on this machine, de-duplicated."""
    found = []

    def add(paths):
        for path in paths:
            if path not in found:
                found.append(path)

    add(_expand(PATTERNS))
    for extra in (os.environ.get("CLIENT_CONFIGS") or "").split(os.pathsep):
        extra = extra.strip()
        if extra:
            add(_expand([extra]))
    return found


def read_url():
    """First tunnel URL found in any known client config, or None."""
    for path in candidates():
        try:
            with open(path, encoding="utf-8", errors="replace") as fh:
                match = TUNNEL_RE.search(fh.read())
        except OSError:
            continue
        if match:
            return match.group(0)
    return None


def update_all(url):
    """Point every known client config at `url`. Returns the files changed."""
    changed = []
    for path in candidates():
        try:
            with open(path, encoding="utf-8", errors="replace") as fh:
                text = fh.read()
        except OSError:
            continue
        new_text = TUNNEL_RE.sub(url, text)
        if new_text != text:
            try:
                with open(path, "w", encoding="utf-8") as fh:
                    fh.write(new_text)
            except OSError:
                continue
            changed.append(path)
    return changed

# Hermes Agent dev container.
#
# Mirrors the production runtime (Python 3.13, Node 22, uv) but is optimized
# for development: the repo is bind-mounted, deps install into a project-local
# .venv on first create, and the image stays slim. See .devcontainer/README.md.
#
# Base: Microsoft's devcontainer Python image (Debian bookworm). It ships a
# non-root `vscode` user, git, build-essential, and the common tooling
# Codespaces / VS Code Dev Containers expect.
FROM mcr.microsoft.com/devcontainers/python:3.13-bookworm

# uv — the package manager the project standardizes on. Copy the static
# binary from the official image (pinned to match pyproject's dev floor) so we
# don't depend on a curl|sh bootstrap at build time.
COPY --from=ghcr.io/astral-sh/uv:0.11.6 /uv /uvx /usr/local/bin/

# System dependencies the agent and its test/build paths expect:
#   ripgrep   — backs the `search_files` tool (AGENTS.md prefers rg)
#   ffmpeg    — audio/video skills + TTS encoding
#   libolm-dev / libffi-dev / cmake / build tooling — native source builds
#               (matrix's python-olm, faster-whisper, etc.)
#   procps    — ps/process management used by gateway + psutil paths
RUN apt-get update && export DEBIAN_FRONTEND=noninteractive && \
    apt-get install -y --no-install-recommends \
        ripgrep \
        ffmpeg \
        cmake \
        libffi-dev \
        libolm-dev \
        procps \
        openssh-client \
        xz-utils && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Don't write .pyc files; unbuffer stdout so logs stream immediately.
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_LINK_MODE=copy

FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    HF_HOME=/opt/hf-cache \
    SENTENCE_TRANSFORMERS_HOME=/opt/hf-cache \
    HF_HUB_DISABLE_TELEMETRY=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends git ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /workspace
COPY requirements.txt requirements-dev.txt ./

RUN python -m pip install --upgrade pip \
    && python -m pip install --no-cache-dir \
       --index-url https://download.pytorch.org/whl/cpu torch \
    && python -m pip install --no-cache-dir -r requirements-dev.txt

# Model acquisition happens during image construction, never during test execution.
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"

COPY . /workspace

# Tests exercise Flask's persistent-secret path. Seed a per-image throwaway
# value at build time so the source tree can stay read-only during execution.
RUN python -c "from pathlib import Path; import secrets; p=Path('/workspace/.flask_secret'); p.write_bytes(secrets.token_bytes(32)); p.chmod(0o444)" \
    && if [ ! -e /usr/bin/python3 ]; then ln -s /usr/local/bin/python3 /usr/bin/python3; fi \
    && chown -R 65532:65532 /workspace

# The test process runs unprivileged; the image filesystem remains read-only at runtime.
USER 65532:65532

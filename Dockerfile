# =========================
# Build stage
# =========================
FROM python:3.12-bookworm AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONFAULTHANDLER=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DEFAULT_TIMEOUT=100 \
    PIP_DISABLE_PIP_VERSION_CHECK=on

WORKDIR /myapp

# Build-time OS deps to compile wheels (Pillow, psycopg/cryptography, cffi, etc.)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    libpq-dev \
    libffi-dev \
    libjpeg62-turbo-dev \
    zlib1g-dev \
    libpng-dev \
    libfreetype6-dev \
    curl \
    ca-certificates \
    dos2unix \
 && rm -rf /var/lib/apt/lists/*

# Create a persistent virtualenv and make it the default Python for all next layers
ENV VIRTUAL_ENV=/opt/venv
RUN python -m venv "$VIRTUAL_ENV"
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

# Copy requirements early to leverage Docker layer caching
COPY requirements.txt ./

# Normalize CRLF, show context, then install with extra verbosity
RUN dos2unix requirements.txt || true \
 && python -V \
 && pip -V \
 && echo "----- requirements.txt -----" \
 && cat requirements.txt \
 && echo "----------------------------" \
 && python -m pip install --upgrade pip setuptools wheel \
 && pip install --no-cache-dir -vv --prefer-binary -r requirements.txt

# Copy the rest of the app AFTER deps to leverage Docker layer caching
COPY . .

# =========================
# Runtime stage
# =========================
FROM python:3.12-slim-bookworm AS final

ENV PYTHONUNBUFFERED=1 \
    PYTHONFAULTHANDLER=1

WORKDIR /myapp

# Runtime libs needed at import/use time (Pillow, libpq for psycopg2, etc.)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libjpeg62-turbo \
    zlib1g \
    libpng16-16 \
    libfreetype6 \
    libpq5 \
    ca-certificates \
    curl \
 && rm -rf /var/lib/apt/lists/*

# Bring the venv from the build stage and make it default
COPY --from=base /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Create a non-root user and copy source with correct ownership
RUN useradd -m myuser
USER myuser
COPY --chown=myuser:myuser . .

# Expose API port
EXPOSE 8000

# Default app command (override in docker-compose if needed)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

# ============================================
# BusGo API - Production Dockerfile
# ============================================

# ---------- Stage 1: Build Dependencies ----------
FROM python:3.12-slim-bookworm AS builder

WORKDIR /app

# Install Python dependencies into a virtual environment
# All packages have pre-built wheels for Python 3.12, so no build tools needed
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir --only-binary :all: -r requirements.txt

# ---------- Stage 2: Runtime ----------
FROM python:3.12-slim-bookworm AS runtime

WORKDIR /app

# Create non-root user for security
RUN groupadd -r busgo && useradd -r -g busgo -d /app busgo

# Copy virtual environment from builder stage
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy application code
COPY . .

# Make entrypoint script executable
RUN chmod +x /app/scripts/entrypoint.sh \
    && mkdir -p /app/logs \
    && chown -R busgo:busgo /app

# Switch to non-root user
USER busgo

# Expose the application port
EXPOSE 8000

# Health check (using Python's built-in urllib - no curl needed)
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/', timeout=5)" || exit 1

# Entrypoint: run migrations + seed, then start uvicorn
ENTRYPOINT ["/app/scripts/entrypoint.sh"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
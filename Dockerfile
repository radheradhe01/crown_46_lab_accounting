# Use Python 3.11 slim image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV UV_SYSTEM_PYTHON=1

# Install system dependencies and uv
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    curl \
    && curl -LsSf https://astral.sh/uv/install.sh | sh \
    && mv /root/.local/bin/uv /usr/local/bin/uv \
    && rm -rf /var/lib/apt/lists/* \
    && rm -rf /root/.local

# Copy project configuration files
COPY pyproject.toml uv.lock* ./

# Install Python dependencies using uv
# uv pip install installs to system Python (no virtual environment)
# Install dependencies from pyproject.toml
RUN uv pip install --system --no-cache \
    "gradio>=4.0.0" \
    "pandas>=2.0.0" \
    "numpy>=1.24.0"

# Copy application code
COPY app.py .

# Expose port 7860 (Gradio default)
EXPOSE 7860

# Run the application
CMD ["python", "app.py"]

FROM python:3.13-slim

WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN pip install --no-cache-dir uv && uv sync --frozen --no-dev
COPY week2/app.py ./app.py
EXPOSE 8012
CMD [".venv/bin/uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8012"]

FROM python:3.13-slim

WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN pip install --no-cache-dir uv && uv sync --frozen --no-dev
COPY labs ./labs
EXPOSE 8013
CMD [".venv/bin/uvicorn", "labs.week3_change_request:app", "--host", "0.0.0.0", "--port", "8013"]

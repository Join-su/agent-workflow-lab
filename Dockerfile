FROM python:3.13-slim

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN pip install --no-cache-dir uv \
    && uv sync --frozen --no-dev

COPY lab_core.py ./
COPY week1 ./week1
COPY week2 ./week2
COPY week3 ./week3

ENV PATH="/app/.venv/bin:${PATH}"

CMD ["uvicorn", "week1.app:app", "--host", "0.0.0.0", "--port", "8011"]

FROM python:3.13-slim

WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN pip install --no-cache-dir uv && uv sync --frozen --no-dev
COPY labs ./labs
EXPOSE 8012
CMD [".venv/bin/uvicorn", "labs.week2_expense_review:app", "--host", "0.0.0.0", "--port", "8012"]

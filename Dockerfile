FROM python:3.12-slim

RUN groupadd -r nonroot && useradd -r -g nonroot appuser

WORKDIR /app

RUN pip install --no-cache-dir poetry

ENV POETRY_VIRTUALENVS_CREATE=false

COPY pyproject.toml poetry.lock /app/

RUN poetry install --only main --no-root && \
    rm -rf /root/.cache/* /tmp/*

COPY . .

RUN chown -R appuser:nonroot /app

USER appuser

ENTRYPOINT ["python3", "-m", "src.main"]
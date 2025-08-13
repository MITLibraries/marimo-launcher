#========================================
# builder layer
#========================================
FROM python:3.13-slim AS builder

# install uv and use system python
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv
ENV UV_SYSTEM_PYTHON=1

COPY pyproject.toml pyproject.toml
COPY uv.lock uv.lock

RUN uv export --no-dev --format requirements.txt -o /requirements.txt

#========================================
# final image
#========================================
FROM python:3.13-slim

# install git
RUN apt-get update && \
    apt-get install -y --no-install-recommends git ca-certificates

# install uv and use system python
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv
ENV UV_SYSTEM_PYTHON=1

# get pylock.toml from builder layer
COPY --from=builder /requirements.txt /requirements.txt

# install dependencies to global python
RUN uv pip install -r /requirements.txt

# copy application
WORKDIR /app
COPY ./launcher /app/launcher

EXPOSE 2718

ENTRYPOINT ["python", "-m", "launcher.cli"]
CMD []

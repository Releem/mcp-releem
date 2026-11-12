FROM python:3.12-alpine@sha256:e064671ca452259bab50e8e2c7bd896e39e9a343bb06ca25234adf6fe18d0fc7 AS base
RUN pip install --no-cache-dir uv==0.13.7
WORKDIR /app
ENV UV_PROJECT_ENVIRONMENT=/opt/venv UV_CACHE_DIR=/tmp/uv-cache UV_LINK_MODE=copy PYTHONDONTWRITEBYTECODE=1
COPY pyproject.toml uv.lock README.md ./
COPY src ./src

FROM base AS checks
RUN --mount=type=tmpfs,target=/tmp uv sync --locked --no-cache
COPY tests ./tests
COPY deploy ./deploy
COPY compose.yaml ./compose.yaml
COPY docs/plans/evidence/releem-openapi-2026-11-11.json ./docs/plans/evidence/
COPY tools/release ./tools/release
COPY tools/containers ./tools/containers
ENV PATH="/opt/venv/bin:$PATH"
USER 65532:65532
CMD ["pytest", "-q", "-p", "no:cacheprovider"]

FROM base AS build
RUN --mount=type=tmpfs,target=/tmp uv sync --locked --no-cache && uv build --python /opt/venv/bin/python --no-sources --no-build-isolation

FROM scratch AS artifacts
COPY --from=build /app/dist /

FROM base AS runtime
LABEL org.opencontainers.image.source="https://github.com/Releem/releem-mcp-server"
RUN --mount=type=bind,source=tools/containers,target=/build-tools,ro python /build-tools/runtime_base.py
RUN --mount=type=tmpfs,target=/tmp uv sync --locked --no-dev --no-editable --no-cache
ENV PATH="/opt/venv/bin:$PATH"
USER 65532:65532
ENTRYPOINT ["mcp-releem"]

FROM runtime AS hosted
ENV RELEEM_MCP_PROFILE=hosted RELEEM_MCP_BIND_HOST=0.0.0.0
ENTRYPOINT ["mcp-releem", "--transport", "streamable-http"]

FROM runtime AS wheel-check
USER root
COPY --from=build /app/dist /dist
RUN uv pip install --python /opt/venv/bin/python --no-deps --reinstall /dist/*.whl
USER 65532:65532

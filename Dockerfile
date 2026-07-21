# Multi-stage, non-root container (audit SEC-007).
FROM python:3.12-slim AS build
WORKDIR /app
COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --no-cache-dir --upgrade pip build \
    && pip install --no-cache-dir --prefix=/install .

FROM python:3.12-slim
# Drop privileges: run as an unprivileged user, never root.
RUN useradd --create-home --uid 10001 appuser
COPY --from=build /install /usr/local
USER appuser
WORKDIR /home/appuser

# Loopback bind by default (SEC-016); override MCP_HOST only behind a proxy.
ENV MCP_TRANSPORT=streamable-http \
    MCP_HOST=0.0.0.0 \
    MCP_PORT=8000
# In a container the process is already network-isolated, so binding 0.0.0.0
# inside the container is the documented, intended case (the host still maps a
# single published port). Put an authenticating reverse proxy in front.
EXPOSE 8000
ENTRYPOINT ["python", "-m", "swiss_holidays_mcp"]

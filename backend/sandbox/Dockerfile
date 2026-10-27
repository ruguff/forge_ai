# Build this trusted runtime explicitly before generated-code execution.
# Generated dependency scripts and internet access are disabled at execution.
FROM node:20-bookworm-slim
RUN apt-get update && apt-get install -y --no-install-recommends python3 python3-venv && rm -rf /var/lib/apt/lists/*
RUN python3 -m venv /opt/python && /opt/python/bin/pip install fastapi uvicorn pydantic 'sqlalchemy>=2,<3' httpx pytest pytest-asyncio playwright && /opt/python/bin/playwright install --with-deps chromium
ENV PATH="/opt/python/bin:${PATH}" PYTHONPATH="/tmp/workspace/backend" HOME="/tmp" PYTHONDONTWRITEBYTECODE="1"
ENV PLAYWRIGHT_BROWSERS_PATH="/opt/browsers"
RUN /opt/python/bin/playwright install chromium && chmod -R a+rX /opt/browsers
RUN mkdir -p /opt/frontend && cd /opt/frontend && npm install --ignore-scripts react@18 react-dom@18 @types/react@18 @types/react-dom@18 typescript@5 vite@6.4.5 @vitejs/plugin-react@4.7.0 \
    && ln -s /tmp /opt/frontend/node_modules/.vite-temp
COPY entrypoint.sh /opt/entrypoint.sh
RUN chmod 755 /opt/entrypoint.sh
USER 65534:65534
ENTRYPOINT ["/opt/entrypoint.sh"]

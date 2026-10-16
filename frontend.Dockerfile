# syntax=docker/dockerfile:1
# Web application (TanStack Start, server-rendered by Nitro's node-server preset).
# Caddy routes /api/* to the backend and everything else to this container.

FROM node:22-alpine AS build
WORKDIR /app
# bun.lock pins the exact versions the design was approved against.
RUN npm install -g bun@1.4.2
COPY package.json bun.lock bunfig.toml ./
RUN bun install --frozen-lockfile
COPY . .
ENV NITRO_PRESET=node-server
RUN bun run build && bun install --production --frozen-lockfile

FROM node:22-alpine AS runtime
WORKDIR /app
ENV NODE_ENV=production \
    HOST=0.0.0.0 \
    PORT=8080
COPY --from=build --chown=node:node /app/.output ./.output
USER node
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD wget -qO- http://127.0.0.1:8080/ >/dev/null || exit 1
CMD ["node", ".output/server/index.mjs"]

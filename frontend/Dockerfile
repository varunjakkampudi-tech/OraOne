# syntax=docker/dockerfile:1

# ---- Build stage ----
FROM node:20-alpine AS build

WORKDIR /build

COPY package.json package-lock.json ./
# react-day-picker 8.x has a stale React peer range and is compatible with
# this project's React 19 runtime. Keep the lockfile authoritative while
# allowing the clean production image to resolve that known peer mismatch.
RUN npm ci --ignore-scripts --legacy-peer-deps

COPY . .

# REACT_APP_* build args let a deployer point this image at an explicit
# backend. Production Compose requires this value; there is no localhost
# fallback in the release image.
ARG REACT_APP_API_URL
ARG REACT_APP_ENV=production
ARG REACT_APP_AUTH_PROVIDER=cognito
ARG REACT_APP_COGNITO_DOMAIN
ARG REACT_APP_COGNITO_CLIENT_ID
ARG REACT_APP_COGNITO_REDIRECT_URI
ENV REACT_APP_API_URL=${REACT_APP_API_URL} \
    REACT_APP_ENV=${REACT_APP_ENV} \
    REACT_APP_AUTH_PROVIDER=${REACT_APP_AUTH_PROVIDER} \
    REACT_APP_COGNITO_DOMAIN=${REACT_APP_COGNITO_DOMAIN} \
    REACT_APP_COGNITO_CLIENT_ID=${REACT_APP_COGNITO_CLIENT_ID} \
    REACT_APP_COGNITO_REDIRECT_URI=${REACT_APP_COGNITO_REDIRECT_URI} \
    CI=true

RUN test -n "$REACT_APP_API_URL" && npm run build

# ---- Runtime stage: static files behind nginx ----
FROM nginx:1.27-alpine AS runtime

ARG APP_VERSION=v1.0.0
LABEL org.opencontainers.image.title="oraone-frontend" \
      org.opencontainers.image.version="${APP_VERSION}" \
      org.opencontainers.image.description="OraOne Chat Platform — static frontend (Vite)"

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /build/build /usr/share/nginx/html

# nginx:alpine already runs the master process as root but worker processes
# as the unprivileged `nginx` user; that's sufficient here since we don't
# bind to a privileged port or write to the filesystem at runtime.

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD wget -qO- http://127.0.0.1:8080/ >/dev/null || exit 1

CMD ["nginx", "-g", "daemon off;"]

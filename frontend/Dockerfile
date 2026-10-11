# syntax=docker/dockerfile:1

# ---- Build stage ----
FROM node:20-alpine AS build

WORKDIR /build

COPY package.json yarn.lock ./
RUN yarn install --frozen-lockfile

COPY . .

# REACT_APP_* build args let a deployer point this image at their own
# backend without rebuilding the Dockerfile itself.
ARG REACT_APP_API_URL=http://localhost:8000
ARG REACT_APP_ENV=production
ENV REACT_APP_API_URL=${REACT_APP_API_URL} \
    REACT_APP_ENV=${REACT_APP_ENV} \
    CI=true

RUN yarn build

# ---- Runtime stage: static files behind nginx ----
FROM nginx:1.27-alpine AS runtime

ARG APP_VERSION=v1.0.0
LABEL org.opencontainers.image.title="oraone-frontend" \
      org.opencontainers.image.version="${APP_VERSION}" \
      org.opencontainers.image.description="OraOne Chat Platform — static frontend (CRA)"

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /build/build /usr/share/nginx/html

# nginx:alpine already runs the master process as root but worker processes
# as the unprivileged `nginx` user; that's sufficient here since we don't
# bind to a privileged port or write to the filesystem at runtime.

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD wget -qO- http://127.0.0.1:8080/ >/dev/null || exit 1

CMD ["nginx", "-g", "daemon off;"]

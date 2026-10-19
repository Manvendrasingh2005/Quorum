# ==============================================================================
# Quorum AI - Production Frontend Dockerfile
# Multi-stage Node.js 20 build -> Minimal Nginx Alpine runtime
# ==============================================================================

# Stage 1: Build production bundle
FROM node:20-alpine AS builder

WORKDIR /app

# Install dependencies first for Docker caching
COPY package*.json ./
RUN npm ci

# Copy source and build static artifacts
COPY . .
RUN npm run build

# Stage 2: Serve via high-performance Nginx
FROM nginx:alpine AS runner

# Remove default static files
RUN rm -rf /usr/share/nginx/html/*

# Copy built distribution from builder
COPY --from=builder /app/dist /usr/share/nginx/html

# Copy custom Nginx configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD wget --quiet --tries=1 --spider http://localhost/healthz || exit 1

CMD ["nginx", "-g", "daemon off;"]

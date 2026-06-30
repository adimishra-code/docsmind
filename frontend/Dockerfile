# syntax=docker/dockerfile:1

# Build Stage
FROM node:22-alpine AS builder

WORKDIR /app

# Install dependencies first for better caching
COPY package.json package-lock.json ./
RUN npm ci

# Copy source code and build
COPY . .
RUN npm run build

# Serve Stage
FROM nginx:alpine-slim

# Copy built assets to Nginx
COPY --from=builder /app/dist /usr/share/nginx/html

# The Nginx config will be provided via docker-compose volume mapping
EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]

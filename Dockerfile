# syntax=docker/dockerfile:1

### Build stage
FROM oven/bun:1 AS builder
WORKDIR /app

# Install Node dependencies
COPY bun.lock package.json ./
RUN bun install --frozen-lockfile

# Copy source files and build the Nuxt application
COPY . .
RUN bun run build

### Runtime stage
FROM python:3.12-slim

# Install required system packages and Bun
RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/* \
    && curl -fsSL https://bun.sh/install | bash \
    && mv /root/.bun/bin/bun /usr/local/bin/bun

WORKDIR /app

# Copy application from the builder stage
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/.output ./.output
COPY --from=builder /app/package.json ./package.json

# Copy Python sources and install dependencies
COPY pyproject.toml uv.lock ./
COPY modules ./modules
RUN pip install --no-cache-dir .

EXPOSE 3000

# Run the built Nuxt application
CMD ["bun", "run", "preview"]

# Build stage
FROM node:22-alpine AS builder

# Set working directory
WORKDIR /app

# Install system dependencies for building native modules
RUN apk add --no-cache \
    curl \
    bash \
    python3 \
    make \
    g++ \
    && rm -rf /var/cache/apk/*

# Install Bun
RUN curl -fsSL https://bun.sh/install | bash
ENV PATH="/root/.bun/bin:$PATH"

# Copy package files
COPY package.json bun.lock* ./

# Install dependencies (including dev dependencies for build)
RUN bun install --frozen-lockfile

# Copy project files
COPY . .

# Build the application
RUN bun run build

# Runtime stage
FROM node:22-alpine AS runtime

# Set working directory
WORKDIR /app

# Set environment variables
ENV NODE_ENV=production \
    NITRO_HOST=0.0.0.0 \
    NITRO_PORT=3000

# Install only runtime dependencies
RUN apk add --no-cache \
    curl \
    netcat-openbsd \
    pandoc \
    && rm -rf /var/cache/apk/*

# Create non-root user
RUN addgroup -g 1001 -S nodejs && \
    adduser -S nuxt -u 1001 -G nodejs

# Copy built application with all dependencies and correct ownership from builder stage
COPY --from=builder --chown=nuxt:nodejs /app/.output /app/.output

# Switch to non-root user
USER nuxt

# Expose the port the app runs on
EXPOSE 3000

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:3000/ || exit 1

# Command to run the application
CMD ["node", ".output/server/index.mjs"]

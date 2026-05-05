# Silvercurrent frontend — dev-mode container for local-first `docker compose up`.
# Not a production image: runs `next dev` for hot reload, mounts source via compose.
FROM node:22-alpine

WORKDIR /app

# pnpm via corepack (bundled with Node 22).
RUN corepack enable && corepack prepare pnpm@latest --activate

# Install dependencies first for layer caching.
COPY package.json pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile

# Copy source. In dev compose we typically bind-mount over this.
COPY . .

EXPOSE 3000

# Bind to 0.0.0.0 so the port is reachable from the host.
CMD ["pnpm", "dev", "--hostname", "0.0.0.0"]

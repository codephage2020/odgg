FROM node:20-alpine

WORKDIR /app

# Install pnpm
RUN corepack enable && corepack prepare pnpm@latest --activate

COPY package.json pnpm-lock.yaml* ./
RUN pnpm install --frozen-lockfile 2>/dev/null || pnpm install

COPY . .

EXPOSE 3001

CMD ["pnpm", "run", "dev", "--", "--host", "--port", "3001"]

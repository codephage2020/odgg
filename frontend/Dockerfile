# ---------- Stage 1: Build ----------
FROM node:20-alpine AS build

WORKDIR /app

# Install pnpm
RUN corepack enable && corepack prepare pnpm@latest --activate

COPY package.json pnpm-lock.yaml* ./
RUN pnpm install --frozen-lockfile 2>/dev/null || pnpm install

# Build args → Vite env vars (baked into the bundle at build time)
ARG VITE_API_URL=/api/v1
ARG VITE_DB_HOST=db
ARG VITE_DB_PORT=5432
ENV VITE_API_URL=$VITE_API_URL
ENV VITE_DB_HOST=$VITE_DB_HOST
ENV VITE_DB_PORT=$VITE_DB_PORT

COPY . .
RUN pnpm run build

# ---------- Stage 2: Serve ----------
FROM nginx:alpine

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 3001

CMD ["nginx", "-g", "daemon off;"]

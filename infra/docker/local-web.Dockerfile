FROM postgres:17

WORKDIR /app

ARG NEXT_PUBLIC_API_BASE_URL=http://localhost:8080
ENV NEXT_PUBLIC_API_BASE_URL=${NEXT_PUBLIC_API_BASE_URL}

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates curl xz-utils \
    && rm -rf /var/lib/apt/lists/*

RUN curl -fsSL https://nodejs.org/dist/v24.15.0/node-v24.15.0-linux-x64.tar.xz \
    | tar -xJf - -C /usr/local --strip-components=1

COPY package.json package-lock.json ./
RUN npm config set registry https://registry.npmmirror.com/ \
    && npm config set replace-registry-host always \
    && npm config set fetch-retries 5 \
    && npm config set fetch-retry-mintimeout 20000 \
    && npm config set fetch-retry-maxtimeout 120000 \
    && npm config set fetch-timeout 180000 \
    && npm ci --include=dev --no-audit --no-fund

COPY . .

ENV NODE_ENV=production
ENV PORT=3000

RUN npm run build

EXPOSE 3000

HEALTHCHECK --interval=15s --timeout=5s --retries=10 CMD curl -fsS http://localhost:3000/app > /dev/null || exit 1

CMD ["npm", "run", "start", "--", "--hostname", "0.0.0.0", "--port", "3000"]

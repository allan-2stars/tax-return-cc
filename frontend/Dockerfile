# Stage 0: Dev — deps only, no build. Source mounted via docker-compose volume.
FROM node:20-alpine AS dev
WORKDIR /app
ENV NEXT_TELEMETRY_DISABLED=1
COPY package*.json ./
RUN npm install
EXPOSE 3000
CMD ["npm", "run", "dev"]

# Stage 1: Builder
FROM node:20-alpine AS builder

WORKDIR /app

ENV NEXT_TELEMETRY_DISABLED=1

# Copy package manifests first for layer caching.
# NODE_ENV is intentionally NOT set here — npm install must include devDependencies
# (Tailwind, TypeScript, etc.) which are needed at build time.
# TODO: switch to `npm ci` once package-lock.json is committed to the repo.
COPY package*.json ./
RUN npm install

# Copy all source files and build.
# next.config.js must have output: 'standalone' (configured in Task 9).
COPY . .
ENV NODE_ENV=production
RUN npm run build

# Stage 2: Runner — lean production image
FROM node:20-alpine AS runner

WORKDIR /app

ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1

# Create a non-root system user/group for security.
RUN addgroup --system --gid 1001 nodejs \
 && adduser --system --uid 1001 nextjs

# Copy built artefacts from builder.
COPY --from=builder /app/public ./public
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

USER nextjs

EXPOSE 3000

ENV PORT=3000
ENV HOSTNAME=0.0.0.0

CMD ["node", "server.js"]

FROM node:20.18.1-alpine

WORKDIR /usr/src/app

# Enable corepack which provides pnpm without global installation
RUN corepack enable

COPY package.json pnpm-lock.yaml ./

# Install dependencies
RUN pnpm install --frozen-lockfile

COPY . .

RUN pnpm build

EXPOSE 3000

# About the start command:
# In development (locally): we use "start:dev" for hot-reload
# In production (Docker): we use "start:prod" for optimized production build
CMD ["pnpm", "start:prod"]
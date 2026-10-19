# syntax=docker/dockerfile:1.7
FROM node:20-alpine AS build
WORKDIR /app/portal
COPY portal/package.json portal/package-lock.json ./
RUN npm ci
WORKDIR /app
COPY shared ./shared
COPY portal ./portal
WORKDIR /app/portal
RUN npm run build

FROM nginx:1.27-alpine AS runtime
COPY --from=build /app/portal/dist /usr/share/nginx/html
COPY portal/nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
HEALTHCHECK --interval=10s --timeout=3s --retries=3 \
  CMD wget -q -O /dev/null http://127.0.0.1/ || exit 1
CMD ["nginx", "-g", "daemon off;"]

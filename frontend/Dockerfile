# Frontend PWA
FROM node:20-alpine as build

WORKDIR /app

# Copy package files
COPY package*.json ./
RUN npm ci

# Copy source
COPY . .

# Build PWA
RUN npm run build

# Production stage with nginx
FROM nginx:alpine

# Copy built files
COPY --from=build /app/dist /usr/share/nginx/html

# Copy nginx config template for SPA routing and API proxy.
# We render ONLY ${BACKEND_URL} at container start to avoid envsubst clobbering
# nginx runtime variables like $uri, $host, etc.
COPY nginx.conf /etc/nginx/conf.d/default.conf.template
COPY docker-entrypoint.d/00-render-nginx-backend-url.sh /docker-entrypoint.d/00-render-nginx-backend-url.sh
RUN chmod +x /docker-entrypoint.d/00-render-nginx-backend-url.sh

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]

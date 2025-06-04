# Build stage
FROM node:20-slim as build

WORKDIR /app

# Copiar arquivos de configuração primeiro para melhor caching
COPY package*.json ./
COPY vite.config.js ./
COPY tailwind.config.js ./
COPY postcss.config.js ./

# Instalar dependências
RUN npm install

# Copiar código fonte
COPY . .

# Build
RUN npm run build

# Production stage
FROM nginx:alpine

# Copiar configuração personalizada do nginx
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copiar arquivos buildados
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]

FROM node:20-slim

WORKDIR /app

# Gerenciamento de dependências via manifestos Node.js para otimização das camadas de construção.
COPY package.json package-lock.json ./

# Provisionamento de pacotes para o framework Nuxt e bibliotecas de visualização espacial.
RUN npm install

# Migração da interface reativa e lógica de visualização 3D para o diretório de trabalho.
COPY . .

# Argumento e variável de ambiente para configurar o proxy em tempo de build/runtime.
ARG API_URL_BASE=http://backend:8000
ENV API_URL_BASE=$API_URL_BASE

# Compilação do frontend para geração dos ativos estáticos otimizados e minificados para produção.
RUN rm -rf .nuxt .output && npm run build

EXPOSE 3000

ENV NUXT_HOST=0.0.0.0
ENV NUXT_PORT=3000

# Inicialização do servidor de aplicação para entrega da interface ao usuário final.
CMD ["node", ".output/server/index.mjs"]

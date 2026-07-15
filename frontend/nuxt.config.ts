// nuxt.config.ts: Configuração do frontend Nuxt 4
export default defineNuxtConfig({
  // Renderização client-side (WebGL no TrussViewer exige browser).
  ssr: false,

  // Módulos Nuxt.
  modules: ['@nuxtjs/tailwindcss', '@tresjs/nuxt', '@pinia/nuxt', '@nuxt/icon'],

  // Variáveis de runtime expostas ao client.
  runtimeConfig: {
    public: {
      apiBaseUrl: process.env.API_URL_BASE || 'http://localhost:8000',
    },
  },

  // Proxy + watcher para desenvolvimento (npm run dev).
  vite: {
    server: {
      // Ative usePolling se for rodar npm run dev dentro do Docker.
      // watch: { usePolling: true, interval: 1000 },
      proxy: {
        '/api': {
          target: process.env.API_URL_BASE || 'http://localhost:8000',
          changeOrigin: true,
          ws: true,
        },
      },
    },
  },

  // Configurações do TresJS (Three.js para Vue).
  tresjs: {
    devtools: false,
  },

  // Configurações de build.
  app: {
    head: {
      title: 'TRUSS-OPT 3D — Otimizador de Treliças 3D',
      meta: [
        { charset: 'utf-8' },
        { name: 'viewport', content: 'width=device-width, initial-scale=1' },
        {
          name: 'description',
          content:
            'Otimização de treliças 3D via Algoritmo Genético com verificação NBR 8800/6120/6123.',
        },
      ],
    },
  },

  // Tipos estritos para TypeScript.
  typescript: {
    strict: true,
    typeCheck: false,
  },

  // Compatibilidade de data.
  compatibilityDate: '2025-01-01',
});

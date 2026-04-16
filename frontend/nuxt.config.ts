// https://nuxt.com/docs/api/configuration/nuxt-config
export default defineNuxtConfig({
  // Desativação do SSR (Server Side Rendering) para garantir uma experiência de Single Page Application (SPA).
  // Sendo assim, a renderização WebGL e o processamento 3D ocorrem exclusivamente no lado do cliente.
  ssr: false,

  // Redirecionamento do diretório de origem para a raiz do projeto frontend.
  srcDir: "./",

  compatibilityDate: "2024-04-03",

  // Módulos para integração de design reativo, renderização espacial, estado global e iconografia.
  modules: ["@nuxtjs/tailwindcss", "@tresjs/nuxt", "@pinia/nuxt", "@nuxt/icon"],

  // Configuração de carregamento automático de componentes para otimização do fluxo de desenvolvimento.
  components: [
    {
      path: "~/components",
      pathPrefix: false,
    },
  ],

  tres: {
    devtools: true,
  },

  // Roteamento de proxy para encaminhamento das requisições de cálculo ao solver no backend.
  // Portanto, mitiga-se a necessidade de configurações complexas de CORS em ambiente de produção.
  nitro: {
    routeRules: {
      "/api/**": { proxy: "http://backend:8000/api/**" },
    },
  },

  // Otimização do bundle Vite para dependências de geometria espacial e renderização.
  vite: {
    optimizeDeps: {
      include: ["three", "@tresjs/core", "@tresjs/cientos"],
    },
  },
});

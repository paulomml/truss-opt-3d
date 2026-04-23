// https://nuxt.com/docs/api/configuration/nuxt-config
export default defineNuxtConfig({
  ssr: false, // TresJS/WebGL dependem de APIs do browser.

  srcDir: "./",

  compatibilityDate: "2024-04-03",

  app: {
    head: {
      title: "TRUSS-OPT 3D - Otimizador de Treliças 3D",
    },
  },

  modules: ["@nuxtjs/tailwindcss", "@tresjs/nuxt", "@pinia/nuxt", "@nuxt/icon"],

  components: [
    {
      path: "~/components",
      pathPrefix: false,
    },
  ],

  tres: {
    devtools: true,
  },

  nitro: {
    routeRules: {
      "/api/**": {
        proxy: process.env.API_URL_BASE
          ? `${process.env.API_URL_BASE}/api/**`
          : "http://localhost:8000/api/**",
      },
    },
  },

  vite: {
    server: {
      proxy: {
        "/api": {
          target: process.env.API_URL_BASE || "http://localhost:8000",
          changeOrigin: true,
          ws: true,
        },
      },
    },
    optimizeDeps: {
      include: ["three", "@tresjs/core", "@tresjs/cientos"],
    },
  },
});

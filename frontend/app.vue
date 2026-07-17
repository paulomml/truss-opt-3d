<template>
  <div>
    <NuxtPage />
  </div>
</template>

<script setup lang="ts">
// App raiz: NuxtPage renderiza a rota atual (pages/index.vue).
// Mantém o keep-alive do WebSocket através do store Pinia.
</script>

<style>
/* Scrollbar customizada (tema escuro) */

/* Firefox */
* {
  scrollbar-width: thin;
  scrollbar-color: #4b5563 #1f2937;
}

/* Chrome, Edge, Safari */
*::-webkit-scrollbar {
  width: 8px;
  height: 8px;
}

*::-webkit-scrollbar-track {
  background: #1f2937;
}

*::-webkit-scrollbar-thumb {
  background-color: #4b5563;
  border-radius: 9999px;
  border: 1.5px solid #1f2937;
}

*::-webkit-scrollbar-thumb:hover {
  background-color: #6b7280;
}

*::-webkit-scrollbar-corner {
  background: #1f2937;
}
</style>

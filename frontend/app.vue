<script setup lang="ts">
import { onMounted, onUnmounted } from "vue";

let healthInterval: any;

onMounted(() => {
  // Mantém o servidor Render ativo fazendo pings a cada 5 minutos.
  // Isso evita o desligamento automático da instância por inatividade.
  healthInterval = setInterval(
    () => {
      $fetch("/api/health").catch((err) =>
        console.error("Keep-alive ping falhou:", err),
      );
    },
    5 * 60 * 1000,
  );
});

onUnmounted(() => {
  if (healthInterval) clearInterval(healthInterval);
});
</script>

<style>
/* Estilização Global da Barra de Rolagem (Scrollbar) harmonizada com o tema dark da aplicação. */
::-webkit-scrollbar {
  width: 8px;
  height: 8px;
}

::-webkit-scrollbar-track {
  background: rgba(31, 41, 55, 0.5); /* Gray-800 com opacidade */
  border-radius: 10px;
}

::-webkit-scrollbar-thumb {
  background: rgba(75, 85, 99, 0.8); /* Gray-600 com opacidade */
  border-radius: 10px;
  border: 2px solid transparent;
  background-clip: content-box;
}

::-webkit-scrollbar-thumb:hover {
  background: rgba(107, 114, 128, 1); /* Gray-500 */
  border: 2px solid transparent;
  background-clip: content-box;
}

/* Suporte para Firefox */
* {
  scrollbar-width: thin;
  scrollbar-color: rgba(75, 85, 99, 0.8) rgba(31, 41, 55, 0.5);
}
</style>

<template>
  <!-- Ponto de entrada da aplicação: orquestração de layouts, páginas e sistema de notificações. -->
  <div class="fixed inset-0 overflow-hidden">
    <NuxtLayout>
      <NuxtPage />
    </NuxtLayout>
    <ToastContainer />
  </div>
</template>

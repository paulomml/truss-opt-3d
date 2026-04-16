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

<template>
  <!-- Ponto de entrada da aplicação: orquestração de layouts, páginas e sistema de notificações. -->
  <div class="fixed inset-0 overflow-hidden">
    <NuxtLayout>
      <NuxtPage />
    </NuxtLayout>
    <ToastContainer />
  </div>
</template>

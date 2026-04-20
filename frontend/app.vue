<script setup lang="ts">
import { onMounted, onUnmounted } from "vue";

let healthInterval: any;

onMounted(() => {
  // Mitiga o cold-start de instâncias free-tier (Render).
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
@import url("https://fonts.googleapis.com/css2?family=Roboto:ital,wght@0,100;0,300;0,400;0,500;0,700;0,900;1,100;1,300;1,400;1,500;1,700;1,900&display=swap");

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

* {
  scrollbar-width: thin;
  scrollbar-color: rgba(75, 85, 99, 0.8) rgba(31, 41, 55, 0.5);
}
</style>

<template>
  <div class="fixed inset-0 overflow-hidden">
    <NuxtLayout>
      <NuxtPage />
    </NuxtLayout>
    <ToastContainer />
  </div>
</template>

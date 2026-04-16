<script setup lang="ts">
const store = useTrussStore();
</script>

<template>
  <!-- Camada de bloqueio visual durante o processamento da análise de elementos finitos. -->
  <!-- Portanto, evita-se a alteração de parâmetros enquanto o solver matricial está em execução. -->
  <div
    v-if="store.loading"
    class="absolute inset-0 z-10 flex items-center justify-center bg-black/40 backdrop-blur-sm"
  >
    <div class="flex flex-col items-center">
      <div
        class="w-12 h-12 border-4 border-blue-500 border-t-transparent rounded-full animate-spin mb-4"
      ></div>
      <p class="text-white font-semibold">
        Analisando Estabilidade Estrutural...
      </p>
    </div>
  </div>
</template>

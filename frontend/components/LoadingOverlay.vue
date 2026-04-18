<script setup lang="ts">
const store = useTrussStore();
</script>

<template>
  <!-- Camada de bloqueio visual durante o processamento da análise de elementos finitos. -->
  <!-- Portanto, evita-se a alteração de parâmetros enquanto o solver matricial está em execução. -->
  <div
    v-if="store.loading"
    class="absolute inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-md px-6 text-center"
  >
    <div class="flex flex-col items-center max-w-sm">
      <div
        class="w-14 h-14 border-4 border-blue-500 border-t-transparent rounded-full animate-spin mb-6"
      ></div>
      <p class="text-white text-lg font-bold mb-2">
        Calculando a Melhor Solução...
      </p>

      <!-- Barra de progresso global (Progresso da Análise). -->
      <!-- Sendo assim, o usuário acompanha a evolução total da análise técnica. -->
      <div
        class="w-full bg-gray-700 rounded-full h-3 mb-6 overflow-hidden border border-gray-600"
      >
        <div
          class="bg-blue-500 h-3 rounded-full transition-all duration-500 ease-out shadow-[0_0_10px_rgba(59,130,246,0.5)]"
          :style="{ width: store.mainProgress + '%' }"
        ></div>
      </div>

      <!-- Painel de Status (Acompanhamento em tempo real). -->
      <!-- Logo, o estado de cada etapa do cálculo é visível de forma clara para o usuário. -->
      <div
        class="w-full text-left bg-black/40 backdrop-blur-sm rounded-lg p-3 h-48 overflow-y-auto mb-6 text-[11px] border border-white/10 shadow-inner"
      >
        <div
          v-for="(msg, material) in store.currentLogs"
          :key="material"
          class="flex items-start space-x-2 border-b border-white/5 py-2 last:border-0"
        >
          <span class="text-blue-400 font-bold shrink-0">{{ material }}:</span>
          <span class="text-gray-300">{{ msg }}</span>
        </div>
      </div>

      <!-- Botão de interrupção imediata e limpeza de memória. -->
      <button
        @click="store.cancelOptimization"
        class="px-8 py-3 bg-red-600 hover:bg-red-700 text-white font-bold rounded-lg shadow-lg transition-all transform active:translate-y-0 text-sm"
      >
        Cancelar
      </button>
    </div>
  </div>
</template>

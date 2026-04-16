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
        Analisando Estabilidade Estrutural...
      </p>

      <!-- Aviso dinâmico de tempo de processamento elevado. -->
      <transition
        enter-active-class="transition duration-300 ease-out"
        enter-from-class="opacity-0 transform -translate-y-2"
        enter-to-class="opacity-100 transform translate-y-0"
      >
        <p v-if="store.showTimeoutWarning" class="text-blue-200 text-sm mb-6">
          Esta análise está levando mais tempo que o usual. Você pode continuar
          aguardando ou cancelar o processamento.
        </p>
      </transition>

      <!-- Botão de interrupção imediata: Estilo sóbrio e unificado com o restante da UI. -->
      <button
        @click="store.cancelOptimization"
        class="px-8 py-3 bg-red-600 hover:bg-red-700 text-white font-bold rounded-lg shadow-lg transition-all transform hover:-translate-y-0.5 active:translate-y-0 text-sm"
      >
        Cancelar Otimização
      </button>
    </div>
  </div>
</template>

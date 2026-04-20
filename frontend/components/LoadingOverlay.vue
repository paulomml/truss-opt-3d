<script setup lang="ts">
import { ref, onMounted, onUnmounted } from "vue";
import { useTrussStore } from "@/stores/useTrussStore";

const store = useTrussStore();

const loadingPhrases = [
  "Calculando a melhor solução...",
  "Avaliando esbeltez e estabilidade global...",
  "Processando matriz de rigidez...",
  "Otimizando seções transversais...",
  "Verificando limites de tensão e compressão...",
  "Ajustando perfis estruturais...",
  "Calculando deslocamentos nodais...",
  "Simulando carga e apoios...",
  "Refinando a estrutura para menor peso...",
  "Validando integridade estrutural...",
];

const currentPhraseIndex = ref(0);
let phraseInterval: any = null;

onMounted(() => {
  phraseInterval = setInterval(() => {
    currentPhraseIndex.value =
      (currentPhraseIndex.value + 1) % loadingPhrases.length;
  }, 3000);
});

onUnmounted(() => {
  if (phraseInterval) clearInterval(phraseInterval);
});

const getStatusColor = (msg: string) => {
  const lowerMsg = String(msg).toLowerCase();

  // Status de Sucesso: Sinalização em verde estático para conclusão positiva do processamento.
  if (lowerMsg.includes("finalizado"))
    return "bg-green-500 shadow-[0_0_8px_rgba(34,197,94,0.6)]";

  // Status de Erro ou Inviabilidade: Alerta em vermelho para falhas de estabilidade ou limites de dimensionamento.
  if (
    lowerMsg.includes("erro") ||
    lowerMsg.includes("falha") ||
    lowerMsg.includes("inviável") ||
    lowerMsg.includes("insuficiente") ||
    lowerMsg.includes("resistência máxima")
  ) {
    return "bg-red-500 shadow-[0_0_8px_rgba(239,68,68,0.6)]";
  }

  // Status de Espera na Fila: Representação neutra para tarefas aguardando disponibilidade de núcleos de CPU.
  if (lowerMsg.includes("aguardando"))
    return "bg-gray-500 shadow-[0_0_8px_rgba(107,114,128,0.4)]";

  // Status de Processamento Ativo: Sinalização pulsante em laranja para indicar análise estrutural em andamento.
  return "bg-orange-500 animate-pulse shadow-[0_0_8px_rgba(249,115,22,0.6)]";
};

const parseMessage = (msg: string) => {
  if (!msg) return [];
  return String(msg)
    .split("|")
    .map((s) => s.trim())
    .filter((s) => s.length > 0);
};
</script>

<template>
  <!-- Camada de bloqueio visual durante o processamento da análise de elementos finitos. -->
  <!-- Modificado para 'fixed inset-0 z-[100]' para garantir cobertura total da tela e fixar o layout no mobile. -->
  <div
    v-if="store.loading"
    class="fixed inset-0 z-[100] flex items-center justify-center bg-black/70 backdrop-blur-md px-4 sm:px-6 text-center"
  >
    <div class="flex flex-col items-center w-full max-w-3xl">
      <div
        class="w-14 h-14 border-4 border-blue-500 border-t-transparent rounded-full animate-spin mb-6 shrink-0"
      ></div>
      <p class="text-white text-lg font-bold mb-2">
        {{ loadingPhrases[currentPhraseIndex] }}
      </p>

      <!-- Barra de progresso global (Progresso da Análise). -->
      <!-- O usuário acompanha a evolução total da análise técnica. -->
      <div
        class="w-full max-w-sm bg-gray-700 rounded-full h-3 mb-6 overflow-hidden border border-gray-600"
      >
        <div
          class="bg-blue-500 h-3 rounded-full transition-all duration-500 ease-out shadow-[0_0_10px_rgba(59,130,246,0.5)]"
          :style="{ width: store.mainProgress + '%' }"
        ></div>
      </div>

      <!-- Painel de Status (Acompanhamento em tempo real). -->
      <!-- Janela expandida e logs particionados para melhor legibilidade técnica. -->
      <div
        class="w-full text-left bg-black rounded-lg p-4 h-64 md:h-96 overflow-y-auto mb-6 text-xs sm:text-[13px] font-mono border border-gray-800 shadow-[inset_0_2px_15px_rgba(0,0,0,1)]"
      >
        <div
          v-for="(msg, material) in store.currentLogs"
          :key="material"
          class="grid grid-cols-[100px_1fr] sm:grid-cols-[160px_1fr] gap-4 py-4 border-b border-white/5 last:border-0 hover:bg-white/5 transition-colors duration-200 px-2 rounded -mx-2 items-start"
        >
          <!-- Identificação do Material e Ícone de Status -->
          <div class="flex items-center space-x-2.5 overflow-hidden mt-1">
            <span
              class="w-2.5 h-2.5 rounded-full shrink-0 transition-all duration-300"
              :class="getStatusColor(msg)"
            ></span>
            <span
              class="text-blue-400 font-bold truncate"
              :title="String(material)"
              >{{ material }}</span
            >
          </div>

          <!-- Informações Detalhadas de Otimização -->
          <div class="flex flex-col space-y-2">
            <div
              v-for="(part, idx) in parseMessage(msg)"
              :key="idx"
              class="flex items-start"
            >
              <span class="text-gray-500 mr-2 select-none">›</span>
              <span class="text-gray-300 leading-relaxed break-words">{{
                part
              }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- Botão de interrupção imediata e limpeza de memória. -->
      <!-- Acionador para interrupção forçada do processo e liberação imediata dos recursos do servidor. -->
      <button
        @click="store.cancelOptimization"
        class="px-8 py-3 bg-red-600 hover:bg-red-700 text-white font-bold rounded-lg shadow-lg transition-all transform active:translate-y-0 text-sm"
        title="Interromper imediatamente a análise atual e retornar ao painel de controle."
      >
        Cancelar Análise
      </button>
    </div>
  </div>
</template>

<style scoped>
/* Scrollbar estilizada para o painel de logs para manter harmonia com o layout */
.overflow-y-auto::-webkit-scrollbar {
  width: 6px;
}
.overflow-y-auto::-webkit-scrollbar-track {
  background: rgba(0, 0, 0, 0.2);
}
.overflow-y-auto::-webkit-scrollbar-thumb {
  background: rgba(59, 130, 246, 0.3);
  border-radius: 10px;
}
.overflow-y-auto::-webkit-scrollbar-thumb:hover {
  background: rgba(59, 130, 246, 0.5);
}
</style>

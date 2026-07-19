<script setup lang="ts">
import { ref, computed, reactive, watchEffect, onMounted, onUnmounted } from 'vue';
import { useTrussStore } from '@/stores/useTrussStore';

const store = useTrussStore();

// Frases rotativas de status
const loadingPhrases = [
  'Analisando a estabilidade estrutural...',
  'Calculando a distribuição de esforços internos...',
  'Otimizando as seções transversais dos perfis...',
  'Avaliando o comportamento sob as cargas aplicadas...',
  'Verificando os limites de esbeltez e resistência...',
  'Simulando a interação da estrutura com os apoios...',
  'Processando múltiplas alternativas de materiais...',
  'Buscando a configuração de melhor custo-benefício...',
  'Verificando a conformidade com as normas técnicas...',
  'Realizando cálculos de deslocamentos e deformações...',
];

const currentPhraseIndex = ref(0);
let phraseInterval: ReturnType<typeof setInterval> | null = null;

onMounted(() => {
  phraseInterval = setInterval(() => {
    currentPhraseIndex.value = (currentPhraseIndex.value + 1) % loadingPhrases.length;
  }, 3000);
});

onUnmounted(() => {
  if (phraseInterval) clearInterval(phraseInterval);
  if (timerInterval) clearInterval(timerInterval);
});

// Temporizador de execução
const elapsedSeconds = ref(0);
let timerInterval: ReturnType<typeof setInterval> | null = null;

onMounted(() => {
  timerInterval = setInterval(() => {
    if (store.tempoInicio > 0) {
      elapsedSeconds.value = Math.floor((Date.now() - store.tempoInicio) / 1000);
    }
  }, 1000);
});

// Parsing dos logs acumulados agrupados por material
const materiaisLogs = computed(() => {
  if (!store.logsTexto) return {};
  const lines = store.logsTexto.split('\n').filter((l) => l.trim());
  const result: Record<string, string[]> = {};
  for (const line of lines) {
    const match = line.match(/^\[([^\]]+)\]\s*(.*)/);
    if (match) {
      const mat = match[1]!;
      const content = match[2] ?? '';
      if (!result[mat]) result[mat] = [];
      result[mat].push(content);
    }
  }
  return result;
});

const linhasGerais = computed(() => {
  if (!store.logsTexto) return [];
  const lines = store.logsTexto.split('\n').filter((l) => l.trim());
  return lines.filter((l) => !l.startsWith('['));
});

const materiaisOrdenados = computed(() => {
  const fromMeta = store.dadosProgresso.materiais_nomes as string[] | undefined;
  if (fromMeta && fromMeta.length) return fromMeta;
  return Object.keys(materiaisLogs.value);
});

// Status de cada material
const materiaisStatus = computed(() => {
  const dp = store.dadosProgresso;
  const names = dp.materiais_nomes as string[] | undefined;
  if (!names || !names.length) return {};

  const logs = materiaisLogs.value;
  const status: Record<string, string> = {};

  for (let i = 0; i < names.length; i++) {
    const name = names[i]!;
    const materialLines = logs[name] || [];
    const lastLine = materialLines[materialLines.length - 1] || '';

    if (lastLine.includes('Falhou')) {
      status[name] = 'erro';
    } else if (i < (dp.indice_material ?? 0)) {
      status[name] = 'concluido';
    } else if (i === (dp.indice_material ?? 0)) {
      status[name] = 'processando';
    } else {
      status[name] = 'aguardando';
    }
  }
  return status;
});

// Painéis expansíveis por material
const materiaisExpandidos = reactive(new Set<string>());

watchEffect(() => {
  const current = store.dadosProgresso.material_atual as string | undefined;
  if (current) {
    materiaisExpandidos.add(current);
  }
});

function toggleMaterial(name: string) {
  if (name === store.dadosProgresso.material_atual) return;
  if (materiaisExpandidos.has(name)) {
    materiaisExpandidos.delete(name);
  } else {
    materiaisExpandidos.add(name);
  }
}

function isExpanded(name: string): boolean {
  return materiaisExpandidos.has(name);
}

// Barra de resumo
const globalBestDisplay = computed(() => {
  const dp = store.dadosProgresso;
  const fit = dp.melhor_global_fitness;
  const mat = dp.melhor_global_material;
  if (fit != null && fit !== Infinity && mat) {
    return `R$ ${Number(fit).toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} (${mat})`;
  }
  return '—';
});

const currentMaterialDisplay = computed(() => {
  const dp = store.dadosProgresso;
  const mat = dp.material_atual;
  const gen = dp.geracao;
  const total = dp.total_geracoes;
  if (mat) {
    return `${mat}: ${gen}/${total}`;
  }
  return '—';
});

const elapsedDisplay = computed(() => {
  const s = elapsedSeconds.value;
  if (s <= 0) return '—';
  const min = Math.floor(s / 60);
  const sec = s % 60;
  if (min > 0) return `${min}m ${sec}s`;
  return `${sec}s`;
});

// Helpers por material
function getMaterialLines(name: string): string[] {
  return materiaisLogs.value[name] || [];
}

function getMaterialSummary(name: string): string {
  const lines = getMaterialLines(name);
  const last = lines[lines.length - 1] || '';
  const status = materiaisStatus.value[name];

  if (status === 'concluido') {
    const costMatch = last.match(/Custo:\s*R\$\s*([\d.]+)/);
    if (costMatch) return `R$ ${Number(costMatch[1]).toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
    return 'Concluído';
  }
  if (status === 'erro') {
    return 'Falhou';
  }
    if (status === 'processando') {
      const dp = store.dadosProgresso;
      const best = dp.melhor_do_material;
      if (best != null && best !== Infinity) {
        return `melhor: R$ ${Number(best).toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
      }
      return 'processando...';
    }
  return 'aguardando';
}

function getStatusDotClass(name: string): string {
  const status = materiaisStatus.value[name] || 'aguardando';
  switch (status) {
    case 'concluido':
      return 'bg-green-500 shadow-[0_0_8px_rgba(34,197,94,0.6)]';
    case 'erro':
      return 'bg-red-500 animate-pulse shadow-[0_0_8px_rgba(239,68,68,0.6)]';
    case 'processando':
      return 'bg-yellow-500 animate-pulse shadow-[0_0_8px_rgba(234,179,8,0.6)]';
    default:
      return 'bg-gray-500 shadow-[0_0_8px_rgba(107,114,128,0.4)]';
  }
}
</script>

<template>
  <div
    v-if="store.loading"
    class="fixed inset-0 z-[100] flex items-center justify-center bg-black/85 px-4 sm:px-6 text-center"
  >
    <div class="flex flex-col items-center w-full max-w-3xl">
      <!-- Spinner -->
      <div
        class="w-14 h-14 border-4 border-blue-500 border-t-transparent rounded-full animate-spin mb-6 shrink-0"
      ></div>

      <!-- Frase rotativa -->
      <p class="text-white text-lg font-bold mb-2">
        {{ loadingPhrases[currentPhraseIndex] }}
      </p>

      <!-- Barra de progresso global (agora considera todos os materiais) -->
      <div
        class="w-full max-w-sm bg-gray-700 rounded-full h-3 mb-4 overflow-hidden border border-gray-600"
      >
        <div
          class="bg-blue-500 h-3 rounded-full transition-all duration-500 ease-out shadow-[0_0_10px_rgba(59,130,246,0.5)]"
          :style="{ width: store.mainProgress + '%' }"
        ></div>
      </div>

      <!-- Barra de resumo (melhor global / material atual / tempo) -->
      <div
        class="w-full max-w-3xl bg-gray-900/80 border border-gray-700 rounded-lg px-4 py-2 mb-4 grid grid-cols-3 gap-2 text-xs sm:text-sm font-mono"
      >
        <div class="text-left text-gray-400 truncate">
          <span class="text-gray-500">Melhor:</span>
          <span class="text-green-400 ml-1">{{ globalBestDisplay }}</span>
        </div>
        <div class="text-center text-gray-400 truncate">
          <span class="text-gray-500">Processando:</span>
          <span class="text-yellow-400 ml-1">{{ currentMaterialDisplay }}</span>
        </div>
        <div class="text-right text-gray-400 truncate">
          <span class="text-gray-500">Tempo:</span>
          <span class="text-blue-300 ml-1">{{ elapsedDisplay }}</span>
        </div>
      </div>

      <!-- Aviso de timeout client-side (sem progresso por > 90s) -->
      <div
        v-if="store.showTimeoutWarning"
        class="w-full max-w-3xl bg-orange-900/30 border border-orange-700/50 rounded-lg px-4 py-2 mb-4 text-center text-xs"
      >
        <Icon name="lucide:alert-triangle" class="w-4 h-4 inline mr-1 text-orange-400" />
        <span class="text-orange-300 font-bold">Sem progresso há mais de 90 segundos.</span>
        <span class="text-orange-200 ml-1">
          Se o problema persistir, cancele e verifique o worker Celery.
        </span>
      </div>

      <!-- Painel de logs (agrupado por material com expansão) -->
      <div
        class="w-full text-left bg-black rounded-lg p-3 h-64 md:h-96 overflow-y-auto mb-6 text-xs sm:text-[13px] font-mono border border-gray-800 shadow-[inset_0_2px_15px_rgba(0,0,0,1)]"
      >
        <!-- Linhas gerais (sem prefixo de material, ex.: "Conectando...") -->
        <div v-if="linhasGerais.length" class="px-2 py-2 border-b border-white/5 mb-1">
          <div
            v-for="(line, idx) in linhasGerais"
            :key="'g-' + idx"
            class="text-gray-400 leading-relaxed"
          >
            <span class="text-gray-600 mr-2 select-none">›</span>
            {{ line }}
          </div>
        </div>

        <!-- Seções por material -->
        <div
          v-for="mat in materiaisOrdenados"
          :key="mat"
          class="border-b border-white/5 last:border-0"
        >
          <!-- Cabeçalho do material (clicável) -->
          <div
            class="flex items-center space-x-2.5 px-2 py-3 cursor-pointer hover:bg-white/5 transition-colors duration-200 rounded select-none"
            @click="toggleMaterial(mat)"
          >
            <span
              class="w-2.5 h-2.5 rounded-full shrink-0 transition-all duration-300"
              :class="getStatusDotClass(mat)"
            ></span>
            <span class="text-blue-400 font-bold truncate min-w-0 shrink-0" :title="mat">
              {{ mat }}
            </span>
            <span class="text-gray-500 text-xs truncate ml-2 min-w-0">
              {{ getMaterialSummary(mat) }}
            </span>
            <span class="ml-auto text-gray-600 shrink-0 text-xs">
              {{ isExpanded(mat) ? '▼' : '▶' }}
            </span>
          </div>

          <!-- Linhas de geração (só visíveis quando expandido) -->
          <div v-if="isExpanded(mat) && getMaterialLines(mat).length" class="pb-2">
            <div
              v-for="(line, idx) in getMaterialLines(mat)"
              :key="'l-' + idx"
              class="flex items-start px-2 py-0.5 hover:bg-white/[0.02]"
            >
              <span class="text-gray-600 mr-2 select-none shrink-0">›</span>
              <span class="text-gray-300 leading-relaxed break-words">{{ line }}</span>
            </div>
          </div>
        </div>

        <!-- Mensagem vazia (enquanto não há logs) -->
        <div
          v-if="!linhasGerais.length && !materiaisOrdenados.length"
          class="text-gray-500 text-center py-8"
        >
          <template v-if="store.dadosProgresso.status === 'EM_ANDAMENTO'">
            Processando primeira geração de avaliações estruturais...
          </template>
          <template v-else> Aguardando dados do servidor... </template>
        </div>
      </div>

      <!-- Botão de cancelamento -->
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

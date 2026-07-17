<script setup lang="ts">
// components/StatusWorkerIndicator.vue: Badge de status do worker Celery + CPU.
import { useTrussStore } from '@/stores/useTrussStore';
import { onMounted } from 'vue';

const store = useTrussStore();

onMounted(async () => {
  // Carrega health do servidor (CPU count) e diagnóstico do worker em paralelo.
  await Promise.all([store.verificarSaudeServidor(), store.verificarWorker()]);
});

const statusInfo = computed(() => {
  if (store.verificandoWorker) {
    return {
      label: 'Verificando...',
      dot: 'bg-gray-500 animate-pulse',
      text: 'text-gray-400',
      tooltip: 'Verificando disponibilidade do worker Celery.',
    };
  }
  if (store.workerHealth?.worker_disponivel) {
    return {
      label: 'Worker ativo',
      dot: 'bg-green-500 shadow-[0_0_8px_rgba(34,197,94,0.6)]',
      text: 'text-green-400',
      tooltip: 'Worker Celery respondendo. Análises podem ser iniciadas.',
    };
  }
  return {
    label: 'Worker offline',
    dot: 'bg-red-500 animate-pulse',
    text: 'text-red-400',
    tooltip:
      store.workerHealth?.erro ||
      'Worker Celery não responde. Verifique o container (docker compose ps worker).',
  };
});

const cpuInfo = computed(() => {
  const cpu = store.serverHealth?.cpu_count;
  if (!cpu) return '';
  return `${cpu} CPUs`;
});

const parallelInfo = computed(() => {
  const salud = store.serverHealth;
  if (!salud?.cpu_count) return '';
  return `Núcleos: ${salud.cpu_count}`;
});

async function reverify() {
  await Promise.all([store.verificarSaudeServidor(), store.verificarWorker()]);
}
</script>

<template>
  <div
    class="flex items-center justify-between gap-2 px-3 py-2 bg-gray-900/40 rounded-lg border border-gray-700/50"
  >
    <div class="flex items-center gap-2 min-w-0">
      <span
        :class="['w-2.5 h-2.5 rounded-full shrink-0 transition-all duration-300', statusInfo.dot]"
        :title="statusInfo.tooltip"
      ></span>
      <div class="min-w-0">
        <div :class="['text-[11px] font-bold truncate', statusInfo.text]">
          {{ statusInfo.label }}
        </div>
        <div class="text-[9px] text-gray-500 truncate">
          <span v-if="cpuInfo">{{ cpuInfo }}</span>
          <span v-if="cpuInfo && parallelInfo" class="mx-1">·</span>
          <span v-if="parallelInfo">{{ parallelInfo }}</span>
        </div>
      </div>
    </div>
    <button
      @click="reverify"
      :disabled="store.verificandoWorker"
      class="text-gray-400 hover:text-blue-400 p-1 rounded transition-colors disabled:opacity-50"
      title="Reverificar status"
    >
      <Icon
        name="lucide:refresh-cw"
        :class="['w-3.5 h-3.5', store.verificandoWorker ? 'animate-spin' : '']"
      />
    </button>
  </div>
</template>

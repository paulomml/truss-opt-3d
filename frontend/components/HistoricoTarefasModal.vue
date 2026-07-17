<script setup lang="ts">
// components/HistoricoTarefasModal.vue: Histórico de tarefas executadas.
import { useTrussStore } from '@/stores/useTrussStore';
import { computed } from 'vue';

const store = useTrussStore();

const props = defineProps<{ show: boolean }>();
const emit = defineEmits<{ (e: 'close'): void }>();

// Carrega histórico ao abrir.
watch(
  () => props.show,
  (show) => {
    if (show) {
      store.carregarHistorico(50);
    }
  },
);

const statusClass = (status: string): string => {
  switch (status) {
    case 'CONCLUIDO':
      return 'bg-green-900/50 text-green-300';
    case 'EM_ANDAMENTO':
      return 'bg-yellow-900/50 text-yellow-300';
    case 'PENDENTE':
      return 'bg-gray-700 text-gray-300';
    case 'FALHOU':
      return 'bg-red-900/50 text-red-300';
    case 'CANCELADO':
      return 'bg-orange-900/50 text-orange-300';
    default:
      return 'bg-gray-700 text-gray-300';
  }
};

function formatarData(dataIso: string | null | undefined): string {
  if (!dataIso) return '—';
  try {
    const d = new Date(dataIso);
    return d.toLocaleString('pt-BR', {
      day: '2-digit',
      month: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    });
  } catch {
    return '—';
  }
}

function formatarDurancia(
  criado: string | null | undefined,
  finalizado: string | null | undefined,
): string {
  if (!criado || !finalizado) return '—';
  try {
    const ms = new Date(finalizado).getTime() - new Date(criado).getTime();
    const s = Math.floor(ms / 1000);
    if (s < 60) return `${s}s`;
    const min = Math.floor(s / 60);
    return `${min}m ${s % 60}s`;
  } catch {
    return '—';
  }
}

const totalTarefas = computed(() => store.historicoTarefas.length);
const totalConcluidas = computed(
  () => store.historicoTarefas.filter((t) => t.status === 'CONCLUIDO').length,
);
</script>

<template>
  <Transition name="fade">
    <div
      v-if="show"
      class="fixed inset-0 z-[200] flex items-center justify-center bg-black/70 backdrop-blur-md p-4"
      @click.self="emit('close')"
    >
      <div
        class="bg-gray-800 border border-gray-700 rounded-xl shadow-2xl max-w-5xl w-full max-h-[85vh] overflow-hidden flex flex-col"
      >
        <!-- Cabeçalho -->
        <div class="p-5 border-b border-gray-700 flex justify-between items-center">
          <div>
            <h2 class="text-xl font-bold text-white">Histórico de Tarefas</h2>
            <p class="text-xs text-gray-400 mt-1">
              Últimas {{ totalTarefas }} tarefas registradas no banco de dados.
              <span v-if="totalTarefas > 0">
                {{ totalConcluidas }} concluídas ({{
                  Math.round((totalConcluidas / totalTarefas) * 100)
                }}%).
              </span>
            </p>
          </div>
          <button
            @click="emit('close')"
            class="text-gray-400 hover:text-white p-2 hover:bg-gray-700 rounded-lg transition-colors"
          >
            <Icon name="lucide:x" class="w-5 h-5" />
          </button>
        </div>

        <!-- Tabela -->
        <div class="overflow-auto flex-grow">
          <table class="w-full text-sm">
            <thead class="bg-gray-900/70 sticky top-0">
              <tr class="text-left text-gray-400 uppercase text-[10px]">
                <th class="p-3 font-semibold">ID</th>
                <th class="p-3 font-semibold">Status</th>
                <th class="p-3 font-semibold text-right">Progresso</th>
                <th class="p-3 font-semibold">Criado em</th>
                <th class="p-3 font-semibold">Duração</th>
                <th class="p-3 font-semibold">Mensagem</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="t in store.historicoTarefas"
                :key="t.task_id"
                class="border-t border-gray-700/50 hover:bg-gray-700/30 transition-colors"
              >
                <td class="p-3 font-mono text-blue-400 text-xs">#{{ t.task_id }}</td>
                <td class="p-3">
                  <span
                    :class="['px-2 py-0.5 rounded text-[10px] font-bold', statusClass(t.status)]"
                  >
                    {{ t.status }}
                  </span>
                </td>
                <td class="p-3 text-right font-mono text-gray-200">
                  {{ t.progresso.toFixed(0) }}%
                </td>
                <td class="p-3 text-xs text-gray-300">{{ formatarData(t.criado_em) }}</td>
                <td class="p-3 text-xs text-gray-300">
                  {{ formatarDurancia(t.criado_em, t.finalizado_em) }}
                </td>
                <td class="p-3 text-xs text-gray-400 max-w-xs truncate" :title="t.mensagem || ''">
                  {{ t.mensagem || '—' }}
                </td>
              </tr>
              <tr v-if="!store.historicoTarefas.length">
                <td colspan="6" class="p-8 text-center text-gray-500 italic">
                  <span v-if="store.carregandoHistorico">Carregando...</span>
                  <span v-else>Nenhuma tarefa registrada.</span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <!-- Rodapé -->
        <div class="p-4 border-t border-gray-700 text-xs text-gray-400">
          <div class="flex justify-between items-center">
            <button
              @click="store.carregarHistorico(50)"
              :disabled="store.carregandoHistorico"
              class="px-3 py-1.5 bg-gray-700 hover:bg-gray-600 text-white rounded text-xs font-bold disabled:opacity-50"
            >
              <Icon name="lucide:refresh-cw" class="w-3 h-3 inline mr-1" />
              Atualizar
            </button>
            <button
              @click="emit('close')"
              class="px-4 py-2 bg-gray-700 hover:bg-gray-600 text-white rounded-lg text-xs font-bold"
            >
              Fechar
            </button>
          </div>
        </div>
      </div>
    </div>
  </Transition>
</template>

<style scoped>
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>

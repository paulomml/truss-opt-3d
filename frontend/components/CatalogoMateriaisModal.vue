<script setup lang="ts">
// Catálogo completo de materiais.
import { useTrussStore } from '@/stores/useTrussStore';

const store = useTrussStore();

const props = defineProps<{ show: boolean }>();
const emit = defineEmits<{ (e: 'close'): void }>();

// Carrega materiais ao abrir pela primeira vez.
watch(
  () => props.show,
  (show) => {
    if (show && store.materiais.length === 0) {
      store.carregarMateriais();
    }
  },
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
        class="bg-gray-800 border border-gray-700 rounded-xl shadow-2xl max-w-4xl w-full max-h-[85vh] overflow-hidden flex flex-col"
      >
        <!-- Cabeçalho -->
        <div class="p-5 border-b border-gray-700 flex justify-between items-center">
          <div>
            <h2 class="text-xl font-bold text-white">Catálogo de Materiais</h2>
            <p class="text-xs text-gray-400 mt-1">
              Aços estruturais disponíveis no sistema (ativos no banco de dados).
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
                <th class="p-3 font-semibold">Nome</th>
                <th class="p-3 font-semibold">Norma</th>
                <th class="p-3 font-semibold text-right">E (GPa)</th>
                <th class="p-3 font-semibold text-right">fy (MPa)</th>
                <th class="p-3 font-semibold text-right">fu (MPa)</th>
                <th class="p-3 font-semibold text-right">ρ (kg/m³)</th>
                <th class="p-3 font-semibold text-right">Custo (R$/kg)</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="mat in store.materiais"
                :key="mat.id"
                class="border-t border-gray-700/50 hover:bg-gray-700/30 transition-colors"
              >
                <td class="p-3 font-bold text-blue-400">{{ mat.nome }}</td>
                <td class="p-3 text-gray-300 text-xs">{{ mat.norma_referencia || '—' }}</td>
                <td class="p-3 text-right font-mono text-gray-200">{{ mat.e_gpa.toFixed(1) }}</td>
                <td class="p-3 text-right font-mono text-gray-200">{{ mat.fy_mpa.toFixed(0) }}</td>
                <td class="p-3 text-right font-mono text-gray-200">{{ mat.fu_mpa.toFixed(0) }}</td>
                <td class="p-3 text-right font-mono text-gray-200">
                  {{ mat.rho_kg_m3.toFixed(0) }}
                </td>
                <td class="p-3 text-right font-mono text-green-400">
                  R$ {{ mat.custo_kg.toFixed(2) }}
                </td>
              </tr>
              <tr v-if="!store.materiais.length">
                <td colspan="7" class="p-8 text-center text-gray-500 italic">
                  Nenhum material cadastrado.
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <!-- Rodapé -->
        <div class="p-4 border-t border-gray-700 text-xs text-gray-400">
          <div class="flex justify-between items-center">
            <span>{{ store.materiais.length }} materiais ativos</span>
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

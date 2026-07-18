<script setup lang="ts">
// Catálogo completo de perfis.
import { useTrussStore } from '@/stores/useTrussStore';
import { ref, computed } from 'vue';

const store = useTrussStore();

const props = defineProps<{ show: boolean }>();
const emit = defineEmits<{ (e: 'close'): void }>();

// Filtro de família selecionado (vazio = todas).
const familiaFiltro = ref<string>('');

// Carrega perfis ao abrir.
watch(
  () => props.show,
  (show) => {
    if (show && store.perfis.length === 0) {
      store.carregarPerfis();
    }
  },
);

const familiasDisponiveis = computed(() => {
  return [...new Set(store.perfis.map((p) => p.familia))].sort();
});

const perfisFiltrados = computed(() => {
  if (!familiaFiltro.value) return store.perfis;
  return store.perfis.filter((p) => p.familia === familiaFiltro.value);
});

// Formata área em cm^2 (mais legível que m^2).
function formatarAreaCm2(area_m2: number): string {
  return (area_m2 * 1e4).toFixed(2);
}

// Formata momento de inércia em cm^4.
function formatarInerciaCm4(i_m4: number): string {
  return (i_m4 * 1e8).toFixed(2);
}
</script>

<template>
  <Transition name="fade">
    <div
      v-if="show"
      class="fixed inset-0 z-[200] flex items-center justify-center bg-black/70 backdrop-blur-md p-4"
      @click.self="emit('close')"
    >
      <div
        class="bg-gray-800 border border-gray-700 rounded-xl shadow-2xl max-w-6xl w-full max-h-[85vh] overflow-hidden flex flex-col"
      >
        <!-- Cabeçalho -->
        <div class="p-5 border-b border-gray-700 flex justify-between items-center">
          <div>
            <h2 class="text-xl font-bold text-white">Catálogo de Perfis</h2>
            <p class="text-xs text-gray-400 mt-1">
              Perfis estruturais disponíveis (cantoneiras L, tubos RHS, U enrijecido Ue).
            </p>
          </div>
          <button
            @click="emit('close')"
            class="text-gray-400 hover:text-white p-2 hover:bg-gray-700 rounded-lg transition-colors"
          >
            <Icon name="lucide:x" class="w-5 h-5" />
          </button>
        </div>

        <!-- Filtros -->
        <div class="p-3 border-b border-gray-700 bg-gray-900/30 flex items-center gap-2 flex-wrap">
          <span class="text-xs text-gray-400 uppercase font-bold">Filtrar família:</span>
          <button
            @click="familiaFiltro = ''"
            :class="[
              'px-3 py-1 rounded text-xs font-bold transition',
              familiaFiltro === ''
                ? 'bg-blue-600 text-white'
                : 'bg-gray-700 text-gray-300 hover:bg-gray-600',
            ]"
          >
            Todas
          </button>
          <button
            v-for="fam in familiasDisponiveis"
            :key="fam"
            @click="familiaFiltro = fam"
            :class="[
              'px-3 py-1 rounded text-xs font-bold transition',
              familiaFiltro === fam
                ? 'bg-blue-600 text-white'
                : 'bg-gray-700 text-gray-300 hover:bg-gray-600',
            ]"
          >
            {{ fam }}
          </button>
        </div>

        <!-- Tabela -->
        <div class="overflow-auto flex-grow">
          <table class="w-full text-sm">
            <thead class="bg-gray-900/70 sticky top-0">
              <tr class="text-left text-gray-400 uppercase text-[10px]">
                <th class="p-3 font-semibold">Nome</th>
                <th class="p-3 font-semibold">Família</th>
                <th class="p-3 font-semibold text-right">h (mm)</th>
                <th class="p-3 font-semibold text-right">bf (mm)</th>
                <th class="p-3 font-semibold text-right">t (mm)</th>
                <th class="p-3 font-semibold text-right">Área (cm²)</th>
                <th class="p-3 font-semibold text-right">Ix (cm⁴)</th>
                <th class="p-3 font-semibold text-right">Iy (cm⁴)</th>
                <th class="p-3 font-semibold text-right">J (cm⁴)</th>
                <th class="p-3 font-semibold">Uso</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="perfil in perfisFiltrados"
                :key="perfil.id"
                class="border-t border-gray-700/50 hover:bg-gray-700/30 transition-colors"
              >
                <td class="p-3 font-bold text-blue-400">{{ perfil.nome }}</td>
                <td class="p-3">
                  <span
                    class="px-2 py-0.5 rounded text-[10px] font-bold"
                    :class="{
                      'bg-purple-900/50 text-purple-300': perfil.familia === 'L',
                      'bg-blue-900/50 text-blue-300': perfil.familia === 'RHS',
                      'bg-green-900/50 text-green-300': perfil.familia === 'Ue',
                      'bg-gray-700 text-gray-300': !['L', 'RHS', 'Ue'].includes(perfil.familia),
                    }"
                  >
                    {{ perfil.familia }}
                  </span>
                </td>
                <td class="p-3 text-right font-mono text-gray-200">{{ perfil.h_mm.toFixed(0) }}</td>
                <td class="p-3 text-right font-mono text-gray-200">
                  {{ perfil.bf_mm.toFixed(0) }}
                </td>
                <td class="p-3 text-right font-mono text-gray-200">{{ perfil.t_mm.toFixed(2) }}</td>
                <td class="p-3 text-right font-mono text-gray-200">
                  {{ formatarAreaCm2(perfil.area_m2) }}
                </td>
                <td class="p-3 text-right font-mono text-gray-200">
                  {{ formatarInerciaCm4(perfil.ix_m4) }}
                </td>
                <td class="p-3 text-right font-mono text-gray-200">
                  {{ formatarInerciaCm4(perfil.iy_m4) }}
                </td>
                <td class="p-3 text-right font-mono text-gray-200">
                  {{ formatarInerciaCm4(perfil.j_m4) }}
                </td>
                <td class="p-3 text-xs text-gray-400">{{ perfil.uso_recomendado || '—' }}</td>
              </tr>
              <tr v-if="!perfisFiltrados.length">
                <td colspan="10" class="p-8 text-center text-gray-500 italic">
                  Nenhum perfil encontrado.
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <!-- Rodapé -->
        <div class="p-4 border-t border-gray-700 text-xs text-gray-400">
          <div class="flex justify-between items-center">
            <span>{{ perfisFiltrados.length }} perfis exibidos</span>
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

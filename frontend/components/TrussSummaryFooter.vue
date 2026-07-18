<script setup lang="ts">
import { computed, ref, onMounted } from 'vue';
import { useTrussStore } from '@/stores/useTrussStore';
import { getCylinderData, formatarNumero, formatarMoeda } from '@/utils/truss3d';
import type { BarraResultado, NoResultado } from '@/types/truss';

const store = useTrussStore();

const trussResult = computed(() => store.result);

const isExpanded = ref(true);
const isMobile = ref(false);

onMounted(() => {
  const mql = window.matchMedia('(max-width: 1023px)');
  isMobile.value = mql.matches;
  isExpanded.value = !mql.matches;
  mql.addEventListener('change', (e) => {
    isMobile.value = e.matches;
    if (!e.matches) isExpanded.value = true;
  });
});

const getMemberLength = (member: BarraResultado, nodes: Record<string, NoResultado>): number => {
  const directLength = (member as any).length;
  if (typeof directLength === 'number' && directLength >= 0) return directLength;
  return getCylinderData(member, nodes).length ?? 0;
};

const totalMembers = computed(() => trussResult.value?.members?.length ?? 0);
const totalNodes = computed(() =>
  trussResult.value?.nodes ? Object.keys(trussResult.value.nodes).length : 0,
);

const totalLength = computed(() => {
  if (!trussResult.value?.members?.length || !trussResult.value?.nodes) return 0;
  return trussResult.value.members.reduce(
    (acc, m) => acc + getMemberLength(m, trussResult.value!.nodes),
    0,
  );
});

const flechaRatio = computed(() => {
  const r = trussResult.value;
  if (!r || !r.real_span || !r.max_deflection) return null;
  const ratio = r.real_span / r.max_deflection;
  return `L/${Math.round(ratio)}`;
});

function formatarTempo(segundos: number): string {
  if (!segundos) return '—';
  const min = Math.floor(segundos / 60);
  const seg = Math.round(segundos % 60);
  if (min > 0) return `${min}m ${seg}s`;
  return `${seg}s`;
}

function formatarPeso(valor: number): string {
  if (valor >= 1000) return `${(valor / 1000).toFixed(2)} t`;
  return `${formatarNumero(valor)} kg`;
}

const baixarMemorial = (formato: 'pdf' | 'docx') => {
  store.baixarMemorial(formato);
};
</script>

<template>
  <Transition name="footer-slide">
    <footer
      v-if="trussResult && !(isMobile && store.showMobileMenu)"
      class="fixed bottom-0 right-0 z-40 w-full lg:left-80 lg:w-auto"
    >
      <div
        class="relative bg-gray-800/95 backdrop-blur-md border-t border-gray-700 shadow-[0_-10px_20px_-5px_rgba(0,0,0,0.3)]"
      >
        <!-- Legenda de cores (acima do footer, move junto com ele) -->
        <div
          v-if="trussResult"
          class="absolute bottom-full left-4 z-[45] bg-gray-800/90 backdrop-blur-sm rounded-lg shadow-lg p-3 mb-2"
        >
          <div class="text-[10px] text-gray-300 font-bold mb-2 uppercase">
            {{ store.modoVisualizacao === 'tensao' ? 'Utilização' : 'Deslocamento' }}
          </div>
          <div
            class="w-40 h-3 rounded-full mb-1 bg-gradient-to-r from-blue-500 via-green-500 via-yellow-500 to-red-500"
          />
          <div class="flex justify-between text-[9px] text-gray-400">
            <span>0%</span>
            <span>50%</span>
            <span>80%</span>
            <span>100%</span>
          </div>
        </div>
        <!-- Header clicável para toggle (sempre visível) -->
        <div
          @click="isExpanded = !isExpanded"
          class="flex items-center justify-between px-4 py-2 cursor-pointer select-none hover:bg-white/[0.03] transition-colors"
        >
          <div class="text-xs text-gray-400 font-bold uppercase tracking-wider">
            Resumo da Análise
            <span v-if="trussResult.is_structurally_stable" class="ml-2 text-green-400"
              >✓ Estável</span
            >
            <span v-else class="ml-2 text-red-400">✗ Instável</span>
          </div>
          <div class="flex items-center gap-2">
            <span class="text-[10px] text-gray-500 hidden xs:inline">
              {{ isExpanded ? 'Recolher' : 'Expandir' }}
            </span>
            <Icon
              :name="isExpanded ? 'lucide:chevron-down' : 'lucide:chevron-up'"
              class="w-4 h-4 text-gray-400 transition-transform duration-300"
            />
          </div>
        </div>

        <!-- Conteúdo colapsável com toggle via CSS puro -->
        <div :class="['summary-cards', isExpanded ? 'expanded' : 'collapsed']">
          <div class="px-4 pb-2 space-y-3">
            <!-- Primeira fileira: principais indicadores -->
            <div class="grid grid-cols-1 xs:grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
              <div class="bg-gray-900/50 rounded-lg p-2">
                <div class="text-[10px] text-gray-400 uppercase">Peso Total</div>
                <div class="text-base lg:text-lg font-bold text-blue-400 font-mono">
                  {{ formatarPeso(trussResult.total_weight) }}
                </div>
              </div>
              <div class="bg-gray-900/50 rounded-lg p-2">
                <div class="text-[10px] text-gray-400 uppercase">Custo Estimado</div>
                <div class="text-base lg:text-lg font-bold text-green-400 font-mono">
                  {{ formatarMoeda(trussResult.total_cost) }}
                </div>
              </div>
              <div class="bg-gray-900/50 rounded-lg p-2">
                <div class="text-[10px] text-gray-400 uppercase">Material</div>
                <div class="text-base lg:text-lg font-bold text-white font-mono">
                  {{ trussResult.winning_material }}
                </div>
              </div>
              <div class="bg-gray-900/50 rounded-lg p-2">
                <div class="text-[10px] text-gray-400 uppercase">Utilização Máx.</div>
                <div
                  :class="[
                    'text-base lg:text-lg font-bold font-mono',
                    trussResult.max_utilization > 1 ? 'text-red-400' : 'text-green-400',
                  ]"
                >
                  {{ formatarNumero(trussResult.max_utilization * 100, 1) }}%
                </div>
              </div>
              <div class="bg-gray-900/50 rounded-lg p-2">
                <div class="text-[10px] text-gray-400 uppercase">Contra-flecha</div>
                <div class="text-base lg:text-lg font-bold text-yellow-400 font-mono">
                  {{ formatarNumero(trussResult.precamber * 1000, 1) }} mm
                </div>
              </div>
            </div>

            <!-- Segunda fileira: indicadores complementares -->
            <div class="grid grid-cols-1 xs:grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
              <div class="bg-gray-900/50 rounded-lg p-2">
                <div class="text-[10px] text-gray-400 uppercase">Flecha Máxima</div>
                <div class="text-base lg:text-lg font-bold text-yellow-400 font-mono">
                  {{ formatarNumero(trussResult.max_deflection * 1000, 1) }} mm
                </div>
                <div v-if="flechaRatio" class="text-[10px] text-gray-500 mt-0.5">
                  {{ flechaRatio }}
                </div>
              </div>
              <div class="bg-gray-900/50 rounded-lg p-2">
                <div class="text-[10px] text-gray-400 uppercase">Vão Real</div>
                <div class="text-base lg:text-lg font-bold text-white font-mono">
                  {{ formatarNumero(trussResult.real_span, 1) }} m
                </div>
              </div>
              <div class="bg-gray-900/50 rounded-lg p-2">
                <div class="text-[10px] text-gray-400 uppercase">Perfis Distintos</div>
                <div class="text-base lg:text-lg font-bold text-blue-400 font-mono">
                  {{ trussResult.num_perfis_distintos }}
                </div>
              </div>
              <div class="bg-gray-900/50 rounded-lg p-2">
                <div class="text-[10px] text-gray-400 uppercase">Gerações</div>
                <div class="text-base lg:text-lg font-bold text-gray-300 font-mono">
                  {{ trussResult.geracoes_executadas }}
                </div>
              </div>
              <div class="bg-gray-900/50 rounded-lg p-2">
                <div class="text-[10px] text-gray-400 uppercase">Tempo de Análise</div>
                <div class="text-base lg:text-lg font-bold text-gray-300 font-mono">
                  {{ formatarTempo(trussResult.tempo_execucao_segundos) }}
                </div>
              </div>
            </div>

            <!-- Fileira de metadados da estrutura -->
            <div class="grid grid-cols-1 xs:grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
              <div class="bg-gray-900/50 rounded-lg p-2">
                <div class="text-[10px] text-gray-400 uppercase">Barras</div>
                <div class="text-sm font-bold text-gray-300 font-mono">
                  {{ totalMembers }}
                </div>
              </div>
              <div class="bg-gray-900/50 rounded-lg p-2">
                <div class="text-[10px] text-gray-400 uppercase">Nós</div>
                <div class="text-sm font-bold text-gray-300 font-mono">
                  {{ totalNodes }}
                </div>
              </div>
              <div class="bg-gray-900/50 rounded-lg p-2 sm:col-span-2 lg:col-span-3">
                <div class="text-[10px] text-gray-400 uppercase">Comprimento Total de Barras</div>
                <div class="text-sm font-bold text-gray-300 font-mono">
                  {{ formatarNumero(totalLength, 1) }} m
                </div>
              </div>
            </div>
          </div>

          <!-- Botões de Memorial -->
          <div
            v-if="trussResult.is_structurally_stable"
            class="px-4 pb-2 flex flex-wrap gap-2 justify-center lg:justify-end"
          >
            <button
              @click="baixarMemorial('pdf')"
              class="flex items-center gap-1.5 bg-red-600 hover:bg-red-700 text-white text-xs font-bold py-1.5 px-3 rounded-lg"
            >
              <Icon name="lucide:file-text" class="w-4 h-4" />
              Memorial PDF
            </button>
            <button
              @click="baixarMemorial('docx')"
              class="flex items-center gap-1.5 bg-blue-600 hover:bg-blue-700 text-white text-xs font-bold py-1.5 px-3 rounded-lg"
            >
              <Icon name="lucide:file-text" class="w-4 h-4" />
              Memorial Word
            </button>
          </div>
        </div>
      </div>
    </footer>
  </Transition>
</template>

<style scoped>
.footer-slide-enter-active,
.footer-slide-leave-active {
  transition:
    transform 0.3s ease-in-out,
    opacity 0.3s ease-in-out;
}
.footer-slide-enter-from,
.footer-slide-leave-to {
  transform: translateY(100%);
  opacity: 0;
}

.summary-cards {
  transition:
    max-height 0.3s ease,
    opacity 0.3s ease,
    padding 0.3s ease;
  overflow: hidden;
}
.summary-cards.collapsed {
  max-height: 0;
  opacity: 0;
  padding-top: 0;
  padding-bottom: 0;
  pointer-events: none;
}
.summary-cards.expanded {
  max-height: 2000px;
  opacity: 1;
}
</style>

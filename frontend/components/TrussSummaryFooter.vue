<script setup lang="ts">
import { computed, ref, onMounted, onBeforeUnmount } from "vue";
import { useTrussStore } from "@/stores/useTrussStore";
import { getCylinderData, formatarNumero, formatarMoeda } from "@/utils/truss3d";
import type { BarraResultado, NoResultado } from "@/types/truss";

const store = useTrussStore();
const isExpanded = ref(false);
const isMobile = ref(false);

onMounted(() => {
  const checkMobile = () => {
    isMobile.value = window.innerWidth < 768;
    if (window.innerWidth >= 1024) isExpanded.value = true;
    else isExpanded.value = false;
  };
  checkMobile();
  window.addEventListener("resize", checkMobile);
  onBeforeUnmount(() => window.removeEventListener("resize", checkMobile));
});

const trussResult = computed(() => store.result);

const getMemberLength = (member: BarraResultado, nodes: Record<string, NoResultado>): number => {
  const directLength = (member as any).length;
  if (typeof directLength === "number" && directLength >= 0) return directLength;
  return getCylinderData(member, nodes).length ?? 0;
};

const totalMembers = computed(() => trussResult.value?.members?.length ?? 0);
const totalNodes = computed(() => trussResult.value?.nodes ? Object.keys(trussResult.value.nodes).length : 0);

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
  if (!segundos) return "—";
  const min = Math.floor(segundos / 60);
  const seg = Math.round(segundos % 60);
  if (min > 0) return `${min}m ${seg}s`;
  return `${seg}s`;
}

function formatarPeso(valor: number): string {
  if (valor >= 1000) return `${(valor / 1000).toFixed(2)} t`;
  return `${formatarNumero(valor)} kg`;
}

const baixarMemorial = (formato: "pdf" | "docx") => {
  store.baixarMemorial(formato);
};
</script>

<template>
  <footer
    v-if="trussResult"
    :class="[
      'bg-gray-800/95 backdrop-blur-md border-t border-gray-700 transition-all duration-300',
      isExpanded ? 'max-h-[32rem]' : 'max-h-14',
      isMobile && store.showMobileMenu ? 'hidden' : 'block',
    ]"
  >
    <div class="px-4 py-2">
      <button
        @click="isExpanded = !isExpanded"
        class="w-full flex items-center justify-between text-xs text-gray-400 hover:text-white"
      >
        <span class="font-bold uppercase tracking-wider">
          Resumo da Análise
          <span v-if="trussResult.is_structurally_stable" class="ml-2 text-green-400">✓ Estável</span>
          <span v-else class="ml-2 text-red-400">✗ Instável</span>
        </span>
        <Icon :name="isExpanded ? 'lucide:chevron-down' : 'lucide:chevron-up'" class="w-4 h-4" />
      </button>

      <div v-if="isExpanded" class="mt-3 space-y-3">
        <!-- Primeira fileira: principais indicadores -->
        <div class="grid grid-cols-2 md:grid-cols-5 gap-3">
          <div class="bg-gray-900/50 rounded-lg p-2">
            <div class="text-[10px] text-gray-400 uppercase">Peso Total</div>
            <div class="text-lg font-bold text-blue-400 font-mono">
              {{ formatarPeso(trussResult.total_weight) }}
            </div>
          </div>
          <div class="bg-gray-900/50 rounded-lg p-2">
            <div class="text-[10px] text-gray-400 uppercase">Custo Estimado</div>
            <div class="text-lg font-bold text-green-400 font-mono">
              {{ formatarMoeda(trussResult.total_cost) }}
            </div>
          </div>
          <div class="bg-gray-900/50 rounded-lg p-2">
            <div class="text-[10px] text-gray-400 uppercase">Material</div>
            <div class="text-lg font-bold text-white font-mono">
              {{ trussResult.winning_material }}
            </div>
          </div>
          <div class="bg-gray-900/50 rounded-lg p-2">
            <div class="text-[10px] text-gray-400 uppercase">Utilização Máx.</div>
            <div
              :class="[
                'text-lg font-bold font-mono',
                trussResult.max_utilization > 1 ? 'text-red-400' : 'text-green-400',
              ]"
            >
              {{ formatarNumero(trussResult.max_utilization * 100, 1) }}%
            </div>
          </div>
          <div class="bg-gray-900/50 rounded-lg p-2">
            <div class="text-[10px] text-gray-400 uppercase">Contra-flecha</div>
            <div class="text-lg font-bold text-yellow-400 font-mono">
              {{ formatarNumero(trussResult.precamber * 1000, 1) }} mm
            </div>
          </div>
        </div>

        <!-- Segunda fileira: indicadores complementares -->
        <div class="grid grid-cols-2 md:grid-cols-5 gap-3">
          <div class="bg-gray-900/50 rounded-lg p-2">
            <div class="text-[10px] text-gray-400 uppercase">Flecha Máxima</div>
            <div class="text-lg font-bold text-yellow-400 font-mono">
              {{ formatarNumero(trussResult.max_deflection * 1000, 1) }} mm
            </div>
            <div v-if="flechaRatio" class="text-[10px] text-gray-500 mt-0.5">
              {{ flechaRatio }}
            </div>
          </div>
          <div class="bg-gray-900/50 rounded-lg p-2">
            <div class="text-[10px] text-gray-400 uppercase">Vão Real</div>
            <div class="text-lg font-bold text-white font-mono">
              {{ formatarNumero(trussResult.real_span, 1) }} m
            </div>
          </div>
          <div class="bg-gray-900/50 rounded-lg p-2">
            <div class="text-[10px] text-gray-400 uppercase">Perfis Distintos</div>
            <div class="text-lg font-bold text-blue-400 font-mono">
              {{ trussResult.num_perfis_distintos }}
            </div>
          </div>
          <div class="bg-gray-900/50 rounded-lg p-2">
            <div class="text-[10px] text-gray-400 uppercase">Gerações</div>
            <div class="text-lg font-bold text-gray-300 font-mono">
              {{ trussResult.geracoes_executadas }}
            </div>
          </div>
          <div class="bg-gray-900/50 rounded-lg p-2">
            <div class="text-[10px] text-gray-400 uppercase">Tempo de Análise</div>
            <div class="text-lg font-bold text-gray-300 font-mono">
              {{ formatarTempo(trussResult.tempo_execucao_segundos) }}
            </div>
          </div>
        </div>

        <!-- Fileira de metadados da estrutura -->
        <div class="grid grid-cols-2 md:grid-cols-5 gap-3">
          <div class="bg-gray-900/50 rounded-lg p-2 col-span-1">
            <div class="text-[10px] text-gray-400 uppercase">Barras</div>
            <div class="text-sm font-bold text-gray-300 font-mono">
              {{ totalMembers }}
            </div>
          </div>
          <div class="bg-gray-900/50 rounded-lg p-2 col-span-1">
            <div class="text-[10px] text-gray-400 uppercase">Nós</div>
            <div class="text-sm font-bold text-gray-300 font-mono">
              {{ totalNodes }}
            </div>
          </div>
          <div class="bg-gray-900/50 rounded-lg p-2 md:col-span-3">
            <div class="text-[10px] text-gray-400 uppercase">Comprimento Total de Barras</div>
            <div class="text-sm font-bold text-gray-300 font-mono">
              {{ formatarNumero(totalLength, 1) }} m
            </div>
          </div>
        </div>
      </div>

      <!-- Botões de Memorial -->
      <div v-if="isExpanded && trussResult.is_structurally_stable" class="mt-3 flex gap-2 justify-end">
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
  </footer>
</template>

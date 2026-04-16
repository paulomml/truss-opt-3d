<script setup lang="ts">
import { useTrussStore } from "@/stores/useTrussStore";
import { storeToRefs } from "pinia";

const store = useTrussStore();
const { form, loading, showMobileMenu } = storeToRefs(store);

// Catálogo de tipologias estruturais disponíveis para o design paramétrico.
// As opções abrangem desde coberturas residenciais até torres de transmissão e pontes.
const templateCategories = [
  {
    label: "Coberturas (Roof)",
    options: [
      { value: "pratt_roof", label: "Tesoura Pratt" },
      { value: "howe_roof", label: "Tesoura Howe" },
      { value: "fink_roof", label: "Tesoura Fink" },
    ],
  },
  {
    label: "Pontes (Bridge)",
    options: [
      { value: "warren_bridge", label: "Ponte Warren" },
      { value: "pratt_bridge", label: "Ponte Pratt" },
    ],
  },
  {
    label: "Torres (Tower)",
    options: [
      { value: "square_tower", label: "Torre Quadrada" },
      { value: "triangular_tower", label: "Torre Triangular" },
    ],
  },
  {
    label: "Balanços (Cantilever)",
    options: [
      { value: "cantilever_pratt", label: "Balanço Pratt" },
      { value: "cantilever_warren", label: "Balanço Warren" },
    ],
  },
];

// Lógica condicional para ativação de campos baseada na topologia selecionada.
// Portanto, parâmetros irrelevantes para certos modelos são desabilitados para evitar inconsistências.
const isSpanActive = computed(() => {
  return !form.value.selectedTemplate.includes("tower");
});

const isPanelsActive = computed(() => {
  return !form.value.selectedTemplate.includes("fink");
});

const isTopWidthActive = computed(() => {
  return form.value.selectedTemplate.includes("tower");
});

const isSectionsActive = computed(() => {
  return form.value.selectedTemplate.includes("tower");
});

const isMobile = ref(false);
onMounted(() => {
  isMobile.value = window.innerWidth < 768;
  window.addEventListener("resize", () => {
    isMobile.value = window.innerWidth < 768;
  });
});

// Verificação heurística de esbeltez e estabilidade preliminar.
// Sendo assim, o sistema alerta o usuário caso a geometria proposta apresente riscos óbvios de instabilidade global.
const corrosionAnalysis = computed(() => {
  if (form.value.total_load > 20000 && form.value.height < 1.5) {
    return {
      visible: true,
      message:
        "Atenção: Relação de esbeltez crítica detectada. Recomenda-se elevar a altura da treliça para mitigar os esforços axiais nos banzos.",
      type: "warning",
    };
  }
  return { visible: false };
});

const optimizeAndCloseMobile = () => {
  store.optimize();
  if (isMobile.value) {
    store.showMobileMenu = false;
  }
};

const resetParameters = () => {
  // Restauração das condições iniciais de projeto para recalibração do modelo.
  store.form.length = 12.0;
  store.form.height = 2.5;
  store.form.width = 2.0;
  store.form.divisions = 6;
  store.form.total_load = 10000.0;
  store.form.topWidth = 1.0;
  store.form.sections = 5;
  store.form.soil_type = "Rocha";
  store.form.custom_ks = 80000;
  store.form.footing_b = 0.6;
  store.form.footing_l = 0.6;
  store.optimize();
};

/**
 * Sanitização automática de inputs no evento de blur.
 * Garante que valores críticos nunca sejam nulos ou fora dos limites físicos de segurança.
 */
const sanitizeInput = (field: keyof typeof store.form, min: number) => {
  const value = store.form[field];
  if (typeof value === "number") {
    store.form[field] = Math.max(min, value) as any;
  }
};
</script>

<template>
  <aside
    :class="[
      'fixed inset-y-0 left-0 z-50 w-full md:w-80 bg-gray-800 border-r border-gray-700 shadow-2xl transition-transform duration-300 ease-in-out md:translate-x-0 md:static',
      showMobileMenu ? 'translate-x-0' : '-translate-x-full',
    ]"
  >
    <div class="h-full flex flex-col">
      <!-- Cabeçalho do Painel de Controle -->
      <div
        class="p-6 border-b border-gray-700 bg-gray-900/50 flex justify-between items-center"
      >
        <div>
          <h1 class="text-xl font-bold text-white">TRUSS-OPT 3D</h1>
          <p
            class="text-xs text-white opacity-80 mt-1 uppercase tracking-wider"
          >
            Otimizador Estrutural Paramétrico
          </p>
          <p class="text-[10px] text-blue-400/80 mt-1 font-medium">
            Desenvolvido por Paulo Raí Lopes de Melo
          </p>
        </div>
        <button
          v-if="isMobile"
          @click="showMobileMenu = false"
          class="p-2 text-gray-400 hover:text-white transition"
        >
          <Icon name="lucide:x" class="w-6 h-6" />
        </button>
      </div>

      <!-- Área de Input de Parâmetros Geométricos -->
      <div class="p-4 md:p-6 space-y-4 flex-grow overflow-y-auto">
        <!-- Seleção de Tipologia -->
        <div>
          <label class="block text-sm font-semibold text-gray-200 mb-2"
            >Modelo de Estrutura</label
          >
          <select
            v-model="store.form.selectedTemplate"
            class="w-full bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 focus:ring-2 focus:ring-blue-500 outline-none text-sm text-white"
          >
            <optgroup
              v-for="cat in templateCategories"
              :key="cat.label"
              :label="cat.label"
            >
              <option
                v-for="opt in cat.options"
                :key="opt.value"
                :value="opt.value"
              >
                {{ opt.label }}
              </option>
            </optgroup>
          </select>
        </div>

        <!-- Definição de Dimensões Reais -->
        <div class="grid grid-cols-1 gap-4">
          <!-- Vão Livre -->
          <div :class="{ 'opacity-50 pointer-events-none': !isSpanActive }">
            <label class="block text-sm font-semibold text-gray-200 mb-2">
              Vão / Comprimento (m)
            </label>
            <input
              v-model.number="store.form.length"
              @blur="sanitizeInput('length', 0.1)"
              :disabled="!isSpanActive"
              type="number"
              step="0.5"
              class="w-full px-3 py-2 bg-gray-900 border border-gray-700 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none transition text-sm text-white placeholder-gray-500 disabled:opacity-50"
            />
          </div>

          <!-- Altura Estrutural -->
          <div>
            <label class="block text-sm font-semibold text-gray-200 mb-2"
              >Altura (m)</label
            >
            <input
              v-model.number="store.form.height"
              @blur="sanitizeInput('height', 0.1)"
              type="number"
              step="0.1"
              class="w-full px-3 py-2 bg-gray-900 border border-gray-700 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none transition text-sm text-white placeholder-gray-500"
            />
          </div>

          <!-- Largura da Seção Transversal -->
          <div>
            <label class="block text-sm font-semibold text-gray-200 mb-2"
              >Largura (m)
              <span class="text-xs text-blue-400 font-normal"
                >(0 = Análise 2D)</span
              ></label
            >
            <input
              v-model.number="store.form.width"
              @blur="sanitizeInput('width', 0)"
              type="number"
              step="0.1"
              class="w-full px-3 py-2 bg-gray-900 border border-gray-700 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none transition text-sm text-white placeholder-gray-500"
            />
          </div>

          <!-- Geometria Variável para Torres -->
          <div :class="{ 'opacity-50 pointer-events-none': !isTopWidthActive }">
            <label class="block text-sm font-semibold text-gray-200 mb-2"
              >Largura do Topo (m)</label
            >
            <input
              v-model.number="store.form.topWidth"
              @blur="sanitizeInput('topWidth', 0.01)"
              :disabled="!isTopWidthActive"
              type="number"
              step="0.1"
              class="w-full px-3 py-2 bg-gray-900 border border-gray-700 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none transition text-sm text-white placeholder-gray-500 disabled:opacity-50"
            />
          </div>

          <!-- Discretização da Malha -->
          <div :class="{ 'opacity-50 pointer-events-none': !isPanelsActive }">
            <label class="block text-sm font-semibold text-gray-200 mb-2"
              >Painéis / Divisões</label
            >
            <input
              v-model.number="store.form.divisions"
              @blur="sanitizeInput('divisions', 2)"
              :disabled="!isPanelsActive"
              type="number"
              min="2"
              max="20"
              class="w-full px-3 py-2 bg-gray-900 border border-gray-700 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none transition text-sm text-white placeholder-gray-500 disabled:opacity-50"
            />
          </div>

          <div :class="{ 'opacity-50 pointer-events-none': !isSectionsActive }">
            <label class="block text-sm font-semibold text-gray-200 mb-2"
              >Seções (Torres)</label
            >
            <input
              v-model.number="store.form.sections"
              @blur="sanitizeInput('sections', 1)"
              :disabled="!isSectionsActive"
              type="number"
              min="1"
              max="20"
              class="w-full px-3 py-2 bg-gray-900 border border-gray-700 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none transition text-sm text-white placeholder-gray-500 disabled:opacity-50"
            />
          </div>

          <!-- Carregamento de Projeto -->
          <div>
            <label class="block text-sm font-semibold text-gray-200 mb-2"
              >Carga Total (kgf)</label
            >
            <input
              v-model.number="store.form.total_load"
              @blur="sanitizeInput('total_load', 1)"
              type="number"
              step="100"
              class="w-full px-3 py-2 bg-gray-900 border border-gray-700 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none transition text-sm text-white placeholder-gray-500"
            />
          </div>

          <!-- Configuração da Interação Solo-Estrutura (ISE) -->
          <div class="pt-2 border-t border-gray-700 mt-2">
            <h3 class="text-xs font-bold text-blue-400 uppercase mb-3">
              Interação Solo-Estrutura (ISE)
            </h3>

            <div class="mb-3">
              <label class="block text-sm font-semibold text-gray-200 mb-2"
                >Tipo de Solo</label
              >
              <select
                v-model="store.form.soil_type"
                class="w-full bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 focus:ring-2 focus:ring-blue-500 outline-none text-sm text-white"
              >
                <option value="Areia Fofa">Areia Fofa</option>
                <option value="Areia Compacta">Areia Compacta</option>
                <option value="Argila Mole">Argila Mole</option>
                <option value="Argila Rija">Argila Rija</option>
                <option value="Rocha">Rocha (Rígido)</option>
                <option value="Customizado">Customizado...</option>
              </select>
            </div>

            <div v-if="store.form.soil_type === 'Customizado'" class="mb-3">
              <label class="block text-sm font-semibold text-gray-200 mb-2"
                >ks1 (kN/m³)</label
              >
              <input
                v-model.number="store.form.custom_ks"
                @blur="sanitizeInput('custom_ks', 1000)"
                type="number"
                class="w-full px-3 py-2 bg-gray-900 border border-gray-700 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none transition text-sm text-white"
              />
            </div>

            <div class="grid grid-cols-2 gap-3">
              <div>
                <label class="block text-sm font-semibold text-gray-200 mb-2"
                  >Sapata B (m)</label
                >
                <input
                  v-model.number="store.form.footing_b"
                  @blur="sanitizeInput('footing_b', 0.3)"
                  type="number"
                  step="0.1"
                  min="0.3"
                  class="w-full px-3 py-2 bg-gray-900 border border-gray-700 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none transition text-sm text-white"
                />
              </div>
              <div>
                <label class="block text-sm font-semibold text-gray-200 mb-2"
                  >Sapata L (m)</label
                >
                <input
                  v-model.number="store.form.footing_l"
                  @blur="sanitizeInput('footing_l', 0.3)"
                  type="number"
                  step="0.1"
                  min="0.3"
                  class="w-full px-3 py-2 bg-gray-900 border border-gray-700 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none transition text-sm text-white"
                />
              </div>
            </div>
          </div>

          <!-- Alerta de Segurança e Esbeltez Crítica -->
          <div
            v-if="corrosionAnalysis.visible"
            :class="[
              'p-4 rounded-lg border transition-all duration-300 shadow-lg',
              corrosionAnalysis.type === 'danger'
                ? 'bg-red-900/20 border-red-700/50'
                : 'bg-yellow-900/20 border-yellow-700/50',
            ]"
          >
            <div class="flex items-start gap-3">
              <Icon
                :name="
                  corrosionAnalysis.type === 'danger'
                    ? 'lucide:alert-octagon'
                    : 'lucide:alert-triangle'
                "
                :class="[
                  'w-5 h-5 shrink-0 mt-0.5',
                  corrosionAnalysis.type === 'danger'
                    ? 'text-red-400'
                    : 'text-yellow-400',
                ]"
              />
              <p class="text-xs leading-relaxed text-gray-200">
                {{ corrosionAnalysis.message }}
              </p>
            </div>
          </div>
        </div>

        <!-- Comandos de Execução do Solver -->
        <div class="pt-4 space-y-3">
          <button
            @click="optimizeAndCloseMobile"
            :disabled="store.loading"
            class="w-full bg-blue-600 hover:bg-blue-700 text-white font-bold py-3 rounded-lg shadow-lg transition-all transform hover:-translate-y-0.5 active:translate-y-0 disabled:bg-gray-600 text-base"
          >
            {{ store.loading ? "Processando MEF..." : "Otimizar Estrutura" }}
          </button>

          <button
            @click="resetParameters"
            class="w-full bg-gray-700 hover:bg-gray-600 border border-gray-600 text-gray-200 font-medium py-2 rounded-lg transition text-sm"
          >
            Resetar Parâmetros
          </button>
        </div>
      </div>
    </div>
  </aside>

  <!-- Overlay para dispositivos móveis -->
  <div
    v-if="showMobileMenu"
    @click="showMobileMenu = false"
    class="fixed inset-0 bg-black/50 backdrop-blur-sm z-40 md:hidden"
  ></div>
</template>

<style scoped>
.slide-enter-active,
.slide-leave-active {
  transition: transform 0.3s ease-in-out;
}
.slide-enter-from {
  transform: translateX(-100%);
}
.slide-leave-to {
  transform: translateX(-100%);
}
</style>

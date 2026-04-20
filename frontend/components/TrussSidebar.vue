<script setup lang="ts">
import { useTrussStore } from "@/stores/useTrussStore";
import { storeToRefs } from "pinia";
import HelpModal from "./HelpModal.vue";
import AboutModal from "./AboutModal.vue";

const store = useTrussStore();
const { form, loading, showMobileMenu } = storeToRefs(store);

const showHelpModal = ref(false);
const showAboutModal = ref(false);

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

const structuralSafetyAlerts = computed(() => {
  const alerts: Array<{ message: string; type: "warning" | "danger" }> = [];

  // Justificativa: Integração de erros estruturais críticos vindos do backend (PyNite/NBR 8800).
  if (store.result && !store.result.is_structurally_stable && store.result.status_message) {
    alerts.push({
      message: store.result.status_message,
      type: "danger",
    });
  }

  const {
    selectedTemplate,
    length,
    height,
    width,
    divisions,
    total_load,
    soil_type,
  } = form.value;

  // 1. Aviso de Proporção (Vão vs. Altura)
  if (selectedTemplate.includes("roof") && height > 0 && length / height > 10) {
    alerts.push({
      message:
        "Identificamos que o comprimento da estrutura está muito grande para a altura atual, o que pode causar o envergamento excessivo do telhado. Recomendamos aumentar a altura.",
      type: "warning",
    });
  } else if (
    selectedTemplate.includes("bridge") &&
    height > 0 &&
    length / height > 20
  ) {
    alerts.push({
      message:
        "Identificamos que o vão da ponte está longo demais para a sua altura, o que pode causar vibrações severas. Recomendamos aumentar a altura.",
      type: "warning",
    });
  }

  // 2. Aviso de Estabilidade (Tombamento de Torres)
  if (selectedTemplate.includes("tower") && width > 0 && height / width > 10) {
    alerts.push({
      message:
        "Identificamos que a torre está muito alta para uma base muito estreita, o que eleva o risco de tombamento. Recomendamos aumentar a largura da base.",
      type: "danger",
    });
  }

  // 3. Aviso de Divisões (Flambagem de Barras)
  if (
    !selectedTemplate.includes("tower") &&
    divisions > 0 &&
    length / divisions > 4
  ) {
    alerts.push({
      message:
        "Identificamos que o espaçamento entre as divisões internas está muito longo, o que pode fazer as barras dobrarem com facilidade. Recomendamos aumentar o número de divisões.",
      type: "warning",
    });
  }

  // 4. Aviso de Fundação (Solo vs. Carga)
  if (
    total_load > 30000 &&
    (soil_type === "Areia Fofa" || soil_type === "Argila Mole")
  ) {
    alerts.push({
      message:
        "Identificamos que a carga aplicada é muito elevada para um solo do tipo mole ou fofo, o que pode causar o afundamento da base. Recomendamos aumentar as dimensões da sapata ou selecionar um solo mais firme.",
      type: "warning",
    });
  }

  // Regra Legada de Segurança
  if (total_load > 20000 && height < 1.5 && alerts.length === 0) {
    alerts.push({
      message:
        "Identificamos que a altura definida é reduzida para a carga informada. Recomendamos aumentar a altura da estrutura para garantir uma melhor distribuição do peso.",
      type: "warning",
    });
  }

  return alerts;
});

const optimizeAndCloseMobile = () => {
  store.optimize();
  if (isMobile.value) {
    store.showMobileMenu = false;
  }
};

const resetParameters = () => {
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
};

/**
 * Garante que valores críticos nunca fiquem fora dos limites de segurança.
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
      <!-- Cabeçalho -->
      <div
        class="relative p-6 border-b border-gray-700 bg-gray-900/50 flex flex-col items-center justify-center text-center"
      >
        <div>
          <h1 class="text-xl font-bold text-white">TRUSS-OPT 3D</h1>
          <p
            class="text-xs text-white opacity-80 mt-1 uppercase tracking-wider"
            title="Realiza o cálculo e a otimização de estruturas metálicas."
          >
            Dimensionamento Estrutural
          </p>
          <p class="text-[10px] text-blue-400/80 mt-1 font-medium">
            Desenvolvido por
            <a
              href="https://github.com/paulomml/truss-opt-3d"
              target="_blank"
              rel="noopener noreferrer"
              class="hover:underline text-blue-400"
              title="Acessa o repositório no GitHub."
            >
              Paulo Raí Lopes de Melo
            </a>
          </p>
          <!-- Ajuda e Sobre -->
          <div class="flex gap-2 mt-3 justify-center w-full">
            <button
              @click="showHelpModal = true"
              class="flex-1 flex items-center justify-center gap-1.5 py-1.5 px-3 bg-gray-800 hover:bg-gray-700 border border-gray-700 rounded-md text-[10px] font-bold text-gray-300 transition-colors group"
              title="Abre o manual de instruções."
            >
              <Icon
                name="lucide:help-circle"
                class="w-3.5 h-3.5 text-blue-400 group-hover:scale-110 transition-transform"
              />
              AJUDA
            </button>
            <button
              @click="showAboutModal = true"
              class="flex-1 flex items-center justify-center gap-1.5 py-1.5 px-3 bg-gray-800 hover:bg-gray-700 border border-gray-700 rounded-md text-[10px] font-bold text-gray-300 transition-colors group"
              title="Exibe informações sobre o projeto."
            >
              <Icon
                name="lucide:info"
                class="w-3.5 h-3.5 text-blue-400 group-hover:scale-110 transition-transform"
              />
              SOBRE
            </button>
          </div>
        </div>
        <button
          v-if="isMobile"
          @click="showMobileMenu = false"
          class="absolute top-4 right-4 p-2 text-gray-400 hover:text-white transition"
        >
          <Icon name="lucide:x" class="w-6 h-6" />
        </button>
      </div>
      <!-- Entrada de Parâmetros -->
      <div class="p-4 md:p-6 space-y-4 flex-grow overflow-y-auto">
        <!-- Tipo de Estrutura -->
        <div>
          <label
            class="block text-sm font-semibold text-gray-200 mb-2"
            title="Selecione o formato da estrutura."
            >Tipo de Estrutura</label
          >
          <select
            v-model="store.form.selectedTemplate"
            :disabled="store.loading"
            class="w-full bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 focus:ring-2 focus:ring-blue-500 outline-none text-sm text-white disabled:opacity-50"
            title="Escolha um dos modelos para iniciar."
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
          <div
            :class="{
              'opacity-50 pointer-events-none': !isSpanActive || store.loading,
            }"
          >
            <label
              class="block text-sm font-semibold text-gray-200 mb-2"
              title="Define a distância horizontal total que a estrutura vai cobrir."
            >
              Comprimento do Vão (m)
            </label>
            <input
              v-model.number="store.form.length"
              @blur="sanitizeInput('length', 0.1)"
              :disabled="!isSpanActive || store.loading"
              type="number"
              step="0.5"
              class="w-full px-3 py-2 bg-gray-900 border border-gray-700 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none transition text-sm text-white placeholder-gray-500 disabled:opacity-50"
              title="Insira o comprimento total em metros."
            />
          </div>

          <!-- Altura Estrutural -->
          <div :class="{ 'opacity-50 pointer-events-none': store.loading }">
            <label
              class="block text-sm font-semibold text-gray-200 mb-2"
              title="Define a altura máxima da estrutura."
              >Altura da Estrutura (m)</label
            >
            <input
              v-model.number="store.form.height"
              @blur="sanitizeInput('height', 0.1)"
              :disabled="store.loading"
              type="number"
              step="0.1"
              class="w-full px-3 py-2 bg-gray-900 border border-gray-700 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none transition text-sm text-white placeholder-gray-500 disabled:opacity-50"
              title="Insira a altura total em metros."
            />
          </div>

          <!-- Largura da Seção Transversal -->
          <div :class="{ 'opacity-50 pointer-events-none': store.loading }">
            <label
              class="block text-sm font-semibold text-gray-200 mb-2"
              title="Define a largura da estrutura. Use 0 para uma análise plana (2D)."
              >Largura da Estrutura (m)
              <span class="text-xs text-blue-400 font-normal"
                >(0 = Análise 2D)</span
              ></label
            >
            <input
              v-model.number="store.form.width"
              @blur="sanitizeInput('width', 0)"
              :disabled="store.loading"
              type="number"
              step="0.1"
              class="w-full px-3 py-2 bg-gray-900 border border-gray-700 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none transition text-sm text-white placeholder-gray-500 disabled:opacity-50"
              title="Insira a largura em metros. Use 0 para modelos planos."
            />
          </div>

          <!-- Geometria Variável para Torres -->
          <div
            :class="{
              'opacity-50 pointer-events-none':
                !isTopWidthActive || store.loading,
            }"
          >
            <label
              class="block text-sm font-semibold text-gray-200 mb-2"
              title="Define a largura do topo para modelos de torre."
              >Largura da Parte Superior (m)</label
            >
            <input
              v-model.number="store.form.topWidth"
              @blur="sanitizeInput('topWidth', 0.01)"
              :disabled="!isTopWidthActive || store.loading"
              type="number"
              step="0.1"
              class="w-full px-3 py-2 bg-gray-900 border border-gray-700 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none transition text-sm text-white placeholder-gray-500 disabled:opacity-50"
              title="Insira a largura do topo em metros."
            />
          </div>

          <!-- Divisões -->
          <div
            :class="{
              'opacity-50 pointer-events-none':
                !isPanelsActive || store.loading,
            }"
          >
            <label
              class="block text-sm font-semibold text-gray-200 mb-2"
              title="Define a quantidade de divisões internas da estrutura."
              >Quantidade de Seções (Divisões)</label
            >
            <input
              v-model.number="store.form.divisions"
              @blur="sanitizeInput('divisions', 2)"
              :disabled="!isPanelsActive || store.loading"
              type="number"
              min="2"
              max="20"
              class="w-full px-3 py-2 bg-gray-900 border border-gray-700 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none transition text-sm text-white placeholder-gray-500 disabled:opacity-50"
              title="Insira em quantas partes a estrutura será dividida."
            />
          </div>

          <div
            :class="{
              'opacity-50 pointer-events-none':
                !isSectionsActive || store.loading,
            }"
          >
            <label
              class="block text-sm font-semibold text-gray-200 mb-2"
              title="Define o número de andares para modelos de torre."
              >Número de Seções (Torres)</label
            >
            <input
              v-model.number="store.form.sections"
              @blur="sanitizeInput('sections', 1)"
              :disabled="!isSectionsActive || store.loading"
              type="number"
              min="1"
              max="20"
              class="w-full px-3 py-2 bg-gray-900 border border-gray-700 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none transition text-sm text-white placeholder-gray-500 disabled:opacity-50"
              title="Insira a quantidade de níveis verticais."
            />
          </div>

          <!-- Carregamento de Projeto -->
          <div :class="{ 'opacity-50 pointer-events-none': store.loading }">
            <label
              class="block text-sm font-semibold text-gray-200 mb-2"
              title="Define o peso total que a estrutura vai suportar em quilogramas (kgf)."
              >Carga Aplicada na Estrutura (kgf)</label
            >
            <input
              v-model.number="store.form.total_load"
              @blur="sanitizeInput('total_load', 1)"
              :disabled="store.loading"
              type="number"
              step="100"
              class="w-full px-3 py-2 bg-gray-900 border border-gray-700 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none transition text-sm text-white placeholder-gray-500 disabled:opacity-50"
              title="Insira o peso total previsto para o projeto."
            />
          </div>

          <!-- Configuração da Interação Solo-Estrutura (ISE) -->
          <div class="pt-2 border-t border-gray-700 mt-2">
            <h3 class="text-xs font-bold text-blue-400 uppercase mb-3">
              Fundação e Solo
            </h3>

            <div
              class="mb-3"
              :class="{ 'opacity-50 pointer-events-none': store.loading }"
            >
              <label
                class="block text-sm font-semibold text-gray-200 mb-2"
                title="Seleciona o tipo de solo. Isso afeta a estabilidade da fundação."
                >Tipo de Solo (Fundação)</label
              >
              <select
                v-model="store.form.soil_type"
                :disabled="store.loading"
                class="w-full bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 focus:ring-2 focus:ring-blue-500 outline-none text-sm text-white disabled:opacity-50"
                title="Escolha o tipo de terreno predominante na obra."
              >
                <option value="Areia Fofa">Areia Fofa</option>
                <option value="Areia Compacta">Areia Compacta</option>
                <option value="Argila Mole">Argila Mole</option>
                <option value="Argila Rija">Argila Rija</option>
                <option value="Rocha">Rocha (Rígido)</option>
                <option value="Customizado">Customizado...</option>
              </select>
            </div>

            <div
              v-if="store.form.soil_type === 'Customizado'"
              class="mb-3"
              :class="{ 'opacity-50 pointer-events-none': store.loading }"
            >
              <label
                class="block text-sm font-semibold text-gray-200 mb-2"
                title="Define a resistência técnica específica do solo."
                >Resistência Estimada do Solo (kN/m³)</label
              >
              <input
                v-model.number="store.form.custom_ks"
                @blur="sanitizeInput('custom_ks', 1000)"
                :disabled="store.loading"
                type="number"
                class="w-full px-3 py-2 bg-gray-900 border border-gray-700 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none transition text-sm text-white disabled:opacity-50"
                title="Insira o valor da resistência do solo em kN/m³."
              />
            </div>

            <div class="grid grid-cols-2 gap-3">
              <div :class="{ 'opacity-50 pointer-events-none': store.loading }">
                <label
                  class="block text-sm font-semibold text-gray-200 mb-2"
                  title="Define a largura da base de concreto (sapata) que apoia a estrutura."
                  >Largura da Sapata (m)</label
                >
                <input
                  v-model.number="store.form.footing_b"
                  @blur="sanitizeInput('footing_b', 0.3)"
                  :disabled="store.loading"
                  type="number"
                  step="0.1"
                  min="0.3"
                  class="w-full px-3 py-2 bg-gray-900 border border-gray-700 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none transition text-sm text-white disabled:opacity-50"
                  title="Insira a largura da sapata em metros."
                />
              </div>
              <div :class="{ 'opacity-50 pointer-events-none': store.loading }">
                <label
                  class="block text-sm font-semibold text-gray-200 mb-2"
                  title="Define o comprimento da base de concreto (sapata) que apoia a estrutura."
                  >Comprimento da Sapata (m)</label
                >
                <input
                  v-model.number="store.form.footing_l"
                  @blur="sanitizeInput('footing_l', 0.3)"
                  :disabled="store.loading"
                  type="number"
                  step="0.1"
                  min="0.3"
                  class="w-full px-3 py-2 bg-gray-900 border border-gray-700 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none transition text-sm text-white disabled:opacity-50"
                  title="Insira o comprimento da sapata em metros."
                />
              </div>
            </div>
          </div>

          <!-- Sistema de Avisos de Segurança Inteligentes -->
          <TransitionGroup name="list" tag="div" class="space-y-3">
            <div
              v-for="(alert, idx) in structuralSafetyAlerts"
              :key="idx"
              :class="[
                'p-4 rounded-lg border transition-all duration-300 shadow-lg',
                alert.type === 'danger'
                  ? 'bg-red-900/20 border-red-700/50'
                  : 'bg-yellow-900/20 border-yellow-700/50',
              ]"
            >
              <div class="flex items-start gap-3">
                <Icon
                  :name="
                    alert.type === 'danger'
                      ? 'lucide:alert-octagon'
                      : 'lucide:alert-triangle'
                  "
                  :class="[
                    'w-5 h-5 shrink-0 mt-0.5',
                    alert.type === 'danger'
                      ? 'text-red-400'
                      : 'text-yellow-400',
                  ]"
                />
                <p class="text-xs leading-relaxed text-gray-200">
                  {{ alert.message }}
                </p>
              </div>
            </div>
          </TransitionGroup>
        </div>

        <!-- Comandos de Execução do Solver -->
        <div class="pt-4 space-y-3">
          <button
            @click="optimizeAndCloseMobile"
            :disabled="store.loading"
            class="w-full bg-blue-600 hover:bg-blue-700 text-white font-bold py-3 rounded-lg shadow-lg transition-all transform active:translate-y-0 disabled:bg-gray-600 text-base"
            title="Inicia o processo de análise e dimensionamento da estrutura."
          >
            {{
              store.loading
                ? "Analisando Estrutura..."
                : "Iniciar Análise Estrutural"
            }}
          </button>

          <button
            @click="resetParameters"
            :disabled="store.loading"
            class="w-full bg-gray-700 hover:bg-gray-600 border border-gray-600 text-gray-200 font-medium py-2 rounded-lg transition text-sm disabled:opacity-50 disabled:cursor-not-allowed"
            title="Retorna todos os campos para os valores padrão."
          >
            Resetar Valores
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

  <!-- Modais de Informação -->
  <HelpModal :show="showHelpModal" @close="showHelpModal = false" />
  <AboutModal :show="showAboutModal" @close="showAboutModal = false" />
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

.list-enter-active,
.list-leave-active {
  transition: all 0.4s ease;
}
.list-enter-from {
  opacity: 0;
  transform: translateY(-10px);
}
.list-leave-to {
  opacity: 0;
  transform: scale(0.9);
}
</style>

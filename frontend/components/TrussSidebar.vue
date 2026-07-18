<script setup lang="ts">
import { useTrussStore } from '@/stores/useTrussStore';
import { storeToRefs } from 'pinia';
import HelpModal from './HelpModal.vue';
import AboutModal from './AboutModal.vue';
import InfoTooltip from './InfoTooltip.vue';

import CatalogoMateriaisModal from './CatalogoMateriaisModal.vue';
import CatalogoPerfisModal from './CatalogoPerfisModal.vue';
import HistoricoTarefasModal from './HistoricoTarefasModal.vue';
import NormasReferenciaModal from './NormasReferenciaModal.vue';

const store = useTrussStore();
const {
  form,
  loading,
  showMobileMenu,
  materiais,
  perfis,
  restricoes,
  parametrosVento,
  modoDesempenho,
  agAvancado,
} = storeToRefs(store);

const showHelpModal = ref(false);
const showAboutModal = ref(false);
const showRestricoesAvancadas = ref(false);
const showVentoAvancado = ref(false);
const showGA_avancado = ref(false);
const showCatalogoMateriais = ref(false);
const showCatalogoPerfis = ref(false);
const showHistorico = ref(false);
const showNormas = ref(false);

// Carrega catálogos e normas na montagem.
onMounted(() => {
  store.carregarMateriais();
  store.carregarPerfis();
  store.carregarNormas();
  store.verificarSaudeServidor();
});

const templateCategories = [
  {
    label: 'Coberturas (Roof)',
    options: [
      { value: 'pratt_roof', label: 'Tesoura Pratt' },
      { value: 'howe_roof', label: 'Tesoura Howe' },
      { value: 'fink_roof', label: 'Tesoura Fink' },
    ],
  },
  {
    label: 'Pontes (Bridge)',
    options: [
      { value: 'warren_bridge', label: 'Ponte Warren' },
      { value: 'pratt_bridge', label: 'Ponte Pratt' },
    ],
  },
  {
    label: 'Torres (Tower)',
    options: [
      { value: 'square_tower', label: 'Torre Quadrada' },
      { value: 'triangular_tower', label: 'Torre Triangular' },
    ],
  },
  {
    label: 'Balanços (Cantilever)',
    options: [
      { value: 'cantilever_pratt', label: 'Balanço Pratt' },
      { value: 'cantilever_warren', label: 'Balanço Warren' },
    ],
  },
];

const familiasDisponiveis = computed(() => {
  return [...new Set(perfis.value.map((p) => p.familia))].sort();
});

const isSpanActive = computed(() => !(form.value as any).selectedTemplate.includes('tower'));
const isPanelsActive = computed(() => !(form.value as any).selectedTemplate.includes('fink'));
const isTopWidthActive = computed(() => (form.value as any).selectedTemplate.includes('tower'));
const isSectionsActive = computed(() => (form.value as any).selectedTemplate.includes('tower'));

const isMobile = ref(false);
onMounted(() => {
  isMobile.value = window.innerWidth < 768;
  window.addEventListener('resize', () => {
    isMobile.value = window.innerWidth < 768;
  });
});

const structuralSafetyAlerts = computed(() => {
  const alerts: Array<{ message: string; type: 'warning' | 'danger' }> = [];

  if (store.result && !store.result.is_structurally_stable && store.result.status_message) {
    alerts.push({ message: store.result.status_message, type: 'danger' });
  }

  const formAny = form.value as any;
  const { selectedTemplate, length, height, width, divisions, soil_type } = formAny;
  const dead_load = formAny.dead_load || 0;
  const live_load = formAny.live_load || 0;
  const current_total_load = dead_load + live_load;

  if (selectedTemplate.includes('roof') && height > 0 && length / height > 10) {
    alerts.push({
      message: 'Comprimento muito grande para a altura — risco de envergamento excessivo.',
      type: 'warning',
    });
  }
  if (selectedTemplate.includes('bridge') && height > 0 && length / height > 20) {
    alerts.push({
      message: 'Vão longo para a altura — risco de vibrações severas.',
      type: 'warning',
    });
  }
  if (selectedTemplate.includes('tower') && width > 0 && height / width > 10) {
    alerts.push({
      message: 'Torre muito alta para a base — risco de tombamento.',
      type: 'danger',
    });
  }
  if (!selectedTemplate.includes('tower') && divisions > 0 && length / divisions > 4) {
    alerts.push({
      message: 'Painéis muito longos — risco de flambagem das barras.',
      type: 'warning',
    });
  }
  if (current_total_load > 30000 && (soil_type === 'Areia Fofa' || soil_type === 'Argila Mole')) {
    alerts.push({
      message: 'Carga elevada para solo mole — risco de recalque. Aumente a sapata.',
      type: 'warning',
    });
  }

  return alerts;
});

const optimizeAndCloseMobile = () => {
  store.optimize();
  if (isMobile.value) store.showMobileMenu = false;
};

const sanitizeInput = (field: string, min: number) => {
  const formAny = form.value as any;
  const value = formAny[field];
  if (typeof value === 'number') {
    formAny[field] = Math.max(min, value);
  }
};

// Toggle de materiais permitidos.
const toggleMaterialPermitido = (nome: string) => {
  if (!restricoes.value.materiais_permitidos) {
    restricoes.value.materiais_permitidos = [nome];
    return;
  }
  const idx = restricoes.value.materiais_permitidos.indexOf(nome);
  if (idx >= 0) {
    restricoes.value.materiais_permitidos.splice(idx, 1);
    if (restricoes.value.materiais_permitidos.length === 0) {
      restricoes.value.materiais_permitidos = null;
    }
  } else {
    restricoes.value.materiais_permitidos.push(nome);
  }
};

const toggleFamiliaPermitida = (familia: string) => {
  if (!restricoes.value.familias_permitidas) {
    restricoes.value.familias_permitidas = [familia];
    return;
  }
  const idx = restricoes.value.familias_permitidas.indexOf(familia);
  if (idx >= 0) {
    restricoes.value.familias_permitidas.splice(idx, 1);
    if (restricoes.value.familias_permitidas.length === 0) {
      restricoes.value.familias_permitidas = null;
    }
  } else {
    restricoes.value.familias_permitidas.push(familia);
  }
};
</script>

<template>
  <aside
    :class="[
      'fixed inset-y-0 left-0 z-50 w-full max-w-md lg:max-w-none lg:w-80 bg-gray-800 border-r border-gray-700 shadow-2xl transition-transform duration-300 ease-in-out lg:translate-x-0 lg:static',
      showMobileMenu ? 'translate-x-0' : '-translate-x-full',
    ]"
  >
    <div class="h-full flex flex-col overflow-y-auto">
      <!-- Cabeçalho -->
      <div class="relative p-4 border-b border-gray-700 bg-gray-900/50 text-center">
        <!-- Botão fechar (mobile) -->
        <button
          @click="showMobileMenu = false"
          class="absolute top-2 right-2 lg:hidden p-1.5 rounded-lg text-gray-400 hover:text-white hover:bg-gray-700 transition-colors"
          aria-label="Fechar menu"
        >
          <Icon name="lucide:x" class="w-5 h-5" />
        </button>
        <h1 class="text-xl font-bold text-white">TRUSS-OPT 3D</h1>
        <p class="text-xs text-blue-400/80 mt-1 font-medium uppercase tracking-wider">
          Dimensionamento e Otimização Paramétrica de Treliças Espaciais
        </p>

        <!-- Botões de ação: AJUDA / SOBRE -->
        <div class="flex gap-2 mt-3 justify-center">
          <button
            @click="showHelpModal = true"
            class="flex-1 py-1.5 px-3 bg-gray-800 hover:bg-gray-700 border border-gray-700 rounded-md text-[10px] font-bold text-gray-300"
          >
            AJUDA
          </button>
          <button
            @click="showAboutModal = true"
            class="flex-1 py-1.5 px-3 bg-gray-800 hover:bg-gray-700 border border-gray-700 rounded-md text-[10px] font-bold text-gray-300"
          >
            SOBRE
          </button>
        </div>

        <!-- Botões de catálogos e referências -->
        <div class="grid grid-cols-2 gap-1.5 mt-2">
          <button
            @click="showCatalogoMateriais = true"
            class="py-1.5 lg:py-1 px-2 bg-gray-800/60 hover:bg-gray-700 border border-gray-700/50 rounded text-[11px] lg:text-[9px] font-bold text-gray-400 uppercase"
          >
            Materiais
          </button>
          <button
            @click="showCatalogoPerfis = true"
            class="py-1.5 lg:py-1 px-2 bg-gray-800/60 hover:bg-gray-700 border border-gray-700/50 rounded text-[11px] lg:text-[9px] font-bold text-gray-400 uppercase"
          >
            Perfis
          </button>
          <button
            @click="showNormas = true"
            class="py-1.5 lg:py-1 px-2 bg-gray-800/60 hover:bg-gray-700 border border-gray-700/50 rounded text-[11px] lg:text-[9px] font-bold text-gray-400 uppercase"
          >
            Normas NBR
          </button>
          <button
            @click="showHistorico = true"
            class="py-1.5 lg:py-1 px-2 bg-gray-800/60 hover:bg-gray-700 border border-gray-700/50 rounded text-[11px] lg:text-[9px] font-bold text-gray-400 uppercase"
          >
            Histórico
          </button>
        </div>
      </div>

      <!-- Formulário -->
      <div class="p-4 space-y-4 flex-grow">
        <div class="pt-1">
          <h3 class="text-xs font-bold text-blue-400 uppercase tracking-wider mb-3">
            1. Geometria
          </h3>

          <div class="space-y-3">
            <div>
              <label class="block text-sm font-semibold text-gray-200 mb-2">
                Tipo de Estrutura
                <InfoTooltip
                  text="Define a topologia da treliça. Pratt, Howe e Fink distribuem as diagonais de formas diferentes, afetando a rigidez e a eficiência sob carga. Veja o diagrama 3D ao lado."
                />
              </label>
              <select
                v-model="(form as any).selectedTemplate"
                :disabled="loading"
                class="w-full bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-base lg:text-sm text-white"
              >
                <optgroup v-for="cat in templateCategories" :key="cat.label" :label="cat.label">
                  <option v-for="opt in cat.options" :key="opt.value" :value="opt.value">
                    {{ opt.label }}
                  </option>
                </optgroup>
              </select>
            </div>

            <div :class="{ 'opacity-50 pointer-events-none': !isSpanActive || loading }">
              <label class="block text-sm font-semibold text-gray-200 mb-1">
                Vão (m)
                <InfoTooltip
                  text="Distância entre os apoios, em metros. Quanto maior o vão, maiores os esforços internos. Típico: 10–30 m para coberturas."
                />
              </label>
              <input
                v-model.number="form.length"
                @blur="sanitizeInput('length', 0.1)"
                :disabled="!isSpanActive || loading"
                type="number"
                step="0.5"
                class="w-full px-3 py-2 bg-gray-900 border border-gray-700 rounded-lg text-base lg:text-sm text-white"
              />
            </div>

            <div :class="{ 'opacity-50 pointer-events-none': loading }">
              <label class="block text-sm font-semibold text-gray-200 mb-1">
                Altura (m)
                <InfoTooltip
                  text="Altura total da treliça. Uma altura maior reduz as forças nas barras mas aumenta o custo. Relação vão/altura ideal: 4 a 8."
                />
              </label>
              <input
                v-model.number="form.height"
                @blur="sanitizeInput('height', 0.1)"
                :disabled="loading"
                type="number"
                step="0.1"
                class="w-full px-3 py-2 bg-gray-900 border border-gray-700 rounded-lg text-base lg:text-sm text-white"
              />
            </div>

            <div :class="{ 'opacity-50 pointer-events-none': loading }">
              <label class="block text-sm font-semibold text-gray-200 mb-1">
                Largura (m)
                <span class="text-xs text-blue-400">(0 = 2D)</span>
                <InfoTooltip
                  text="Largura transversal da treliça. Use 0 para análise 2D (plana). Para treliças espaciais 3D, informe a largura real em metros."
                />
              </label>
              <input
                v-model.number="form.width"
                @blur="sanitizeInput('width', 0)"
                :disabled="loading"
                type="number"
                step="0.1"
                class="w-full px-3 py-2 bg-gray-900 border border-gray-700 rounded-lg text-base lg:text-sm text-white"
              />
            </div>

            <div :class="{ 'opacity-50 pointer-events-none': !isTopWidthActive || loading }">
              <label class="block text-sm font-semibold text-gray-200 mb-1">
                Largura do Topo (m)
                <InfoTooltip
                  text="Largura do topo da torre (só para torres). Uma base mais larga que o topo melhora a estabilidade lateral."
                />
              </label>
              <input
                v-model.number="(form as any).topWidth"
                @blur="sanitizeInput('topWidth', 0.01)"
                :disabled="!isTopWidthActive || loading"
                type="number"
                step="0.1"
                class="w-full px-3 py-2 bg-gray-900 border border-gray-700 rounded-lg text-base lg:text-sm text-white"
              />
            </div>

            <div :class="{ 'opacity-50 pointer-events-none': !isPanelsActive || loading }">
              <label class="block text-sm font-semibold text-gray-200 mb-1">
                Painéis
                <InfoTooltip
                  text="Subdivisões do vão. Mais painéis = distribuição de cargas mais refinada, porém mais barras e juntas. Típico: 4–12."
                />
              </label>
              <input
                v-model.number="form.divisions"
                @blur="sanitizeInput('divisions', 2)"
                :disabled="!isPanelsActive || loading"
                type="number"
                min="2"
                max="20"
                class="w-full px-3 py-2 bg-gray-900 border border-gray-700 rounded-lg text-base lg:text-sm text-white"
              />
            </div>

            <div :class="{ 'opacity-50 pointer-events-none': !isSectionsActive || loading }">
              <label class="block text-sm font-semibold text-gray-200 mb-1">
                Andares (Torres)
                <InfoTooltip
                  text="Módulos verticais da torre (só para torres). Cada andar representa uma seção repetitiva da estrutura."
                />
              </label>
              <input
                v-model.number="(form as any).sections"
                @blur="sanitizeInput('sections', 1)"
                :disabled="!isSectionsActive || loading"
                type="number"
                min="1"
                max="20"
                class="w-full px-3 py-2 bg-gray-900 border border-gray-700 rounded-lg text-base lg:text-sm text-white"
              />
            </div>
          </div>
        </div>

        <div class="pt-3 border-t border-gray-700 space-y-3">
          <h3 class="text-xs font-bold text-blue-400 uppercase tracking-wider">
            2. Carregamento <span class="text-gray-500 font-normal">(NBR 6120)</span>
          </h3>

          <div :class="{ 'opacity-50 pointer-events-none': loading }">
            <label class="block text-sm font-semibold text-gray-200 mb-1">
              Carga Permanente G (kgf)
              <InfoTooltip
                text="Peso próprio dos elementos construtivos sobre a treliça: telhas, terças, forro, instalações. Valor típico: 1.000–3.000 kgf por nó do banzo superior."
              />
            </label>
            <input
              v-model.number="(form as any).dead_load"
              @blur="sanitizeInput('dead_load', 0)"
              :disabled="loading"
              type="number"
              step="100"
              class="w-full px-3 py-2 bg-gray-900 border border-gray-700 rounded-lg text-base lg:text-sm text-white"
            />
          </div>

          <div :class="{ 'opacity-50 pointer-events-none': loading }">
            <label class="block text-sm font-semibold text-gray-200 mb-1">
              Sobrecarga Q (kgf)
              <InfoTooltip
                text="Carga variável por uso (NBR 6120): pessoas, móveis, equipamentos. Para coberturas sem acesso, a norma recomenda mínimo de 25 kgf/m² de projeção horizontal."
              />
            </label>
            <input
              v-model.number="(form as any).live_load"
              @blur="sanitizeInput('live_load', 0)"
              :disabled="loading"
              type="number"
              step="100"
              class="w-full px-3 py-2 bg-gray-900 border border-gray-700 rounded-lg text-base lg:text-sm text-white"
            />
          </div>

          <div :class="{ 'opacity-50 pointer-events-none': loading }">
            <label class="block text-sm font-semibold text-gray-200 mb-1">
              Lâmina d'Água (mm)
              <InfoTooltip
                text="Altura da lâmina de água acumulada na cobertura, simulando chuva intensa. Consulte a NBR 6120 item 6.3 para valores mínimos de projeto."
              />
            </label>
            <input
              v-model.number="form.water_lamina"
              @blur="sanitizeInput('water_lamina', 0)"
              :disabled="loading"
              type="number"
              step="10"
              class="w-full px-3 py-2 bg-gray-900 border border-gray-700 rounded-lg text-base lg:text-sm text-white"
            />
          </div>

          <!-- Vento (NBR 6123): expansível -->
          <div class="pt-1">
            <button
              @click="showVentoAvancado = !showVentoAvancado"
              class="w-full flex items-center justify-between text-xs font-bold text-gray-400 hover:text-blue-400 transition-colors uppercase"
            >
              <span>Vento (NBR 6123)</span>
              <Icon
                :name="showVentoAvancado ? 'lucide:chevron-up' : 'lucide:chevron-down'"
                class="w-4 h-4"
              />
            </button>

            <div v-if="showVentoAvancado" class="mt-3 space-y-3">
              <div>
                <label class="block text-xs text-gray-300 mb-1">
                  V₀ (m/s)
                  <InfoTooltip
                    text="Velocidade básica do vento na região, conforme mapa eólico da NBR 6123. No Brasil, varia de 30 a 50 m/s dependendo da localidade."
                  />
                </label>
                <input
                  v-model.number="parametrosVento.v0_mps"
                  type="number"
                  step="1"
                  class="w-full px-2 py-1.5 bg-gray-900 border border-gray-700 rounded text-sm lg:text-xs text-white"
                />
              </div>
              <div class="grid grid-cols-3 gap-2">
                <div>
                  <label class="block text-xs text-gray-300 mb-1">
                    S₁
                    <InfoTooltip
                      text="Fator topográfico da NBR 6123. Considera se a edificação está em topo de morro, vale ou terreno plano. Varia de 0,85 a 1,15."
                    />
                  </label>
                  <input
                    v-model.number="parametrosVento.s1"
                    type="number"
                    step="0.05"
                    class="w-full px-2 py-1.5 bg-gray-900 border border-gray-700 rounded text-sm lg:text-xs text-white"
                  />
                </div>
                <div>
                  <label class="block text-xs text-gray-300 mb-1">
                    S₂
                    <InfoTooltip
                      text="Fator de rugosidade do terreno da NBR 6123. Considera obstáculos (prédios, árvores) e altura da edificação. Varia conforme a categoria do terreno."
                    />
                  </label>
                  <input
                    v-model.number="parametrosVento.s2"
                    type="number"
                    step="0.05"
                    class="w-full px-2 py-1.5 bg-gray-900 border border-gray-700 rounded text-sm lg:text-xs text-white"
                  />
                </div>
                <div>
                  <label class="block text-xs text-gray-300 mb-1">
                    S₃
                    <InfoTooltip
                      text="Fator estatístico da NBR 6123. Baseado na vida útil e probabilidade de ocorrência do vento máximo. Edificações comuns usam S₃ = 1,00."
                    />
                  </label>
                  <input
                    v-model.number="parametrosVento.s3"
                    type="number"
                    step="0.05"
                    class="w-full px-2 py-1.5 bg-gray-900 border border-gray-700 rounded text-sm lg:text-xs text-white"
                  />
                </div>
              </div>
              <div>
                <label class="block text-xs text-gray-300 mb-1">Direção (graus)</label>
                <input
                  v-model.number="parametrosVento.direcao_vento_graus"
                  type="number"
                  step="15"
                  min="0"
                  max="345"
                  class="w-full px-2 py-1.5 bg-gray-900 border border-gray-700 rounded text-sm lg:text-xs text-white"
                />
              </div>
              <div class="grid grid-cols-2 gap-2">
                <div>
                  <label class="block text-xs text-gray-300 mb-1">
                    Ce (externo)
                    <InfoTooltip
                      text="Coeficiente de pressão externa da NBR 6123. Determina a sucção ou pressão do vento nas faces externas da edificação."
                    />
                  </label>
                  <input
                    v-model.number="parametrosVento.ce_externo"
                    type="number"
                    step="0.1"
                    class="w-full px-2 py-1.5 bg-gray-900 border border-gray-700 rounded text-sm lg:text-xs text-white"
                  />
                </div>
                <div>
                  <label class="block text-xs text-gray-300 mb-1">
                    Ci (interno)
                    <InfoTooltip
                      text="Coeficiente de pressão interna da NBR 6123. Depende da permeabilidade das vedações (paredes, janelas). Edificações fechadas usam Ci próximo de 0."
                    />
                  </label>
                  <input
                    v-model.number="parametrosVento.ci_interno"
                    type="number"
                    step="0.1"
                    class="w-full px-2 py-1.5 bg-gray-900 border border-gray-700 rounded text-sm lg:text-xs text-white"
                  />
                </div>
              </div>
              <div class="text-[10px] text-gray-400 italic">
                Vk = V₀·S₁·S₂·S₃ =
                {{
                  (
                    parametrosVento.v0_mps *
                    parametrosVento.s1 *
                    parametrosVento.s2 *
                    parametrosVento.s3
                  ).toFixed(1)
                }}
                m/s | q = 0,613·Vk² =
                {{
                  (
                    0.613 *
                    Math.pow(
                      parametrosVento.v0_mps *
                        parametrosVento.s1 *
                        parametrosVento.s2 *
                        parametrosVento.s3,
                      2,
                    )
                  ).toFixed(1)
                }}
                N/m²
              </div>
            </div>
          </div>
        </div>

        <div class="pt-3 border-t border-gray-700 space-y-3">
          <h3 class="text-xs font-bold text-blue-400 uppercase tracking-wider">3. Fundação</h3>

          <div :class="{ 'opacity-50 pointer-events-none': loading }">
            <label class="block text-sm font-semibold text-gray-200 mb-1">
              Tipo de Solo
              <InfoTooltip
                text="Classificação do solo de apoio. Determina o coeficiente de reação do subleito (ks) usado nos apoios elásticos (Modelo de Winkler). Solos moles geram maiores recalques."
              />
            </label>
            <select
              v-model="form.soil_type"
              :disabled="loading"
              class="w-full bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-base lg:text-sm text-white"
            >
              <option>Areia Fofa</option>
              <option>Areia Compacta</option>
              <option>Argila Mole</option>
              <option>Argila Rija</option>
              <option>Rocha</option>
              <option>Customizado</option>
            </select>
          </div>

          <div
            v-if="form.soil_type === 'Customizado'"
            :class="{ 'opacity-50 pointer-events-none': loading }"
          >
            <label class="block text-sm font-semibold text-gray-200 mb-1">
              ks (kN/m³)
              <InfoTooltip
                text="Coeficiente de reação do subleito. Só usado quando Tipo de Solo = Customizado. Valores típicos: areia fofa ~8.000, rocha ~100.000 kN/m³."
              />
            </label>
            <input
              v-model.number="form.custom_ks"
              type="number"
              class="w-full px-3 py-2 bg-gray-900 border border-gray-700 rounded-lg text-base lg:text-sm text-white"
            />
          </div>

          <div class="grid grid-cols-2 gap-2">
            <div :class="{ 'opacity-50 pointer-events-none': loading }">
              <label class="block text-sm font-semibold text-gray-200 mb-1">
                Sapata B (m)
                <InfoTooltip
                  text="Dimensão da base da sapata no eixo X. Usada no cálculo da rigidez rotacional dos apoios. Sapatas maiores reduzem recalques."
                />
              </label>
              <input
                v-model.number="form.footing_b"
                @blur="sanitizeInput('footing_b', 0.3)"
                :disabled="loading"
                type="number"
                step="0.1"
                min="0.3"
                class="w-full px-3 py-2 bg-gray-900 border border-gray-700 rounded-lg text-base lg:text-sm text-white"
              />
            </div>
            <div :class="{ 'opacity-50 pointer-events-none': loading }">
              <label class="block text-sm font-semibold text-gray-200 mb-1">
                Sapata L (m)
                <InfoTooltip
                  text="Dimensão da base da sapata no eixo Z. Junto com B, define a rigidez rotacional dos apoios. Sapatas maiores reduzem recalques."
                />
              </label>
              <input
                v-model.number="form.footing_l"
                @blur="sanitizeInput('footing_l', 0.3)"
                :disabled="loading"
                type="number"
                step="0.1"
                min="0.3"
                class="w-full px-3 py-2 bg-gray-900 border border-gray-700 rounded-lg text-base lg:text-sm text-white"
              />
            </div>
          </div>
        </div>

        <div class="pt-3 border-t border-gray-700 space-y-3">
          <h3 class="text-xs font-bold text-blue-400 uppercase tracking-wider">4. Otimizador</h3>

          <!-- Modo de Desempenho -->
          <div>
            <label class="block text-sm font-semibold text-gray-200 mb-1">
              Modo de Desempenho
              <InfoTooltip
                text="Controla a velocidade × qualidade da otimização. Rápido: 5 gerações (testes rápidos). Normal: 25 gerações (padrão). Preciso: 50 gerações (máxima qualidade). Customizado: você define gerações e população manualmente."
              />
            </label>
            <select
              v-model="store.modoDesempenho"
              :disabled="loading"
              class="w-full bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-base lg:text-sm text-white"
            >
              <option value="rapido">Rápido (teste)</option>
              <option value="normal">Normal (padrão)</option>
              <option value="preciso">Preciso (qualidade)</option>
              <option value="customizado">Customizado</option>
            </select>
          </div>

          <!-- Sliders (só quando customizado) -->
          <div v-if="store.modoDesempenho === 'customizado'" class="space-y-3">
            <div :class="{ 'opacity-50 pointer-events-none': loading }">
              <label class="block text-sm font-semibold text-gray-200 mb-1">
                Gerações: {{ form.ag_geracoes }}
                <InfoTooltip
                  text="Número de iterações do Algoritmo Genético. Mais gerações = solução mais otimizada, porém maior tempo de processamento. Típico: 5–100."
                />
              </label>
              <input
                v-model.number="form.ag_geracoes"
                :disabled="loading"
                type="range"
                min="1"
                max="200"
                class="w-full accent-blue-500"
              />
              <div class="flex justify-between text-[10px] text-gray-500">
                <span>1</span><span>50</span><span>100</span><span>200</span>
              </div>
            </div>
            <div :class="{ 'opacity-50 pointer-events-none': loading }">
              <label class="block text-sm font-semibold text-gray-200 mb-1">
                População: {{ form.ag_populacao }}
                <InfoTooltip
                  text="Número de soluções candidatas por geração. Populações maiores exploram melhor o espaço de busca, mas cada geração demora mais. Típico: 10–100."
                />
              </label>
              <input
                v-model.number="form.ag_populacao"
                :disabled="loading"
                type="range"
                min="4"
                max="200"
                class="w-full accent-blue-500"
              />
              <div class="flex justify-between text-[10px] text-gray-500">
                <span>4</span><span>50</span><span>100</span><span>200</span>
              </div>
            </div>
          </div>

          <!-- Parâmetros Avançados do GA: expansível -->
          <div class="pt-1">
            <button
              @click="showGA_avancado = !showGA_avancado"
              class="w-full flex items-center justify-between text-xs font-bold text-gray-400 hover:text-blue-400 transition-colors uppercase"
            >
              <span>Parâmetros Avançados do GA</span>
              <Icon
                :name="showGA_avancado ? 'lucide:chevron-up' : 'lucide:chevron-down'"
                class="w-4 h-4"
              />
            </button>

            <div v-if="showGA_avancado" class="mt-3 space-y-3">
              <!-- Refinamento local (memético) -->
              <label class="flex items-center gap-2 text-xs text-gray-200 cursor-pointer">
                <input type="checkbox" v-model="agAvancado.usar_refinamento_local" />
                <span>
                  Refinamento local (memético)
                  <InfoTooltip
                    text="Ativa hill climbing first-improvement nos melhores indivíduos a cada geração. Algoritmo memético: combina exploração global (GA) com refinamento local (Lamarckiano). Recomendado: ligado."
                  />
                </span>
              </label>

              <!-- Probabilidade de cruzamento -->
              <div :class="{ 'opacity-50 pointer-events-none': loading }">
                <label class="block text-xs text-gray-300 mb-1">
                  Prob. Cruzamento:
                  {{
                    agAvancado.probabilidade_cruzamento === null
                      ? 'padrão'
                      : agAvancado.probabilidade_cruzamento.toFixed(2)
                  }}
                  <InfoTooltip
                    text="Probabilidade de crossover entre dois indivíduos (0 a 1). Padrão do backend: 0,7. Valores menores preservam diversidade, valores maiores aceleram convergência."
                  />
                </label>
                <input
                  v-model.number="agAvancado.probabilidade_cruzamento"
                  :disabled="loading"
                  type="range"
                  min="0"
                  max="1"
                  step="0.05"
                  class="w-full accent-blue-500"
                />
                <button
                  @click="agAvancado.probabilidade_cruzamento = null"
                  class="text-xs lg:text-[9px] text-gray-500 hover:text-gray-400 underline mt-0.5 py-1"
                >
                  usar padrão
                </button>
              </div>

              <!-- Probabilidade de mutação -->
              <div :class="{ 'opacity-50 pointer-events-none': loading }">
                <label class="block text-xs text-gray-300 mb-1">
                  Prob. Mutação:
                  {{
                    agAvancado.probabilidade_mutacao === null
                      ? 'padrão'
                      : agAvancado.probabilidade_mutacao.toFixed(2)
                  }}
                  <InfoTooltip
                    text="Probabilidade de mutação de cada gene (0 a 1). Padrão do backend: 0,2. Valores maiores aumentam diversidade, valores menores aceleram convergência."
                  />
                </label>
                <input
                  v-model.number="agAvancado.probabilidade_mutacao"
                  :disabled="loading"
                  type="range"
                  min="0"
                  max="1"
                  step="0.05"
                  class="w-full accent-blue-500"
                />
                <button
                  @click="agAvancado.probabilidade_mutacao = null"
                  class="text-xs lg:text-[9px] text-gray-500 hover:text-gray-400 underline mt-0.5 py-1"
                >
                  usar padrão
                </button>
              </div>

              <!-- Tamanho do torneio -->
              <div :class="{ 'opacity-50 pointer-events-none': loading }">
                <label class="block text-xs text-gray-300 mb-1">
                  Tamanho do Torneio:
                  {{ agAvancado.indice_torneio === null ? 'padrão' : agAvancado.indice_torneio }}
                  <InfoTooltip
                    text="Número de indivíduos que competem na seleção por torneio. Padrão do backend: 3. Valores maiores aumentam a pressão seletiva (convergência mais rápida, menos diversidade)."
                  />
                </label>
                <input
                  v-model.number="agAvancado.indice_torneio"
                  :disabled="loading"
                  type="range"
                  min="1"
                  max="10"
                  step="1"
                  class="w-full accent-blue-500"
                />
                <button
                  @click="agAvancado.indice_torneio = null"
                  class="text-xs lg:text-[9px] text-gray-500 hover:text-gray-400 underline mt-0.5 py-1"
                >
                  usar padrão
                </button>
              </div>

              <!-- Máximo de perfis distintos -->
              <div :class="{ 'opacity-50 pointer-events-none': loading }">
                <label class="block text-xs text-gray-300 mb-1">
                  Máx. Perfis Distintos:
                  {{
                    agAvancado.max_perfis_distintos === null
                      ? 'padrão'
                      : agAvancado.max_perfis_distintos
                  }}
                  <InfoTooltip
                    text="Número máximo de perfis distintos sem aplicar penalidade de padronização. Padrão do backend: 4. Valores menores forçam padronização (menos custo de fabricação), valores maiores permitem mais diversidade estrutural."
                  />
                </label>
                <input
                  v-model.number="agAvancado.max_perfis_distintos"
                  :disabled="loading"
                  type="range"
                  min="1"
                  max="20"
                  step="1"
                  class="w-full accent-blue-500"
                />
                <button
                  @click="agAvancado.max_perfis_distintos = null"
                  class="text-xs lg:text-[9px] text-gray-500 hover:text-gray-400 underline mt-0.5 py-1"
                >
                  usar padrão
                </button>
              </div>

              <!-- Semente aleatória -->
              <hr class="border-gray-700/50 my-2" />
              <div :class="{ 'opacity-50 pointer-events-none': loading }">
                <label class="block text-xs text-gray-300 mb-1">
                  Seed Aleatória: {{ store.form.ag_semente ?? 'aleatório' }}
                  <InfoTooltip
                    text="Seed do gerador aleatório. 42 = resultados idênticos a cada execução. 0 ou vazio = aleatório (diferente a cada vez)."
                  />
                </label>
                <input
                  v-model.number="store.form.ag_semente"
                  :disabled="loading"
                  type="range"
                  min="0"
                  max="9999"
                  step="1"
                  class="w-full accent-blue-500"
                />
                <button
                  @click="store.form.ag_semente = 42"
                  class="text-[9px] text-gray-500 hover:text-gray-400 underline mt-0.5"
                >
                  restaurar 42
                </button>
              </div>
            </div>
          </div>

          <!-- Restrições Avançadas: expansível -->
          <div class="pt-1">
            <button
              @click="showRestricoesAvancadas = !showRestricoesAvancadas"
              class="w-full flex items-center justify-between text-xs font-bold text-gray-400 hover:text-blue-400 transition-colors uppercase"
            >
              <span>Restrições Avançadas</span>
              <Icon
                :name="showRestricoesAvancadas ? 'lucide:chevron-up' : 'lucide:chevron-down'"
                class="w-4 h-4"
              />
            </button>

            <div v-if="showRestricoesAvancadas" class="mt-3 space-y-3">
              <!-- Materiais -->
              <div>
                <label class="block text-xs text-gray-300 mb-1">
                  Materiais Permitidos
                  <InfoTooltip
                    text="Seleciona quais aços estruturais o GA pode usar (A36, MR250, SAC300…). Cada um tem resistência (fy) e custo diferentes. O otimizador escolhe o de melhor custo-benefício. Vazio = todos disponíveis."
                  />
                </label>
                <div class="space-y-1 max-h-32 overflow-y-auto">
                  <label
                    v-for="mat in materiais"
                    :key="mat.id"
                    class="flex items-center gap-2 text-xs text-gray-200 cursor-pointer hover:bg-gray-700/50 px-2 py-1 rounded"
                  >
                    <input
                      type="checkbox"
                      :checked="restricoes.materiais_permitidos?.includes(mat.nome) || false"
                      @change="toggleMaterialPermitido(mat.nome)"
                      class="rounded"
                    />
                    <span
                      >{{ mat.nome }}
                      <span class="text-gray-500"
                        >({{ mat.fy_mpa }} MPa · R$ {{ mat.custo_kg.toFixed(2) }}/kg)</span
                      ></span
                    >
                  </label>
                </div>
                <p
                  v-if="!restricoes.materiais_permitidos"
                  class="text-[10px] text-gray-500 italic mt-1"
                >
                  Vazio = todos os materiais
                </p>
              </div>

              <!-- Famílias -->
              <div>
                <label class="block text-xs text-gray-300 mb-1">
                  Famílias de Perfis
                  <InfoTooltip
                    text="Restringe as famílias de perfis disponíveis: L (cantoneiras), RHS (tubos retangulares), Ue (U enrijecido). Menos famílias = busca mais rápida. Vazio = todas disponíveis."
                  />
                </label>
                <div class="flex flex-wrap gap-2">
                  <label
                    v-for="fam in familiasDisponiveis"
                    :key="fam"
                    class="flex items-center gap-1 text-xs text-gray-200 cursor-pointer bg-gray-700 px-2 py-1 rounded"
                  >
                    <input
                      type="checkbox"
                      :checked="restricoes.familias_permitidas?.includes(fam) || false"
                      @change="toggleFamiliaPermitida(fam)"
                    />
                    {{ fam }}
                  </label>
                </div>
                <p
                  v-if="!restricoes.familias_permitidas"
                  class="text-[10px] text-gray-500 italic mt-1"
                >
                  Vazio = todas as famílias
                </p>
              </div>

              <!-- Penalidade de diversidade -->
              <label class="flex items-center gap-2 text-xs text-gray-200 cursor-pointer">
                <input type="checkbox" v-model="restricoes.usar_penalidade_diversidade" />
                <span>
                  Penalizar muitos perfis distintos
                  <InfoTooltip
                    text="Ativa penalidade no GA para soluções com muitos tipos de perfis diferentes. Incentiva a padronização, reduzindo complexidade e custo de fabricação."
                  />
                </span>
              </label>
              <p class="text-[10px] text-gray-500 italic">
                Reduz complexidade de fabricação limitando perfis distintos.
              </p>
            </div>
          </div>
        </div>

        <!-- ═══════════════════════════════════════════ -->
        <!-- ALERTAS DE SEGURANÇA                        -->
        <!-- ═══════════════════════════════════════════ -->
        <TransitionGroup name="list" tag="div" class="space-y-2">
          <div
            v-for="(alert, idx) in structuralSafetyAlerts"
            :key="idx"
            :class="[
              'p-3 rounded-lg border',
              alert.type === 'danger'
                ? 'bg-red-900/20 border-red-700/50'
                : 'bg-yellow-900/20 border-yellow-700/50',
            ]"
          >
            <div class="flex items-start gap-2">
              <Icon
                :name="alert.type === 'danger' ? 'lucide:alert-octagon' : 'lucide:alert-triangle'"
                :class="[
                  'w-4 h-4 shrink-0 mt-0.5',
                  alert.type === 'danger' ? 'text-red-400' : 'text-yellow-400',
                ]"
              />
              <p class="text-xs leading-relaxed text-gray-200">{{ alert.message }}</p>
            </div>
          </div>
        </TransitionGroup>
      </div>

      <!-- Botões -->
      <div class="p-4 border-t border-gray-700 space-y-2">
        <button
          @click="optimizeAndCloseMobile"
          :disabled="loading"
          class="w-full bg-blue-600 hover:bg-blue-700 text-white font-bold py-3 rounded-lg shadow-lg disabled:bg-gray-600 text-base"
        >
          {{ loading ? 'Analisando...' : 'Iniciar Análise Estrutural' }}
        </button>
        <button
          @click="store.resetParameters()"
          :disabled="loading"
          class="w-full bg-gray-700 hover:bg-gray-600 border border-gray-600 text-gray-200 font-medium py-2 rounded-lg text-sm disabled:opacity-50"
        >
          Resetar Valores
        </button>
      </div>
    </div>
  </aside>

  <!-- Overlay mobile -->
  <div
    v-if="showMobileMenu"
    @click="showMobileMenu = false"
    class="fixed inset-0 bg-black/50 backdrop-blur-sm z-40 lg:hidden"
  ></div>

  <HelpModal :show="showHelpModal" @close="showHelpModal = false" />
  <AboutModal :show="showAboutModal" @close="showAboutModal = false" />

  <!-- Catálogos e referências -->
  <CatalogoMateriaisModal :show="showCatalogoMateriais" @close="showCatalogoMateriais = false" />
  <CatalogoPerfisModal :show="showCatalogoPerfis" @close="showCatalogoPerfis = false" />
  <HistoricoTarefasModal :show="showHistorico" @close="showHistorico = false" />
  <NormasReferenciaModal :show="showNormas" @close="showNormas = false" />
</template>

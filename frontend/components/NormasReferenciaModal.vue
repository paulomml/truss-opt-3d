<script setup lang="ts">
// Referência de normas NBR e defaults do GA.
import { useTrussStore } from '@/stores/useTrussStore';

const store = useTrussStore();

const props = defineProps<{ show: boolean }>();
const emit = defineEmits<{ (e: 'close'): void }>();

// Carrega normas ao abrir.
watch(
  () => props.show,
  (show) => {
    if (show) {
      store.carregarNormas();
    }
  },
);

const normas = computed(() => store.normasReferencia);

// Formata chave de constante para exibição amigável.
function formatarChave(chave: string): string {
  return chave
    .replace('gamma_g', 'γ_G')
    .replace('gamma_q', 'γ_Q')
    .replace('psi_0', 'ψ₀')
    .replace('psi_1', 'ψ₁')
    .replace('psi_2', 'ψ₂')
    .replace('pressao_dinamica_coeficiente', 'Coef. pressão dinâmica');
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
        class="bg-gray-800 border border-gray-700 rounded-xl shadow-2xl max-w-4xl w-full max-h-[85vh] overflow-hidden flex flex-col"
      >
        <!-- Cabeçalho -->
        <div class="p-5 border-b border-gray-700 flex justify-between items-center">
          <div>
            <h2 class="text-xl font-bold text-white">Referência de Normas Técnicas</h2>
            <p class="text-xs text-gray-400 mt-1">
              Constantes e equações das normas brasileiras usadas pelo sistema.
            </p>
          </div>
          <button
            @click="emit('close')"
            class="text-gray-400 hover:text-white p-2 hover:bg-gray-700 rounded-lg transition-colors"
          >
            <Icon name="lucide:x" class="w-5 h-5" />
          </button>
        </div>

        <!-- Conteúdo -->
        <div class="overflow-auto flex-grow p-5 space-y-6">
          <div v-if="!normas" class="text-center text-gray-500 italic py-8">Carregando...</div>

          <!-- NBR 6120 -->
          <div v-if="normas" class="bg-gray-900/50 rounded-lg p-4 border border-gray-700">
            <h3 class="text-blue-400 font-bold text-sm mb-1">
              {{ normas.nbr_6120.nome }}
            </h3>
            <p class="text-xs text-gray-400 mb-3">{{ normas.nbr_6120.descricao }}</p>
            <div class="grid grid-cols-2 md:grid-cols-5 gap-2 text-xs">
              <div
                v-for="(valor, chave) in normas.nbr_6120.constantes"
                :key="chave"
                class="bg-gray-800 p-2 rounded"
              >
                <div class="text-gray-500 uppercase text-[10px] break-words">
                  {{ formatarChave(chave) }}
                </div>
                <div class="text-white font-mono font-bold">{{ valor }}</div>
              </div>
            </div>
            <div class="mt-3 text-xs text-gray-400">
              <span class="font-bold text-gray-300">Combinações ELU:</span>
              {{ normas.nbr_6120.combinacoes_elu.join(', ') }}
            </div>
            <div class="text-xs text-gray-400">
              <span class="font-bold text-gray-300">Combinações ELS:</span>
              {{ normas.nbr_6120.combinacoes_els.join(', ') }}
            </div>
          </div>

          <!-- NBR 6123 -->
          <div v-if="normas" class="bg-gray-900/50 rounded-lg p-4 border border-gray-700">
            <h3 class="text-blue-400 font-bold text-sm mb-1">
              {{ normas.nbr_6123.nome }}
            </h3>
            <p class="text-xs text-gray-400 mb-3">{{ normas.nbr_6123.descricao }}</p>
            <p class="text-xs text-gray-300">
              <span class="font-bold">Fórmula:</span> Vk = V₀ · S₁ · S₂ · S₃
            </p>
            <p class="text-xs text-gray-300">
              <span class="font-bold">Pressão dinâmica:</span> q = 0,613 · Vk² (N/m²)
            </p>
            <div class="mt-2 text-xs text-gray-400">
              <span class="font-bold text-gray-300">Valores padrão:</span>
              V₀ = {{ normas.nbr_6123.vento_default.v0_mps }} m/s, S₁ =
              {{ normas.nbr_6123.vento_default.s1 }}, S₂ = {{ normas.nbr_6123.vento_default.s2 }},
              S₃ = {{ normas.nbr_6123.vento_default.s3 }}, Ce =
              {{ normas.nbr_6123.vento_default.ce_externo }}, Ci =
              {{ normas.nbr_6123.vento_default.ci_interno }}
            </div>
          </div>

          <!-- NBR 8800 -->
          <div v-if="normas" class="bg-gray-900/50 rounded-lg p-4 border border-gray-700">
            <h3 class="text-blue-400 font-bold text-sm mb-1">
              {{ normas.nbr_8800.nome }}
            </h3>
            <p class="text-xs text-gray-400 mb-3">{{ normas.nbr_8800.descricao }}</p>
            <div class="grid grid-cols-2 md:grid-cols-3 gap-2 text-xs mb-3">
              <div
                v-for="(valor, chave) in normas.nbr_8800.constantes"
                :key="chave"
                class="bg-gray-800 p-2 rounded"
              >
                <div class="text-gray-500 uppercase text-[10px] break-words">
                  {{ formatarChave(chave) }}
                </div>
                <div class="text-white font-mono font-bold">{{ valor }}</div>
              </div>
            </div>
            <div class="text-xs text-gray-400">
              <span class="font-bold text-gray-300 block mb-1">Equações verificadas:</span>
              <ul class="space-y-1">
                <li
                  v-for="eq in normas.nbr_8800.equacoes"
                  :key="eq.id"
                  class="flex items-start gap-2"
                >
                  <span class="font-mono text-blue-400 text-[10px] mt-0.5">{{ eq.id }}</span>
                  <span class="text-gray-300">{{ eq.nome }}</span>
                </li>
              </ul>
            </div>
          </div>

          <!-- Defaults do GA -->
          <div v-if="normas" class="bg-gray-900/50 rounded-lg p-4 border border-gray-700">
            <h3 class="text-purple-400 font-bold text-sm mb-1">Algoritmo Genético (defaults)</h3>
            <p class="text-xs text-gray-400 mb-3">
              Valores padrão usados quando um parâmetro não é informado no payload.
            </p>
            <div class="grid grid-cols-2 md:grid-cols-3 gap-2 text-xs">
              <div
                v-for="(valor, chave) in normas.ga.defaults"
                :key="chave"
                class="bg-gray-800 p-2 rounded"
              >
                <div class="text-gray-500 uppercase text-[10px] break-words">
                  {{ String(chave) }}
                </div>
                <div class="text-white font-mono font-bold">
                  {{
                    typeof valor === 'boolean'
                      ? valor
                        ? 'Sim'
                        : 'Não'
                      : typeof valor === 'number'
                        ? Number.isInteger(valor)
                          ? valor
                          : valor.toFixed(3)
                        : valor
                  }}
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Rodapé -->
        <div class="p-4 border-t border-gray-700 text-xs text-gray-400">
          <div class="flex justify-end">
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

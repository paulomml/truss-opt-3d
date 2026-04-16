<script setup lang="ts">
import { useTrussStore } from "@/stores/useTrussStore";
import { ref, onMounted, onUnmounted, watch, computed } from "vue";

const store = useTrussStore();
const isMobile = ref(false);
const showContent = ref(false);

// Estimativa de durabilidade e corrosão baseada nas propriedades químicas e físicas do solo.
// O tipo de solo influencia diretamente a agressividade ambiental sobre o aço estrutural.
const corrosionInfo = computed(() => {
  const soil = store.form.soil_type;
  switch (soil) {
    case "Argila Mole":
      return {
        level: "Crítico",
        time: "5 a 10 anos",
        color: "text-red-400",
        icon: "lucide:alert-triangle",
        tip: "Exige fundações profundas e revestimento epóxi de alta espessura.",
      };
    case "Argila Rija":
      return {
        level: "Moderado",
        time: "15 a 20 anos",
        color: "text-yellow-400",
        icon: "lucide:alert-circle",
        tip: "Recomenda-se galvanização a fogo conforme NBR 6323.",
      };
    case "Areia Fofa":
      return {
        level: "Baixo",
        time: "> 50 anos",
        color: "text-green-400",
        icon: "lucide:shield-check",
        tip: "Pintura anticorrosiva convencional é satisfatória.",
      };
    case "Areia Compacta":
      return {
        level: "Controlado",
        time: "30 a 50 anos",
        color: "text-green-300",
        icon: "lucide:shield",
        tip: "Manutenção preventiva decenal para preservação da seção.",
      };
    case "Rocha":
      return {
        level: "Inexpressivo",
        time: "> 100 anos",
        color: "text-blue-400",
        icon: "lucide:shield-check",
        tip: "Proteção básica contra corrosão atmosférica padrão.",
      };
    default:
      return {
        level: "Indeterminado",
        time: "Variável",
        color: "text-gray-400",
        icon: "lucide:help-circle",
        tip: "Consulte laudo geotécnico para análise de agressividade.",
      };
  }
});

// Sincronização do estado reativo para exibição dos esforços internos do elemento selecionado.
watch(
  () => store.selectedMember,
  (newVal) => {
    if (newVal) {
      setTimeout(() => {
        showContent.value = true;
      }, 10);
    } else {
      showContent.value = false;
    }
  },
  { immediate: true },
);

onMounted(() => {
  const checkMobile = () => {
    isMobile.value = window.innerWidth < 1024;
  };
  checkMobile();
  window.addEventListener("resize", checkMobile);
  onUnmounted(() => window.removeEventListener("resize", checkMobile));
});

const close = () => {
  showContent.value = false;
};
</script>

<template>
  <div>
    <!-- Container de Modal Mobile: detalhamento técnico adaptado para telas reduzidas. -->
    <div
      v-if="isMobile && store.selectedMember"
      class="fixed inset-0 z-[1050] flex items-end"
    >
      <!-- Fundo translúcido para foco na informação estrutural. -->
      <Transition
        enter-active-class="transition-opacity duration-500 ease-out"
        enter-from-class="opacity-0"
        enter-to-class="opacity-100"
        leave-active-class="transition-opacity duration-400 ease-in"
        leave-from-class="opacity-100"
        leave-to-class="opacity-0"
      >
        <div
          v-if="showContent"
          class="absolute inset-0 bg-black/60 backdrop-blur-[2px]"
          @click="close"
        ></div>
      </Transition>

      <!-- Cartão de detalhes: memória de cálculo pontual por elemento. -->
      <Transition name="slide-up" @after-leave="store.selectMember(null)">
        <div
          v-if="showContent"
          class="relative w-full bg-gray-800 rounded-t-2xl p-6 space-y-4 max-h-[90vh] overflow-y-auto border-t border-gray-700 shadow-[0_-8px_30px_rgb(0,0,0,0.5)]"
        >
          <div class="flex justify-between items-start mb-2">
            <h3 class="font-bold text-white text-xl">Detalhes do Elemento</h3>
            <button
              @click="close"
              class="text-gray-400 hover:text-white p-1 transition-colors"
            >
              <Icon name="lucide:x" class="w-6 h-6" />
            </button>
          </div>

          <div class="space-y-4">
            <div class="flex justify-between border-b border-gray-700 pb-3">
              <span class="text-gray-400 text-sm font-medium"
                >ID da Barra:</span
              >
              <span class="font-mono font-bold text-lg text-white">{{
                store.selectedMember.id
              }}</span>
            </div>
            <div class="flex justify-between border-b border-gray-700 pb-3">
              <span class="text-gray-400 text-sm font-medium"
                >Grupo Estrutural:</span
              >
              <span class="font-semibold text-blue-400 text-sm">{{
                store.selectedMember.group
              }}</span>
            </div>
            <div class="flex justify-between border-b border-gray-700 pb-3">
              <span class="text-gray-400 text-sm font-medium"
                >Perfil Selecionado:</span
              >
              <span class="font-bold text-white text-sm">{{
                store.selectedMember.profile
              }}</span>
            </div>
            <div class="flex justify-between border-b border-gray-700 pb-3">
              <span class="text-gray-400 text-sm font-medium"
                >Solicitação Axial:</span
              >
              <div class="text-right">
                <span
                  :class="[
                    'font-bold font-mono block text-sm',
                    store.selectedMember.axial_force > 0
                      ? 'text-blue-400'
                      : 'text-red-400',
                  ]"
                >
                  {{
                    (Math.abs(store.selectedMember.axial_force) / 1000).toFixed(
                      2,
                    )
                  }}
                  kN
                </span>
                <span class="text-xs uppercase text-gray-400">{{
                  store.selectedMember.stress_type === "Tension"
                    ? "Tração"
                    : "Compressão"
                }}</span>
              </div>
            </div>
            <div class="pt-2">
              <div class="flex justify-between mb-2">
                <span class="text-gray-400 text-sm font-medium"
                  >Taxa de Utilização:</span
                >
                <span
                  :class="[
                    'font-bold text-lg',
                    store.selectedMember.utilization > 0.9
                      ? 'text-red-400'
                      : 'text-green-400',
                  ]"
                  >{{
                    (store.selectedMember.utilization * 100).toFixed(1)
                  }}%</span
                >
              </div>
              <div class="w-full bg-gray-700 h-3 rounded-full overflow-hidden">
                <div
                  class="h-full transition-all duration-500"
                  :class="
                    store.selectedMember.utilization > 0.9
                      ? 'bg-red-500'
                      : 'bg-green-500'
                  "
                  :style="{
                    width: `${Math.min(100, store.selectedMember.utilization * 100)}%`,
                  }"
                ></div>
              </div>
            </div>

            <!-- Indicador de durabilidade e proteção superficial. -->
            <div class="pt-4 border-t border-gray-700 mt-2">
              <div class="flex items-center gap-2 mb-1">
                <Icon
                  :name="corrosionInfo.icon"
                  :class="['w-5 h-5', corrosionInfo.color]"
                />
                <span
                  class="text-sm font-bold uppercase tracking-wider text-gray-400"
                  >Análise de Durabilidade (ISE)</span
                >
              </div>
              <div class="flex flex-col gap-1">
                <div class="flex justify-between items-end">
                  <span :class="['text-base font-bold', corrosionInfo.color]">{{
                    corrosionInfo.level
                  }}</span>
                  <span class="text-sm text-gray-400"
                    >Vida Útil Est.: {{ corrosionInfo.time }}</span
                  >
                </div>
                <p class="text-md text-gray-500 mt-1">
                  {{ corrosionInfo.tip }}
                </p>
              </div>
            </div>
          </div>
        </div>
      </Transition>
    </div>

    <!-- Interface Desktop: posicionamento fixo para inspeção dinâmica. -->
    <Transition name="fade">
      <div
        v-if="store.selectedMember && !isMobile"
        class="fixed top-8 right-8 w-80 bg-gray-800/90 backdrop-blur shadow-2xl rounded-lg border border-gray-700 p-6 z-[1050] hidden lg:block"
      >
        <div class="flex justify-between items-start mb-4">
          <h3 class="font-bold text-white text-lg">Detalhes do Elemento</h3>
          <button
            @click="store.selectMember(null)"
            class="text-gray-400 hover:text-gray-300 text-2xl"
          >
            &times;
          </button>
        </div>
        <div class="space-y-3">
          <div class="flex justify-between border-b border-gray-700 pb-2">
            <span class="text-gray-400 text-sm">ID:</span>
            <span class="font-mono font-bold text-white">{{
              store.selectedMember.id
            }}</span>
          </div>
          <div class="flex justify-between border-b border-gray-700 pb-2">
            <span class="text-gray-400 text-sm">Grupo:</span>
            <span class="font-semibold text-blue-400 text-sm">{{
              store.selectedMember.group
            }}</span>
          </div>
          <div class="flex justify-between border-b border-gray-700 pb-2">
            <span class="text-gray-400 text-sm">Perfil:</span>
            <span class="font-bold text-white text-sm">{{
              store.selectedMember.profile
            }}</span>
          </div>
          <div class="flex justify-between border-b border-gray-700 pb-2">
            <span class="text-gray-400 text-sm">Força Axial:</span>
            <span
              :class="[
                'font-bold font-mono text-sm',
                store.selectedMember.axial_force > 0
                  ? 'text-blue-400'
                  : 'text-red-400',
              ]"
            >
              {{
                (Math.abs(store.selectedMember.axial_force) / 1000).toFixed(2)
              }}
              kN<br />
              <span class="text-xs uppercase text-gray-400">{{
                store.selectedMember.stress_type === "Tension"
                  ? "Tração"
                  : "Compressão"
              }}</span>
            </span>
          </div>
          <div class="pt-2">
            <div class="flex justify-between mb-1">
              <span class="text-gray-400 text-sm">Utilização:</span>
              <span
                :class="[
                  'font-bold text-sm',
                  store.selectedMember.utilization > 0.9
                    ? 'text-red-400'
                    : 'text-green-400',
                ]"
                >{{
                  (store.selectedMember.utilization * 100).toFixed(1)
                }}%</span
              >
            </div>
            <div class="w-full bg-gray-700 h-2 rounded-full overflow-hidden">
              <div
                class="h-full transition-all duration-500"
                :class="
                  store.selectedMember.utilization > 0.9
                    ? 'bg-red-500'
                    : 'bg-green-500'
                "
                :style="{
                  width: `${Math.min(100, store.selectedMember.utilization * 100)}%`,
                }"
              ></div>
            </div>
          </div>

          <div class="pt-4 border-t border-gray-700 mt-2">
            <div class="flex items-center gap-2 mb-1">
              <Icon
                :name="corrosionInfo.icon"
                :class="['w-5 h-5', corrosionInfo.color]"
              />
              <span
                class="text-xs font-bold uppercase tracking-wider text-gray-400"
                >Vida Útil de Projeto (Solo)</span
              >
            </div>
            <div class="flex flex-col gap-1">
              <div class="flex justify-between items-end">
                <span :class="['text-sm font-bold', corrosionInfo.color]">{{
                  corrosionInfo.level
                }}</span>
                <span class="text-xs text-gray-400"
                  >Estimativa: {{ corrosionInfo.time }}</span
                >
              </div>
              <p class="text-md text-gray-500 mt-1 leading-tight">
                {{ corrosionInfo.tip }}
              </p>
            </div>
          </div>
        </div>
      </div>
    </Transition>
  </div>
</template>

<style scoped>
.fade-enter-active,
.fade-leave-active {
  transition:
    opacity 0.3s ease,
    transform 0.3s ease;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
  transform: translateY(-20px);
}

.slide-up-enter-active {
  transition:
    transform 0.5s cubic-bezier(0.16, 1, 0.3, 1),
    opacity 0.5s ease-out;
}
.slide-up-leave-active {
  transition:
    transform 0.4s cubic-bezier(0.7, 0, 0.84, 0),
    opacity 0.4s ease-in;
}
.slide-up-enter-from,
.slide-up-leave-to {
  transform: translateY(100%);
  opacity: 0;
}
</style>

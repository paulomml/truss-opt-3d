<script setup lang="ts">
import { computed, ref, onMounted, onBeforeUnmount } from "vue";
import { useTrussStore } from "@/stores/useTrussStore";
import { getCylinderData } from "@/utils/truss3d";
import type { MemberResult, NodeResult } from "@/types/truss";

const store = useTrussStore();
const isExpanded = ref(false);
const isMobile = ref(false);

onMounted(() => {
  const checkMobile = () => {
    isMobile.value = window.innerWidth < 768;
    if (window.innerWidth >= 1024) {
      isExpanded.value = true;
    } else {
      isExpanded.value = false;
    }
  };
  checkMobile();
  window.addEventListener("resize", checkMobile);

  onBeforeUnmount(() => {
    window.removeEventListener("resize", checkMobile);
  });
});

const trussResult = computed(() => store.result);

const getMemberLength = (
  member: MemberResult,
  nodes: Record<string, NodeResult>,
): number => {
  const directLength = (member as any).length;
  if (typeof directLength === "number" && directLength >= 0) {
    return directLength;
  }

  const cylinderData = getCylinderData(member, nodes);
  return cylinderData.length ?? 0;
};

const totalMembers = computed(() => trussResult.value?.members?.length ?? 0);

const totalNodes = computed(() =>
  trussResult.value?.nodes ? Object.keys(trussResult.value.nodes).length : 0,
);

const totalLength = computed(() => {
  if (!trussResult.value?.members?.length || !trussResult.value?.nodes) {
    return 0;
  }

  return trussResult.value.members.reduce((sum, member) => {
    return sum + getMemberLength(member, trussResult.value!.nodes);
  }, 0);
});

const totalWeight = computed(() => trussResult.value?.total_weight ?? 0);
const totalCost = computed(() => trussResult.value?.total_cost ?? 0);
const winningMaterial = computed(
  () => trussResult.value?.winning_material ?? "Aço",
);

const hasData = computed(
  () =>
    trussResult.value != null && totalMembers.value > 0 && totalNodes.value > 0,
);

const formattedLength = computed(() => totalLength.value.toFixed(2));
const formattedWeight = computed(() => totalWeight.value.toFixed(2));
const formattedCost = computed(() =>
  totalCost.value.toLocaleString("pt-BR", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }),
);

const toggleSummary = () => {
  isExpanded.value = !isExpanded.value;
};
</script>

<template>
  <Transition name="footer-slide">
    <footer
      v-if="hasData && !(isMobile && store.showMobileMenu)"
      class="fixed bottom-0 right-0 z-40 w-full md:left-80 md:w-auto"
    >
      <div
        class="mx-auto flex w-full flex-col border-t border-gray-700 bg-gray-900/95 backdrop-blur-sm px-4 py-4 shadow-[0_-10px_20px_-5px_rgba(0,0,0,0.3)] sm:px-6 lg:px-8"
      >
        <div
          class="summary-header flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between"
        >
          <div>
            <p class="text-sm font-semibold text-white flex items-center gap-2">
              <Icon name="lucide:clipboard-list" class="w-5 h-5" />
              Resumo da Estrutura Otimizada
            </p>
            <p class="text-xs text-gray-400 mt-1 flex gap-4">
              <span
                >Material Recomendado:
                <span class="text-blue-400 font-bold uppercase">{{
                  winningMaterial
                }}</span></span
              >
              <span v-if="isMobile"
                >Custo Estimado:
                <span class="text-green-400 font-bold"
                  >R$ {{ formattedCost }}</span
                ></span
              >
            </p>
          </div>

          <button
            type="button"
            class="summary-toggle inline-flex items-center justify-center rounded-lg border border-gray-700 bg-gray-800 hover:bg-gray-700 px-4 py-2 text-sm font-medium text-gray-200 transition"
            @click="toggleSummary"
            :aria-expanded="isExpanded"
          >
            {{ isExpanded ? "Ocultar" : "Ver Resumo" }}
          </button>
        </div>

        <div
          :class="[
            'summary-cards mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-4',
            { expanded: isExpanded, collapsed: !isExpanded },
          ]"
        >
          <div
            class="rounded-lg border border-gray-700 bg-gray-800 px-4 py-4"
            title="Exibe o valor total para a compra dos materiais."
          >
            <p class="text-xs uppercase tracking-[0.2em] text-gray-400">
              Custo Estimado
            </p>
            <p class="mt-3 text-2xl font-semibold text-green-400">
              <span class="text-sm font-normal">R$</span> {{ formattedCost }}
            </p>
            <p class="mt-2 text-sm text-gray-400">
              Custo total de aquisição dos materiais.
            </p>
          </div>

          <div
            class="rounded-lg border border-gray-700 bg-gray-800 px-4 py-4"
            title="Exibe o peso total de toda a estrutura metálica."
          >
            <p class="text-xs uppercase tracking-[0.2em] text-gray-400">
              Peso Total
            </p>
            <p class="mt-3 text-2xl font-semibold text-white">
              {{ formattedWeight }}
              <span class="text-base font-normal text-gray-400">kg</span>
            </p>
            <p class="mt-2 text-sm text-gray-400">
              Massa total considerando a liga de
              {{ winningMaterial }}.
            </p>
          </div>

          <div
            class="rounded-lg border border-gray-700 bg-gray-800 px-4 py-4"
            title="Exibe a soma do comprimento de todas as barras de metal."
          >
            <p class="text-xs uppercase tracking-[0.2em] text-gray-400">
              Comprimento Total
            </p>
            <p class="mt-3 text-2xl font-semibold text-white">
              {{ formattedLength }}
              <span class="text-base font-normal text-gray-400">m</span>
            </p>
            <p class="mt-2 text-sm text-gray-400">
              Soma do comprimento de todas as barras de metal.
            </p>
          </div>

          <div
            class="rounded-lg border border-gray-700 bg-gray-800 px-4 py-4"
            title="Exibe o número total de peças individuais."
          >
            <p class="text-xs uppercase tracking-[0.2em] text-gray-400">
              Quantidade de Peças
            </p>
            <p class="mt-3 text-2xl font-semibold text-white">
              {{ totalMembers }}
              <span class="text-base font-normal text-gray-400">un.</span>
            </p>
            <p class="mt-2 text-sm text-gray-400">
              Total de peças para fabricação.
            </p>
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

.summary-header {
  gap: 0.75rem;
}

.summary-toggle {
  display: inline-flex;
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

@media (max-width: 900px) {
  .summary-header {
    align-items: center;
    justify-content: space-between;
    gap: 1rem;
  }

  .summary-toggle {
    width: fit-content;
  }
}
</style>

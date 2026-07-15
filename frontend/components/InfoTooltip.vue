<script setup lang="ts">
import { ref, nextTick, onMounted } from 'vue';

defineProps<{ text: string }>();

const visible = ref(false);
const isMobile = ref(false);
const tooltipEl = ref<HTMLElement | null>(null);
const posTop = ref(true);

onMounted(() => {
  isMobile.value = window.innerWidth < 768;
});

function toggle() {
  visible.value = !visible.value;
  if (visible.value) {
    if (isMobile.value) {
      setTimeout(() => {
        visible.value = false;
      }, 5000);
    }
    nextTick(() => atualizarPosicao());
  }
}

function show() {
  if (!isMobile.value) {
    visible.value = true;
    nextTick(() => atualizarPosicao());
  }
}

function hide() {
  if (!isMobile.value) visible.value = false;
}

function atualizarPosicao() {
  if (!tooltipEl.value) return;
  const rect = tooltipEl.value.getBoundingClientRect();
  const espacoAcima = rect.top;
  const alturaTooltip = rect.height;
  posTop.value = espacoAcima > alturaTooltip + 4;
}
</script>

<template>
  <span class="relative inline-flex items-center">
    <button
      type="button"
      class="inline-flex items-center justify-center w-4 h-4 rounded-full text-gray-500 hover:text-blue-400 hover:bg-gray-700/50 transition-colors text-[10px] font-bold leading-none cursor-pointer select-none shrink-0 ml-1"
      @click="toggle"
      @mouseenter="show"
      @mouseleave="hide"
      aria-label="Ajuda"
    >
      ?
    </button>
    <Transition name="tooltip-fade">
      <div
        v-if="visible"
        ref="tooltipEl"
        :class="[
          'absolute z-[200] left-1/2 -translate-x-1/2 w-64 px-3 py-2 bg-gray-900 border border-gray-600 rounded-lg shadow-xl text-xs text-gray-200 leading-relaxed pointer-events-none',
          posTop ? 'bottom-full mb-2' : 'top-full mt-2',
        ]"
      >
        <div class="relative">
          {{ text }}
          <div
            :class="[
              'absolute left-1/2 -translate-x-1/2 w-0 h-0 border-l-4 border-r-4 border-transparent',
              posTop
                ? 'top-full border-t-4 border-t-gray-600'
                : 'bottom-full border-b-4 border-b-gray-600',
            ]"
          ></div>
        </div>
      </div>
    </Transition>
  </span>
</template>

<style scoped>
.tooltip-fade-enter-active,
.tooltip-fade-leave-active {
  transition: opacity 0.15s ease;
}
.tooltip-fade-enter-from,
.tooltip-fade-leave-to {
  opacity: 0;
}
</style>

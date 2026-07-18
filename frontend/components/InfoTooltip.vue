<script setup lang="ts">
import { ref, reactive, computed, nextTick, onMounted, onUnmounted } from 'vue';

const props = defineProps<{ text: string }>();
const displayText = computed(() => props.text.replace(/\\n/g, '\n'));

const visible = ref(false);
const isMobile = ref(false);
const tooltipEl = ref<HTMLElement | null>(null);
const triggerEl = ref<HTMLElement | null>(null);
const tooltipStyle = reactive({ left: '0px', top: '0px' });

onMounted(() => {
  isMobile.value = window.innerWidth < 768;
  window.addEventListener('scroll', atualizarPosicao, true);
  window.addEventListener('resize', atualizarPosicao);
});

onUnmounted(() => {
  window.removeEventListener('scroll', atualizarPosicao, true);
  window.removeEventListener('resize', atualizarPosicao);
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
  if (!tooltipEl.value || !triggerEl.value) return;

  const tooltip = tooltipEl.value;
  const trigger = triggerEl.value;
  const sidebar = trigger.closest('aside');
  if (!sidebar) return;
  const sidebarRect = sidebar.getBoundingClientRect();
  const tooltipW = tooltip.offsetWidth;
  const tooltipH = tooltip.offsetHeight;
  const margin = 8;
  const vh = window.innerHeight;

  const triggerRect = trigger.getBoundingClientRect();

  let left = sidebarRect.left + (sidebarRect.width - tooltipW) / 2;
  left = Math.max(sidebarRect.left + margin, Math.min(left, sidebarRect.right - tooltipW - margin));

  const spaceAbove = triggerRect.top - margin;
  const spaceBelow = vh - triggerRect.bottom - margin;
  let top: number;
  if (tooltipH <= spaceAbove) {
    top = triggerRect.top - tooltipH - margin;
  } else if (tooltipH <= spaceBelow) {
    top = triggerRect.bottom + margin;
  } else {
    top = Math.max(margin, vh - tooltipH - margin);
  }

  tooltipStyle.left = Math.round(left) + 'px';
  tooltipStyle.top = Math.round(top) + 'px';
}
</script>

<template>
  <span class="relative inline-flex items-center">
    <button
      ref="triggerEl"
      type="button"
      class="inline-flex items-center justify-center w-6 h-6 lg:w-4 lg:h-4 rounded-full text-gray-500 hover:text-blue-400 hover:bg-gray-700/50 transition-colors text-sm lg:text-[10px] font-bold leading-none cursor-pointer select-none shrink-0 ml-1"
      @click="toggle"
      @mouseenter="show"
      @mouseleave="hide"
      aria-label="Ajuda"
    >
      ?
    </button>
    <Teleport to="body">
      <Transition name="tooltip-fade">
        <div
          v-if="visible"
          ref="tooltipEl"
          class="fixed z-[200] w-72 px-4 py-3 bg-gray-900 border border-gray-600 rounded-lg shadow-xl text-sm text-gray-200 leading-relaxed pointer-events-none max-w-[calc(100vw-2rem)]"
          :style="tooltipStyle"
        >
          <div class="whitespace-pre-line">
            {{ displayText }}
          </div>
        </div>
      </Transition>
    </Teleport>
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

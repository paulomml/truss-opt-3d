<script setup lang="ts">
const { toasts, removeToast } = useToast();
</script>

<template>
  <!-- Sistema de notificações para alertas de projeto e status da otimização. -->
  <!-- O usuário recebe feedback imediato sobre a estabilidade ou falha do modelo. -->
  <div class="fixed top-4 right-4 z-[100] space-y-3 w-80 xs:w-72">
    <TransitionGroup name="toast">
      <div
        v-for="toast in toasts"
        :key="toast.id"
        :class="[
          'p-4 rounded-lg shadow-lg border flex items-start space-x-3 transition-all duration-300',
          toast.type === 'success'
            ? 'bg-green-900/20 border-green-700 text-green-300'
            : toast.type === 'error'
              ? 'bg-red-900/20 border-red-700 text-red-300'
              : toast.type === 'warning'
                ? 'bg-yellow-900/20 border-yellow-700 text-yellow-300'
                : 'bg-blue-900/20 border-blue-700 text-blue-300',
        ]"
      >
        <div class="flex-grow">
          <p class="text-sm font-medium">{{ toast.message }}</p>
        </div>
        <button
          @click="removeToast(toast.id)"
          class="text-gray-400 hover:text-gray-300 transition-colors flex-shrink-0"
        >
          <svg
            class="w-5 h-5"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="2"
              d="M6 18L18 6M6 6l12 12"
            />
          </svg>
        </button>
      </div>
    </TransitionGroup>
  </div>
</template>

<style scoped>
.toast-enter-from {
  opacity: 0;
  transform: translateX(30px);
}
.toast-leave-to {
  opacity: 0;
  transform: scale(0.95);
}
.toast-move {
  transition: transform 0.3s ease;
}
</style>

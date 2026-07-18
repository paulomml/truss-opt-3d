<script setup lang="ts">
import { useTrussStore } from '@/stores/useTrussStore';

const store = useTrussStore();
const { showMobileMenu } = storeToRefs(store);
</script>

<template>
  <div class="flex flex-col lg:flex-row h-screen w-full relative overflow-hidden bg-gray-900">
    <!-- Sidebar -->
    <TrussSidebar />

    <!-- Menu hamburger (mobile) -->
    <button
      v-if="!showMobileMenu"
      @click="showMobileMenu = true"
      class="lg:hidden absolute top-4 left-4 z-40 bg-gray-800 text-white p-2 rounded-lg shadow-lg"
    >
      <Icon name="lucide:menu" class="w-6 h-6" />
    </button>

    <!-- Área principal -->
    <main class="flex-1 relative flex flex-col min-w-0 pb-16 lg:pb-0">
      <LoadingOverlay />
      <TrussViewer />
      <TrussSummaryFooter />
      <MemberDetailCard />
    </main>

    <!-- Toasts -->
    <ToastContainer />
  </div>
</template>

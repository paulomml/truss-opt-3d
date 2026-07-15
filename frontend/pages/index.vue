<script setup lang="ts">
import { useTrussStore } from "@/stores/useTrussStore";

const store = useTrussStore();
const { showMobileMenu } = storeToRefs(store);
</script>

<template>
  <div class="flex h-screen overflow-hidden bg-gray-900">
    <!-- Menu hamburger (mobile) -->
    <button
      v-if="!showMobileMenu"
      @click="showMobileMenu = true"
      class="fixed top-4 left-4 z-30 md:hidden bg-gray-800 text-white p-2 rounded-lg shadow-lg"
    >
      <Icon name="lucide:menu" class="w-6 h-6" />
    </button>

    <!-- Sidebar -->
    <TrussSidebar />

    <!-- Área principal -->
    <main class="flex-1 flex flex-col relative">
      <LoadingOverlay />
      <div class="flex-1 relative">
        <TrussViewer />
      </div>
      <TrussSummaryFooter />
      <MemberDetailCard />
    </main>

    <!-- Toasts -->
    <ToastContainer />
  </div>
</template>

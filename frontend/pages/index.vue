<script setup lang="ts">
import { useTrussStore } from "~/stores/useTrussStore";
const store = useTrussStore();
</script>

<template>
  <div class="flex flex-col md:flex-row h-full w-full font-sans relative">
    <TrussSidebar />

    <!-- Interface de navegação para dispositivos móveis: acionamento do menu lateral de parâmetros estruturais. -->
    <button
      class="md:hidden absolute top-4 left-4 z-40 w-10 h-10 flex items-center justify-center bg-gray-800 text-white rounded-md shadow-md border border-gray-700 hover:bg-gray-700 transition"
      @click="store.showMobileMenu = true"
    >
      <Icon name="lucide:menu" class="w-6 h-6" />
    </button>

    <main
      class="flex-grow relative bg-gray-900 flex flex-col min-w-0 pb-16 md:pb-0"
    >
      <LoadingOverlay />
      <TrussViewer />
      <MemberDetailCard />
      <TrussSummaryFooter />
    </main>
  </div>
</template>

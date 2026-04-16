<template>
  <!-- Ponto de entrada da aplicação: orquestração de layouts, páginas e sistema de notificações. -->
  <div class="fixed inset-0 overflow-hidden">
    <NuxtLayout>
      <NuxtPage />
    </NuxtLayout>
    <ToastContainer />
  </div>
</template>

<template>
  <!-- Definição do container principal da aplicação para controle da viewport. -->
  <!-- O layout garante que a interface se adapte às dimensões da tela, mantendo a responsividade do canvas 3D. -->
  <div
    class="fixed inset-0 bg-gray-900 flex flex-col md:flex-row overflow-hidden"
  >
    <slot />
  </div>
</template>

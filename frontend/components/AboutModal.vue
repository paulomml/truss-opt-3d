<script setup lang="ts">
defineProps<{
  show: boolean;
}>();

defineEmits<{
  (e: "close"): void;
}>();
</script>

<template>
  <Transition
    enter-active-class="duration-300 ease-out"
    enter-from-class="opacity-0"
    enter-to-class="opacity-100"
    leave-active-class="duration-300 ease-in-out"
    leave-from-class="opacity-100"
    leave-to-class="opacity-0"
  >
    <div
      v-if="show"
      class="fixed inset-0 z-[200] flex items-center justify-center p-4"
    >
      <div
        class="absolute inset-0 bg-black/60 backdrop-blur-sm"
        @click="$emit('close')"
      ></div>

      <Transition
        enter-active-class="duration-300 ease-out"
        enter-from-class="opacity-0 scale-95 translate-y-4"
        enter-to-class="opacity-100 scale-100 translate-y-0"
        leave-active-class="duration-300 ease-in-out"
        leave-from-class="opacity-100 scale-100 translate-y-0"
        leave-to-class="opacity-0 scale-95 translate-y-4"
        appear
      >
        <div
          v-if="show"
          class="relative bg-gray-900 border border-gray-700 rounded-2xl shadow-2xl w-full max-w-4xl overflow-hidden flex flex-col max-h-full"
        >
          <!-- Cabeçalho -->
          <div
            class="p-6 border-b border-gray-800 flex justify-between items-center bg-gray-900/50 shrink-0"
          >
            <h2 class="text-xl font-bold text-white flex items-center gap-2">
              <Icon name="lucide:info" class="w-6 h-6 text-blue-400" />
              Sobre
            </h2>
            <button
              @click="$emit('close')"
              class="w-10 h-10 flex items-center justify-center text-gray-400 hover:text-white hover:bg-gray-800 rounded-lg transition-colors"
            >
              <Icon name="lucide:x" class="w-6 h-6" />
            </button>
          </div>

          <!-- Conteúdo -->
          <div class="p-8 overflow-y-auto space-y-12 text-gray-300">
            <div class="text-center space-y-2 mb-8">
              <h3 class="text-3xl font-black text-white tracking-tight">
                TRUSS-OPT 3D
              </h3>
              <p
                class="text-blue-400 font-medium uppercase tracking-widest text-sm"
              >
                Cálculo e Otimização de Estruturas Metálicas
              </p>
            </div>

            <!-- Seção 1 -->
            <section class="space-y-4 text-base">
              <div
                class="flex items-center gap-3 border-b border-gray-800 pb-3"
              >
                <Icon name="lucide:target" class="w-6 h-6 text-blue-400" />
                <h3
                  class="text-xl font-bold text-white uppercase tracking-wider"
                >
                  O que é o TRUSS-OPT 3D
                </h3>
              </div>
              <p class="leading-relaxed text-justify">
                O <strong>TRUSS-OPT 3D</strong> é uma solução dedicada ao
                cálculo e à otimização de treliças metálicas. Com base nos
                parâmetros fornecidos, o sistema identifica a configuração de
                perfis que assegura a viabilidade técnica e a eficiência de
                custos.
              </p>
            </section>

            <!-- Seção 2 -->
            <section class="space-y-6 text-base">
              <div
                class="flex items-center gap-3 border-b border-gray-800 pb-3"
              >
                <Icon
                  name="lucide:graduation-cap"
                  class="w-6 h-6 text-blue-400"
                />
                <h3
                  class="text-xl font-bold text-white uppercase tracking-wider"
                >
                  Contexto Acadêmico
                </h3>
              </div>
              <div
                class="bg-gray-800/50 rounded-xl p-6 border border-gray-700/50"
              >
                <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <div class="flex flex-col">
                    <span
                      class="text-gray-500 uppercase text-xs font-bold tracking-tighter"
                      >Instituição</span
                    >
                    <span class="text-gray-200 font-semibold"
                      >Universidade Estadual Vale do Acaraú (UVA)</span
                    >
                  </div>
                  <div class="flex flex-col">
                    <span
                      class="text-gray-500 uppercase text-xs font-bold tracking-tighter"
                      >Curso</span
                    >
                    <span class="text-gray-200 font-semibold"
                      >Bacharelado em Engenharia Civil</span
                    >
                  </div>
                  <div class="flex flex-col">
                    <span
                      class="text-gray-500 uppercase text-xs font-bold tracking-tighter"
                      >Disciplina</span
                    >
                    <span class="text-gray-200 font-semibold"
                      >Métodos Numéricos</span
                    >
                  </div>
                  <div class="flex flex-col">
                    <span
                      class="text-gray-500 uppercase text-xs font-bold tracking-tighter"
                      >Período</span
                    >
                    <span class="text-gray-200 font-semibold">2026.1</span>
                  </div>
                </div>
              </div>
            </section>

            <!-- Seção 3 -->
            <section class="space-y-6 text-base">
              <div
                class="flex items-center gap-3 border-b border-gray-800 pb-3"
              >
                <Icon name="lucide:users" class="w-6 h-6 text-blue-400" />
                <h3
                  class="text-xl font-bold text-white uppercase tracking-wider"
                >
                  Quem Desenvolveu
                </h3>
              </div>
              <div
                class="bg-gray-800/50 rounded-xl p-6 border border-gray-700/50"
              >
                <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <div class="flex flex-col">
                    <span
                      class="text-gray-500 uppercase text-xs font-bold tracking-tighter"
                      >Autor</span
                    >
                    <span class="text-gray-200 font-semibold"
                      >Paulo Raí Lopes de Melo</span
                    >
                  </div>
                  <div class="flex flex-col">
                    <span
                      class="text-gray-500 uppercase text-xs font-bold tracking-tighter"
                      >Professor Orientador</span
                    >
                    <span class="text-gray-200 font-semibold"
                      >Prof. Audelis Marcelo</span
                    >
                  </div>
                </div>
              </div>
            </section>

            <!-- Seção 4 -->
            <section class="space-y-4 text-base">
              <div
                class="flex items-center gap-3 border-b border-gray-800 pb-3"
              >
                <Icon name="lucide:lightbulb" class="w-6 h-6 text-yellow-400" />
                <h3
                  class="text-xl font-bold text-white uppercase tracking-wider"
                >
                  Qual problema este software resolve
                </h3>
              </div>
              <p class="leading-relaxed text-justify">
                O dimensionamento de estruturas metálicas costuma exigir
                múltiplas iterações manuais. O
                <strong>TRUSS-OPT 3D automatiza esse processo</strong>,
                realizando análises comparativas em alta velocidade para
                entregar uma solução otimizada, reduzindo o tempo de projeto e o
                consumo de materiais.
              </p>
            </section>

            <!-- Seção 5 -->
            <section class="space-y-4 text-base">
              <div
                class="flex items-center gap-3 border-b border-gray-800 pb-3"
              >
                <Icon name="lucide:settings" class="w-6 h-6 text-blue-400" />
                <h3
                  class="text-xl font-bold text-white uppercase tracking-wider"
                >
                  Como o sistema funciona por dentro
                </h3>
              </div>
              <p class="leading-relaxed text-base text-justify">
                O sistema utiliza processamento paralelo para avaliar diferentes
                materiais simultaneamente. A estrutura é analisada para
                identificar a distribuição de esforços, ajustando as seções
                transversais até que todos os critérios de segurança sejam
                atendidos. Ao final, o software apresenta a alternativa com o
                melhor custo-benefício.
              </p>
            </section>

            <!-- Seção 6 -->
            <section class="space-y-4 text-base">
              <div
                class="flex items-center gap-3 border-b border-gray-800 pb-3"
              >
                <Icon name="lucide:book" class="w-6 h-6 text-green-400" />
                <h3
                  class="text-xl font-bold text-white uppercase tracking-wider"
                >
                  Materiais e Normas
                </h3>
              </div>
              <div class="space-y-4 leading-relaxed">
                <p>
                  O sistema realiza a verificação de segurança com base na norma
                  brasileira <strong>NBR 8800</strong>, considerando quatro
                  materiais estruturais:
                </p>
                <ul class="list-disc list-inside space-y-2 ml-4">
                  <li><strong>Aço A36:</strong> Padrão, comum e barato.</li>
                  <li>
                    <strong>Aço A572 G50:</strong> Alta resistência, permite
                    peças mais finas.
                  </li>
                  <li>
                    <strong>Aço Corten:</strong> Alta resistência à ferrugem.
                  </li>
                  <li><strong>Alumínio 6061-T6:</strong> Extremamente leve.</li>
                </ul>
              </div>
            </section>

            <!-- Seção 7 -->
            <section class="space-y-4 text-base">
              <div
                class="flex items-center gap-3 border-b border-gray-800 pb-3"
              >
                <Icon name="lucide:code" class="w-6 h-6 text-blue-400" />
                <h3
                  class="text-xl font-bold text-white uppercase tracking-wider"
                >
                  Tecnologias utilizadas
                </h3>
              </div>
              <div class="space-y-4 leading-relaxed">
                <ul class="list-disc list-inside space-y-2 ml-4">
                  <li>
                    <strong>Python & FastAPI:</strong> Cálculos rápidos no
                    servidor.
                  </li>
                  <li>
                    <strong>Vue.js & Nuxt:</strong> Interface moderna e
                    dinâmica.
                  </li>
                  <li>
                    <strong>TresJS & Three.js:</strong> Desenhos em 3D no
                    navegador.
                  </li>
                  <li><strong>Tailwind CSS:</strong> Estilização visual.</li>
                </ul>
              </div>
            </section>

            <!-- Seção 10 -->
            <section class="space-y-4 text-base">
              <div
                class="flex items-center gap-3 border-b border-gray-800 pb-3"
              >
                <Icon
                  name="lucide:alert-triangle"
                  class="w-6 h-6 text-yellow-400"
                />
                <h3
                  class="text-xl font-bold text-white uppercase tracking-wider"
                >
                  Avisos importantes
                </h3>
              </div>
              <div
                class="p-6 bg-yellow-900/10 border border-yellow-700/30 rounded-xl"
              >
                <p class="leading-relaxed text-justify text-gray-300">
                  <strong>AVISO LEGAL:</strong> O TRUSS-OPT 3D foi desenvolvido
                  para <strong>fins acadêmicos e educacionais</strong>. Este
                  software <strong>NÃO SUBSTITUI</strong> a análise e assinatura
                  de um Engenheiro habilitado. Toda obra exige um projeto
                  executivo chancelado por profissional capacitado.
                </p>
              </div>
            </section>

            <!-- Seção 11 -->
            <section class="space-y-4 text-base">
              <div
                class="flex items-center gap-3 border-b border-gray-800 pb-3"
              >
                <Icon name="lucide:file-text" class="w-6 h-6 text-blue-400" />
                <h3
                  class="text-xl font-bold text-white uppercase tracking-wider"
                >
                  Licença
                </h3>
              </div>
              <p class="leading-relaxed text-justify">
                Projeto regido pela licença <strong>MIT</strong> (Código aberto
                e livre).
              </p>
            </section>
          </div>

          <!-- Rodapé -->
          <div
            class="p-6 bg-gray-800/30 border-t border-gray-800 flex justify-center shrink-0"
          >
            <button
              @click="$emit('close')"
              class="px-16 py-4 bg-blue-600 hover:bg-blue-700 text-white font-bold rounded-xl transition-all shadow-xl active:scale-95 flex items-center gap-3 uppercase tracking-widest text-sm"
            >
              <Icon name="lucide:check" class="w-6 h-6" />
              Concluir Leitura
            </button>
          </div>
        </div>
      </Transition>
    </div>
  </Transition>
</template>

<style scoped>
.overflow-y-auto::-webkit-scrollbar {
  width: 6px;
}
.overflow-y-auto::-webkit-scrollbar-thumb {
  background: rgba(59, 130, 246, 0.2);
  border-radius: 10px;
}
</style>

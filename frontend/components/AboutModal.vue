<script setup lang="ts">
/*
 Interface de definição do contrato de comunicação do modal informativo.
 O componente recebe o estado de visibilidade e emite o evento de fechamento para sincronia com o store global.
*/
defineProps<{
  show: boolean;
}>();

defineEmits<{
  (e: "close"): void;
}>();
</script>

<template>
  <!-- Transição de opacidade para o backdrop e o container do modal. -->
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
      <!-- Camada de fundo translúcida com desfoque gaussiano para isolamento visual do conteúdo. -->
      <div
        class="absolute inset-0 bg-black/60 backdrop-blur-sm"
        @click="$emit('close')"
      ></div>

      <!-- Container principal com animação de escala e deslocamento vertical. -->
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
          class="relative bg-gray-900 border border-gray-700 rounded-2xl shadow-2xl w-full max-w-4xl overflow-hidden flex flex-col max-h-[95vh]"
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
                Sistema Computacional para Dimensionamento e Otimização
                Paramétrica de Treliças Espaciais
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
                O <strong>TRUSS-OPT 3D</strong> é um sistema computacional
                desenvolvido para calcular, dimensionar e otimizar estruturas
                metálicas do tipo treliça espacial. A partir da definição
                geométrica e dos carregamentos pelo usuário, o software executa
                análises sucessivas para encontrar a combinação de perfis
                metálicos que atenda aos requisitos normativos de segurança com
                o menor peso e custo possível.
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
                O dimensionamento tradicional de estruturas de metal é um
                processo demorado. O engenheiro precisa chutar um tamanho de
                peça, calcular na mão (ou com softwares lentos) e verificar se
                suporta o peso. Se falhar, tenta uma peça maior. Se sobrar muita
                resistência, tenta uma menor para economizar. Esse processo leva
                horas ou dias. O
                <strong
                  >TRUSS-OPT 3D automatiza e extingue esse processo
                  repetitivo</strong
                >, fazendo milhares de testes por segundo e entregando a solução
                otimizada quase instantaneamente, poupando tempo e dinheiro do
                profissional.
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
                O cérebro do software funciona com
                <strong>Multiprocessamento</strong>: ele divide a tarefa em
                vários "trabalhadores" virtuais simultâneos. Cada trabalhador
                pega um tipo de metal (ex: Aço ou Alumínio) e testa a estrutura
                usando o <strong>Método dos Elementos Finitos (MEF)</strong>,
                uma técnica que fatia a estrutura inteira em pedaços minúsculos
                para descobrir exatamente onde a força atua. O sistema vai
                aumentando a espessura das peças milímetro por milímetro até que
                a estrutura seja totalmente segura. No final, os trabalhadores
                comparam os preços de mercado e exibem o vencedor.
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
                  Materiais e Normas utilizados
                </h3>
              </div>
              <div class="space-y-4 leading-relaxed">
                <p>
                  O sistema baseia todos os seus cálculos rigorosamente nas
                  exigências de segurança da norma técnica brasileira
                  <strong>NBR 8800</strong>. Ele avalia quatro materiais
                  comerciais:
                </p>
                <ul class="list-disc list-inside space-y-2 ml-4">
                  <li>
                    <strong>Aço A36:</strong> O aço estrutural padrão, mais
                    comum e barato no mercado.
                  </li>
                  <li>
                    <strong>Aço A572 G50:</strong> Aço de alta resistência,
                    suporta mais carga utilizando peças mais finas.
                  </li>
                  <li>
                    <strong>Aço Corten:</strong> Aço patinável com altíssima
                    resistência à ferrugem, sem precisar de pintura.
                  </li>
                  <li>
                    <strong>Alumínio 6061-T6:</strong> Extremamente leve, ideal
                    para situações onde o peso próprio é um problema crítico.
                  </li>
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
                  Tecnologias utilizadas no desenvolvimento
                </h3>
              </div>
              <div class="space-y-4 leading-relaxed">
                <p>
                  O projeto foi construído empregando uma arquitetura moderna e
                  de código aberto:
                </p>
                <ul class="list-disc list-inside space-y-2 ml-4">
                  <li>
                    <strong>Python & FastAPI:</strong> Para o cálculo matemático
                    paralelo e rápido no servidor (Backend).
                  </li>
                  <li>
                    <strong>Vue.js & Nuxt 4:</strong> Para a criação da
                    interface do usuário dinâmica e responsiva (Frontend).
                  </li>
                  <li>
                    <strong>TresJS & Three.js:</strong> Motores gráficos WebGL
                    para gerar os desenhos em 3D direto no navegador.
                  </li>
                  <li>
                    <strong>Tailwind CSS:</strong> Para estilização da interface
                    gráfica.
                  </li>
                </ul>
              </div>
            </section>

            <!-- Seção 8 -->
            <section class="space-y-4 text-base">
              <div
                class="flex items-center gap-3 border-b border-gray-800 pb-3"
              >
                <Icon name="lucide:cloud" class="w-6 h-6 text-blue-400" />
                <h3
                  class="text-xl font-bold text-white uppercase tracking-wider"
                >
                  Acesso ao ambiente de testes em nuvem
                </h3>
              </div>
              <p class="leading-relaxed">
                O software está disponível online publicamente na plataforma
                Render em
                <a
                  href="https://trussopt3d.onrender.com"
                  target="_blank"
                  rel="noopener noreferrer"
                  class="text-blue-400 hover:underline"
                  >https://trussopt3d.onrender.com</a
                >.
              </p>
            </section>

            <!-- Seção 9 -->
            <section class="space-y-4 text-base">
              <div
                class="flex items-center gap-3 border-b border-gray-800 pb-3"
              >
                <Icon name="lucide:github" class="w-6 h-6 text-blue-400" />
                <h3
                  class="text-xl font-bold text-white uppercase tracking-wider"
                >
                  Repositório do projeto (código-fonte)
                </h3>
              </div>
              <p class="leading-relaxed">
                O código integral do projeto é aberto e pode ser encontrado no
                GitHub em
                <a
                  href="https://github.com/paulomml/truss-opt-3d"
                  target="_blank"
                  rel="noopener noreferrer"
                  class="text-blue-400 hover:underline"
                  >https://github.com/paulomml/truss-opt-3d</a
                >.
              </p>
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
                  Limitações e avisos importantes
                </h3>
              </div>
              <div
                class="p-6 bg-yellow-900/10 border border-yellow-700/30 rounded-xl"
              >
                <p class="leading-relaxed text-justify text-gray-300">
                  <strong>AVISO LEGAL:</strong> O TRUSS-OPT 3D foi desenvolvido
                  estritamente para
                  <strong
                    >fins acadêmicos, educacionais e de estudo
                    preliminar</strong
                  >. Embora utilize métodos numéricos precisos e literatura
                  técnica consagrada, este software
                  <strong>NÃO SUBSTITUI</strong> a análise minuciosa, o cálculo
                  e a assinatura (ART/RRT) de um Engenheiro habilitado. Toda
                  obra exige um projeto executivo chancelado por profissional
                  capacitado. O autor não se responsabiliza por quaisquer danos
                  ou perdas decorrentes da utilização direta dos dados gerados
                  por este aplicativo em obras reais.
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
                  Licença de uso
                </h3>
              </div>
              <p class="leading-relaxed text-justify">
                Este projeto é regido pela Licença de Código Aberto
                <strong>MIT</strong>. Isso significa que o código pode ser lido,
                copiado, alterado e melhorado por qualquer pessoa de forma
                livre, desde que mantidos os créditos do autor original.
              </p>
            </section>

            <!-- Seção 12 -->
            <section class="space-y-4 text-base">
              <div
                class="flex items-center gap-3 border-b border-gray-800 pb-3"
              >
                <Icon name="lucide:heart" class="w-6 h-6 text-red-400" />
                <h3
                  class="text-xl font-bold text-white uppercase tracking-wider"
                >
                  Créditos e agradecimentos
                </h3>
              </div>
              <p class="leading-relaxed text-justify">
                Agradeço primeiramente ao Prof. Audelis Marcelo pela orientação
                na disciplina de Métodos Numéricos da UVA, que serviu como pilar
                intelectual para a construção matemática deste sistema. Um
                agradecimento especial também à imensa comunidade global de
                desenvolvedores <em>open source</em>, cujas bibliotecas abertas
                permitiram transformar este conceito acadêmico em uma ferramenta
                viva.
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

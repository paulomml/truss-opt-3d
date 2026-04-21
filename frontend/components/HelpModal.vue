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
              <Icon name="lucide:book-open" class="w-6 h-6 text-blue-400" />
              Ajuda
            </h2>
            <button
              @click="$emit('close')"
              class="w-10 h-10 flex items-center justify-center text-gray-400 hover:text-white hover:bg-gray-800 rounded-lg transition-colors"
            >
              <Icon name="lucide:x" class="w-6 h-6" />
            </button>
          </div>

          <!-- Conteúdo Principal -->
          <div class="p-8 overflow-y-auto space-y-12 text-gray-300">
            <div class="text-center space-y-2 mb-4">
              <div
                class="w-16 h-16 bg-blue-500/10 border border-blue-500/20 rounded-2xl flex items-center justify-center mx-auto mb-4"
              >
                <Icon name="lucide:info" class="w-8 h-8 text-blue-400" />
              </div>
              <h3 class="text-3xl font-black text-white tracking-tight">
                Bem-vindo(a) ao TRUSS-OPT 3D
              </h3>
              <p
                class="text-blue-400 font-medium uppercase tracking-widest text-sm"
              >
                Manual de Instruções
              </p>
              <p
                class="max-w-2xl mx-auto mt-4 text-base leading-relaxed text-gray-400"
              >
                Este manual apresenta o funcionamento do sistema e os conceitos
                básicos de engenharia estrutural de forma acessível.
              </p>
            </div>

            <!-- Seção 1 Primeiros Passos -->
            <section class="space-y-6">
              <div
                class="flex items-center gap-3 border-b border-gray-800 pb-3"
              >
                <Icon name="lucide:flag" class="w-6 h-6 text-blue-400" />
                <h3
                  class="text-xl font-bold text-white uppercase tracking-wider"
                >
                  Primeiros Passos
                </h3>
              </div>
              <div class="space-y-6 text-base leading-relaxed">
                <div
                  class="bg-gray-800/30 p-5 rounded-xl border border-gray-700/50"
                >
                  <p class="font-bold text-white mb-1">
                    O que é o TRUSS-OPT 3D?
                  </p>
                  <p>
                    É um sistema inteligente projetado para desenhar e calcular
                    estruturas de metal. Ele testa milhares de combinações para
                    entregar a opção mais barata e segura de acordo com as
                    normas.
                  </p>
                </div>
                <div
                  class="bg-gray-800/30 p-5 rounded-xl border border-gray-700/50"
                >
                  <p class="font-bold text-white mb-1">
                    O que é uma treliça e para que ela serve?
                  </p>
                  <p>
                    Imagine várias barras de metal ligadas pelas pontas formando
                    triângulos. Essa união é uma <strong>treliça</strong>.
                    Triângulos são excelentes para suportar grandes pesos com
                    pouco material. Elas servem para telhados, pontes, antenas e
                    palcos.
                  </p>
                </div>
                <div
                  class="bg-gray-800/30 p-5 rounded-xl border border-gray-700/50"
                >
                  <p class="font-bold text-white mb-1">
                    Como o sistema auxilia no projeto?
                  </p>
                  <p>
                    O software automatiza o dimensionamento estrutural. Após a
                    inserção das dimensões e do peso suportado, o sistema
                    identifica automaticamente as espessuras de metal adequadas.
                  </p>
                </div>
                <div
                  class="bg-gray-800/30 p-5 rounded-xl border border-gray-700/50"
                >
                  <p class="font-bold text-white mb-1">Onde fica cada coisa?</p>
                  <ul class="list-disc list-inside mt-2 space-y-2 ml-2">
                    <li>
                      <strong>Painel Lateral (Esquerda):</strong> Controle para
                      inserir medidas, peso e tipo de solo.
                    </li>
                    <li>
                      <strong>Área Central:</strong> Visualizador 3D da
                      estrutura.
                    </li>
                    <li>
                      <strong>Rodapé (Embaixo):</strong> Resultados de custo e
                      peso.
                    </li>
                  </ul>
                </div>
              </div>
            </section>

            <!-- Seção 2 Escolhendo o Tipo de Estrutura -->
            <section class="space-y-6">
              <div
                class="flex items-center gap-3 border-b border-gray-800 pb-3"
              >
                <Icon
                  name="lucide:layout-template"
                  class="w-6 h-6 text-blue-400"
                />
                <h3
                  class="text-xl font-bold text-white uppercase tracking-wider"
                >
                  Escolhendo o Tipo de Estrutura
                </h3>
              </div>
              <div class="space-y-6 text-base leading-relaxed">
                <div
                  class="bg-gray-800/30 p-5 rounded-xl border border-gray-700/50"
                >
                  <p class="font-bold text-white mb-1">
                    O que são os modelos disponíveis?
                  </p>
                  <p>
                    O sistema oferece modelos pré-definidos que auxiliam no
                    início do projeto. Selecione a tipologia que melhor atende à
                    sua necessidade.
                  </p>
                </div>
                <div
                  class="bg-gray-800/30 p-5 rounded-xl border border-gray-700/50"
                >
                  <p class="font-bold text-white mb-1">
                    Tesouras de telhado: Pratt, Howe e Fink
                  </p>
                  <ul class="list-disc list-inside mt-2 space-y-2 ml-2">
                    <li>
                      <strong>Pratt:</strong> Ótima para telhados longos e
                      retos.
                    </li>
                    <li>
                      <strong>Howe:</strong> Ideal para pendurar coisas pesadas
                      no meio do telhado.
                    </li>
                    <li>
                      <strong>Fink:</strong> Melhor opção para telhados muito
                      inclinados.
                    </li>
                  </ul>
                </div>
                <div
                  class="bg-gray-800/30 p-5 rounded-xl border border-gray-700/50"
                >
                  <p class="font-bold text-white mb-1">
                    Pontes: Warren e Pratt
                  </p>
                  <ul class="list-disc list-inside mt-2 space-y-2 ml-2">
                    <li><strong>Warren:</strong> Mais econômica em metal.</li>
                    <li>
                      <strong>Pratt:</strong> Ideal para pisos que sofrem fortes
                      impactos.
                    </li>
                  </ul>
                </div>
                <div
                  class="bg-gray-800/30 p-5 rounded-xl border border-gray-700/50"
                >
                  <p class="font-bold text-white mb-1">
                    Torres: quadrada e triangular
                  </p>
                  <ul class="list-disc list-inside mt-2 space-y-2 ml-2">
                    <li>
                      <strong>Quadrada:</strong> Estável, ideal para caixas
                      d'água.
                    </li>
                    <li>
                      <strong>Triangular:</strong> Mais leve, perfeita para
                      antenas.
                    </li>
                  </ul>
                </div>
                <div
                  class="bg-gray-800/30 p-5 rounded-xl border border-gray-700/50"
                >
                  <p class="font-bold text-white mb-1">Balanços (marquises)</p>
                  <p>
                    Estruturas presas de um lado só, como pontos de ônibus ou
                    coberturas de estádios.
                  </p>
                </div>
              </div>
            </section>

            <!-- Seção 3 Configurando as Dimensões -->
            <section class="space-y-6">
              <div
                class="flex items-center gap-3 border-b border-gray-800 pb-3"
              >
                <Icon name="lucide:ruler" class="w-6 h-6 text-blue-400" />
                <h3
                  class="text-xl font-bold text-white uppercase tracking-wider"
                >
                  Configurando as Dimensões
                </h3>
              </div>
              <div class="space-y-6 text-base leading-relaxed">
                <div
                  class="bg-gray-800/30 p-5 rounded-xl border border-gray-700/50"
                >
                  <p class="font-bold text-white mb-1">
                    O que é o Vão (comprimento)?
                  </p>
                  <p>
                    É a distância que a estrutura cobre sem pilares no meio.
                  </p>
                </div>
                <div
                  class="bg-gray-800/30 p-5 rounded-xl border border-gray-700/50"
                >
                  <p class="font-bold text-white mb-1">
                    O que é a Altura e seu impacto?
                  </p>
                  <p>
                    É a espessura vertical da peça. Estruturas mais altas tendem
                    a ser mais baratas, pois usam metais mais finos.
                  </p>
                </div>
                <div
                  class="bg-gray-800/30 p-5 rounded-xl border border-gray-700/50"
                >
                  <p class="font-bold text-white mb-1">O que é a Largura?</p>
                  <p>
                    A profundidade da estrutura. Se usar
                    <strong>0 (zero)</strong>, a análise será apenas em um
                    desenho plano (2D).
                  </p>
                </div>
                <div
                  class="bg-gray-800/30 p-5 rounded-xl border border-gray-700/50"
                >
                  <p class="font-bold text-white mb-1">
                    O que são Painéis e Divisões?
                  </p>
                  <p>
                    Define em quantos blocos a estrutura será dividida. O
                    aumento das divisões reduz o comprimento das barras,
                    aumentando sua rigidez e estabilidade.
                  </p>
                </div>
              </div>
            </section>

            <!-- Seção 4 Definindo o Carregamento -->
            <section class="space-y-6">
              <div
                class="flex items-center gap-3 border-b border-gray-800 pb-3"
              >
                <Icon name="lucide:weight" class="w-6 h-6 text-blue-400" />
                <h3
                  class="text-xl font-bold text-white uppercase tracking-wider"
                >
                  Definindo o Carregamento
                </h3>
              </div>
              <div class="space-y-6 text-base leading-relaxed">
                <div
                  class="bg-gray-800/30 p-5 rounded-xl border border-gray-700/50"
                >
                  <p class="font-bold text-white mb-1">
                    O que é carga estrutural?
                  </p>
                  <p>
                    É todo peso sobre o metal: telhas, vento, placas solares,
                    máquinas ou pessoas.
                  </p>
                </div>
                <div
                  class="bg-gray-800/30 p-5 rounded-xl border border-gray-700/50"
                >
                  <p class="font-bold text-white mb-1">
                    O que é kgf (Quilograma-força)?
                  </p>
                  <p>
                    Para fins práticos, considere o mesmo valor que o peso em
                    quilos (kg).
                  </p>
                </div>
              </div>
            </section>

            <!-- Seção 5 Solo e Fundação -->
            <section class="space-y-6">
              <div
                class="flex items-center gap-3 border-b border-gray-800 pb-3"
              >
                <Icon name="lucide:mountain" class="w-6 h-6 text-blue-400" />
                <h3
                  class="text-xl font-bold text-white uppercase tracking-wider"
                >
                  Solo e Fundação
                </h3>
              </div>
              <div class="space-y-6 text-base leading-relaxed">
                <div
                  class="bg-gray-800/30 p-5 rounded-xl border border-gray-700/50"
                >
                  <p class="font-bold text-white mb-1">
                    Por que o solo importa?
                  </p>
                  <p>
                    Se o solo for mole (argila), a estrutura pode afundar e
                    entortar o metal. O sistema avisa se o terreno é firme ou
                    mole.
                  </p>
                </div>
                <div
                  class="bg-gray-800/30 p-5 rounded-xl border border-gray-700/50"
                >
                  <p class="font-bold text-white mb-1">
                    O que são as dimensões da sapata (B e L)?
                  </p>
                  <p>
                    São a largura (B) e o comprimento (L) do bloco de concreto
                    que segura cada pé da estrutura.
                  </p>
                </div>
              </div>
            </section>

            <!-- Seção 6 Executando a Otimização -->
            <section class="space-y-6">
              <div
                class="flex items-center gap-3 border-b border-gray-800 pb-3"
              >
                <Icon name="lucide:cpu" class="w-6 h-6 text-blue-400" />
                <h3
                  class="text-xl font-bold text-white uppercase tracking-wider"
                >
                  Executando a Otimização
                </h3>
              </div>
              <div class="space-y-6 text-base leading-relaxed">
                <div
                  class="bg-gray-800/30 p-5 rounded-xl border border-gray-700/50"
                >
                  <p class="font-bold text-white mb-1">
                    O que o software faz ao iniciar a análise?
                  </p>
                  <p>
                    Ele simula milhares de vezes a construção, testando metais
                    cada vez mais grossos até encontrar a opção 100% segura com
                    o menor custo.
                  </p>
                </div>
                <div
                  class="bg-gray-800/30 p-5 rounded-xl border border-gray-700/50"
                >
                  <p class="font-bold text-white mb-1">
                    Significado das cores no progresso:
                  </p>
                  <ul class="list-disc list-inside mt-2 space-y-2 ml-2">
                    <li>Ponto <strong>Cinza</strong>: aguardando.</li>
                    <li>Ponto <strong>Laranja</strong>: calculando agora.</li>
                    <li>Ponto <strong>Verde</strong>: sucesso.</li>
                    <li>
                      Ponto <strong>Vermelho</strong>: falha (material
                      insuficiente).
                    </li>
                  </ul>
                </div>
              </div>
            </section>

            <!-- Seção 7 Explorando o Modelo 3D -->
            <section class="space-y-6">
              <div
                class="flex items-center gap-3 border-b border-gray-800 pb-3"
              >
                <Icon name="lucide:eye" class="w-6 h-6 text-blue-400" />
                <h3
                  class="text-xl font-bold text-white uppercase tracking-wider"
                >
                  Explorando o Modelo 3D
                </h3>
              </div>
              <div class="space-y-6 text-base leading-relaxed">
                <div
                  class="bg-gray-800/30 p-5 rounded-xl border border-gray-700/50"
                >
                  <p class="font-bold text-white mb-1">
                    O que representam as bolinhas e os cilindros?
                  </p>
                  <p>
                    Os tubos são as barras de metal. As bolinhas brancas são os
                    <strong>Nós</strong> (onde os soldadores ou parafusos
                    emendam as barras).
                  </p>
                </div>
                <div
                  class="bg-gray-800/30 p-5 rounded-xl border border-gray-700/50"
                >
                  <p class="font-bold text-white mb-1">
                    Mapa de cores para análise de segurança:
                  </p>
                  <ul class="list-disc list-inside mt-2 space-y-2 ml-2 text-sm">
                    <li>
                      <strong class="text-blue-400">Azul:</strong> Peça com
                      folga.
                    </li>
                    <li>
                      <strong class="text-green-400">Verde:</strong> Ideal
                      (seguro e econômico).
                    </li>
                    <li>
                      <strong class="text-yellow-400">Amarelo:</strong> Peça
                      sendo forçada, mas segura.
                    </li>
                    <li>
                      <strong class="text-red-400">Vermelho:</strong> Alerta
                      (limite de segurança).
                    </li>
                  </ul>
                </div>
              </div>
            </section>

            <!-- Seção 8 Inspecionando os Resultados -->
            <section class="space-y-6">
              <div
                class="flex items-center gap-3 border-b border-gray-800 pb-3"
              >
                <Icon name="lucide:search" class="w-6 h-6 text-blue-400" />
                <h3
                  class="text-xl font-bold text-white uppercase tracking-wider"
                >
                  Inspecionando os Resultados
                </h3>
              </div>
              <div class="space-y-6 text-base leading-relaxed">
                <div
                  class="bg-gray-800/30 p-5 rounded-xl border border-gray-700/50"
                >
                  <p class="font-bold text-white mb-1">
                    O que é a Taxa de Utilização?
                  </p>
                  <p>
                    Indica quanto da força total a peça está usando. Se for 90%,
                    está usando 90% da sua capacidade para não quebrar.
                  </p>
                </div>
                <div
                  class="bg-gray-800/30 p-5 rounded-xl border border-gray-700/50"
                >
                  <p class="font-bold text-white mb-1">Tração vs. Compressão</p>
                  <ul class="list-disc list-inside mt-2 space-y-2 ml-2">
                    <li><strong>Tração:</strong> Força esticando a peça.</li>
                    <li>
                      <strong>Compressão:</strong> Força esmagando a peça. O
                      software engrossa barras sob compressão para evitar que
                      entortem.
                    </li>
                  </ul>
                </div>
              </div>
            </section>

            <!-- Seção 9 Lendo o Resumo Final -->
            <section class="space-y-6">
              <div
                class="flex items-center gap-3 border-b border-gray-800 pb-3"
              >
                <Icon name="lucide:bar-chart-2" class="w-6 h-6 text-blue-400" />
                <h3
                  class="text-xl font-bold text-white uppercase tracking-wider"
                >
                  Lendo o Resumo Final
                </h3>
              </div>
              <div class="space-y-6 text-base leading-relaxed">
                <div
                  class="bg-gray-800/30 p-5 rounded-xl border border-gray-700/50"
                >
                  <p class="font-bold text-white mb-1">
                    O que é o Material Recomendado?
                  </p>
                  <p>
                    É a opção mais barata que atende a todos os requisitos de
                    segurança.
                  </p>
                </div>
                <div
                  class="bg-gray-800/30 p-5 rounded-xl border border-gray-700/50"
                >
                  <p class="font-bold text-white mb-1">
                    O que é o custo estimado?
                  </p>
                  <p>
                    O preço médio de mercado dos materiais (não inclui mão de
                    obra).
                  </p>
                </div>
              </div>
            </section>

            <!-- Seção 10 Dicas e Boas Práticas -->
            <section class="space-y-6">
              <div
                class="flex items-center gap-3 border-b border-gray-800 pb-3"
              >
                <Icon
                  name="lucide:check-circle-2"
                  class="w-6 h-6 text-blue-400"
                />
                <h3
                  class="text-xl font-bold text-white uppercase tracking-wider"
                >
                  Dicas e Boas Práticas
                </h3>
              </div>
              <div class="space-y-6 text-base leading-relaxed">
                <div
                  class="bg-gray-800/30 p-5 rounded-xl border border-gray-700/50"
                >
                  <p class="font-bold text-white mb-1">
                    O que significa "Aviso de Segurança"?
                  </p>
                  <p>
                    A estrutura é muito longa e rasteira, o que pode causar
                    trepidações. Recomenda-se deixá-la mais robusta aumentando a
                    altura.
                  </p>
                </div>
                <div
                  class="bg-gray-800/30 p-5 rounded-xl border border-gray-700/50"
                >
                  <p class="font-bold text-white mb-1">
                    Como utilizar o botão "Resetar Valores"?
                  </p>
                  <p>
                    Esta função restaura todos os campos para os valores de um
                    modelo padrão equilibrado.
                  </p>
                </div>
              </div>
            </section>

            <!-- Seção 11 Erros e Situações Comuns -->
            <section class="space-y-6">
              <div
                class="flex items-center gap-3 border-b border-gray-800 pb-3"
              >
                <Icon name="lucide:x-circle" class="w-6 h-6 text-blue-400" />
                <h3
                  class="text-xl font-bold text-white uppercase tracking-wider"
                >
                  Erros e Situações Comuns
                </h3>
              </div>
              <div class="space-y-6 text-base leading-relaxed">
                <div
                  class="bg-gray-800/30 p-5 rounded-xl border border-gray-700/50"
                >
                  <p class="font-bold text-white mb-1">
                    O que significa "Falha de estabilidade"?
                  </p>
                  <p>
                    O projeto desabou na simulação matemática por falta de
                    apoios corretos.
                  </p>
                </div>
                <div
                  class="bg-gray-800/30 p-5 rounded-xl border border-gray-700/50"
                >
                  <p class="font-bold text-white mb-1">
                    O que significa "Dimensionamento inviável"?
                  </p>
                  <p>
                    Mesmo com as barras mais grossas do catálogo, a estrutura
                    quebrou sob o peso informado. Diminua a carga ou mude o
                    formato.
                  </p>
                </div>
              </div>
            </section>

            <!-- Seção 12 Glossário -->
            <section class="space-y-6">
              <div
                class="flex items-center gap-3 border-b border-gray-800 pb-3"
              >
                <Icon
                  name="lucide:book-open-check"
                  class="w-6 h-6 text-blue-400"
                />
                <h3
                  class="text-xl font-bold text-white uppercase tracking-wider"
                >
                  Glossário
                </h3>
              </div>
              <div
                class="space-y-4 text-base leading-relaxed bg-gray-800/30 p-6 rounded-xl border border-gray-700/50"
              >
                <ul class="list-disc list-inside space-y-3 ml-2 text-gray-300">
                  <li>
                    <strong class="text-blue-300">Nó:</strong> Ponto onde as
                    pontas das barras se encontram e são fixadas.
                  </li>
                  <li>
                    <strong class="text-blue-300">Flambagem:</strong>
                    Encurvamento de uma peça quando submetida a esforços de
                    compressão (como uma haste flexível que dobra ao ser
                    pressionada nas pontas).
                  </li>
                </ul>
              </div>
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

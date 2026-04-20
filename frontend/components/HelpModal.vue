<script setup lang="ts">
/*
 Definição de propriedades e eventos para o manual de instruções da aplicação.
 Sendo assim, o componente garante a reatividade necessária para o controle de fluxo do modal.
*/
defineProps<{
  show: boolean;
}>();

defineEmits<{
  (e: "close"): void;
}>();
</script>

<template>
  <!-- Orquestração de transição para o manual de usuário. -->
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
      <!-- Camada de obscurecimento para foco narrativo no conteúdo de ajuda. -->
      <div
        class="absolute inset-0 bg-black/60 backdrop-blur-sm"
        @click="$emit('close')"
      ></div>

      <!-- Janela de visualização do manual com efeitos de entrada espacial. -->
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
          class="relative bg-gray-900 border border-gray-700 rounded-2xl shadow-2xl w-full max-w-5xl overflow-hidden flex flex-col max-h-[95vh]"
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
                Criamos este manual pensando em você que nunca teve contato com
                engenharia estrutural ou softwares de simulação. Aqui
                explicaremos absolutamente tudo, passo a passo, de forma clara e
                sem jargões difíceis.
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
                    É um sistema de computador inteligente projetado para
                    desenhar e calcular estruturas de metal. Ele testa milhares
                    de combinações matemáticas em poucos segundos para lhe
                    entregar a opção de construção mais barata e segura
                    possível, de acordo com as normas.
                  </p>
                </div>
                <div
                  class="bg-gray-800/30 p-5 rounded-xl border border-gray-700/50"
                >
                  <p class="font-bold text-white mb-1">
                    O que é uma treliça e para que ela serve?
                  </p>
                  <p>
                    Imagine vários pedaços de metal retos (barras) ligados pelas
                    pontas (nós), formando triângulos. Essa união de triângulos
                    é o que chamamos de <strong>treliça</strong>. A forma
                    triangular é o "segredo" da engenharia para suportar pesos
                    gigantescos gastando muito pouco material. Elas servem para
                    fazer telhados, pontes, antenas e palcos.
                  </p>
                </div>
                <div
                  class="bg-gray-800/30 p-5 rounded-xl border border-gray-700/50"
                >
                  <p class="font-bold text-white mb-1">
                    Como o software me ajuda a projetar uma estrutura?
                  </p>
                  <p>
                    Normalmente, uma pessoa teria que chutar qual grossura de
                    metal usar e fazer contas enormes no papel para ver se não
                    vai cair. Aqui, você só precisa dizer qual é o tamanho do
                    espaço que quer cobrir e o peso que a estrutura vai segurar.
                    O software faz o trabalho duro: ele "adivinha" e testa as
                    espessuras corretas para você.
                  </p>
                </div>
                <div
                  class="bg-gray-800/30 p-5 rounded-xl border border-gray-700/50"
                >
                  <p class="font-bold text-white mb-1">
                    Conheça a tela principal: onde fica cada coisa?
                  </p>
                  <ul class="list-disc list-inside mt-2 space-y-2 ml-2">
                    <li>
                      <strong>Painel Lateral (Esquerda):</strong> É o seu
                      controle remoto. Onde você insere as medidas, o peso e o
                      tipo de solo.
                    </li>
                    <li>
                      <strong>Área Central:</strong> É o Visualizador 3D. Onde o
                      esqueleto da sua estrutura vai aparecer colorido após o
                      cálculo.
                    </li>
                    <li>
                      <strong>Rodapé (Embaixo):</strong> É onde os resultados
                      financeiros e de peso aparecem após o computador terminar
                      de pensar.
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
                    O que são os modelos de estrutura disponíveis?
                  </p>
                  <p>
                    O programa já possui formatos pré-desenhados (templates)
                    para facilitar sua vida. Você só precisa escolher o formato
                    que melhor se adapta àquilo que você quer construir.
                  </p>
                </div>
                <div
                  class="bg-gray-800/30 p-5 rounded-xl border border-gray-700/50"
                >
                  <p class="font-bold text-white mb-1">
                    Tesouras de telhado: Pratt, Howe e Fink quando usar cada
                    uma?
                  </p>
                  <ul class="list-disc list-inside mt-2 space-y-2 ml-2">
                    <li>
                      <strong>Pratt:</strong> As barras inclinadas de dentro
                      apontam para o centro. É ótima para telhados longos e
                      retos.
                    </li>
                    <li>
                      <strong>Howe:</strong> As barras inclinadas apontam para
                      fora. Funciona muito bem se você for pendurar coisas
                      pesadas no meio do telhado.
                    </li>
                    <li>
                      <strong>Fink:</strong> Tem o desenho interno parecendo
                      vários "W". É a melhor opção para telhados muito
                      inclinados (como chalés).
                    </li>
                  </ul>
                </div>
                <div
                  class="bg-gray-800/30 p-5 rounded-xl border border-gray-700/50"
                >
                  <p class="font-bold text-white mb-1">
                    Pontes: Warren e Pratt entendendo a diferença
                  </p>
                  <ul class="list-disc list-inside mt-2 space-y-2 ml-2">
                    <li>
                      <strong>Warren:</strong> Forma uma sequência de triângulos
                      perfeitos. É o modelo que mais economiza metal.
                    </li>
                    <li>
                      <strong>Pratt para Pontes:</strong> Usa "cruzes" dentro
                      dos quadrados. É ideal quando o chão da ponte vai sofrer
                      impactos muito fortes.
                    </li>
                  </ul>
                </div>
                <div
                  class="bg-gray-800/30 p-5 rounded-xl border border-gray-700/50"
                >
                  <p class="font-bold text-white mb-1">
                    Torres: quadrada e triangular quando se aplicam?
                  </p>
                  <ul class="list-disc list-inside mt-2 space-y-2 ml-2">
                    <li>
                      <strong>Quadrada:</strong> Tem quatro pernas. É muito
                      fácil de construir e não balança quase nada. Ideal para
                      caixas d'água grandes.
                    </li>
                    <li>
                      <strong>Triangular:</strong> Tem três pernas. Gasta bem
                      menos material e é perfeita para antenas de rádio ou
                      internet.
                    </li>
                  </ul>
                </div>
                <div
                  class="bg-gray-800/30 p-5 rounded-xl border border-gray-700/50"
                >
                  <p class="font-bold text-white mb-1">
                    Balanços (marquises): Pratt e Warren para que servem?
                  </p>
                  <p>
                    Um "balanço" é uma estrutura que está grudada em uma parede
                    de um lado só e fica "voando" do outro (como o teto de um
                    ponto de ônibus ou a arquibancada de um estádio). Esse
                    modelo exige peças muito fortes perto da parede.
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
                    O que é o Vão (comprimento) e como escolher o valor certo?
                  </p>
                  <p>
                    É a distância exata de "pulo" que a estrutura precisa dar no
                    ar sem colocar nenhum pilar no meio do caminho. Se o seu
                    galpão tem 20 metros de largura livre, seu vão é 20.
                  </p>
                </div>
                <div
                  class="bg-gray-800/30 p-5 rounded-xl border border-gray-700/50"
                >
                  <p class="font-bold text-white mb-1">
                    O que é a Altura da estrutura e qual é o impacto dela?
                  </p>
                  <p>
                    É a espessura vertical do seu esqueleto de metal (do chão ao
                    teto da peça). <strong>Dica de ouro:</strong> estruturas
                    "gordinhas" (altas) envergam muito menos do que estruturas
                    "fininhas" (baixas). Aumentar a altura quase sempre deixa o
                    projeto mais barato, pois o programa poderá usar metais mais
                    finos.
                  </p>
                </div>
                <div
                  class="bg-gray-800/30 p-5 rounded-xl border border-gray-700/50"
                >
                  <p class="font-bold text-white mb-1">
                    O que é a Largura e o que significa colocar zero?
                  </p>
                  <p>
                    A largura é a profundidade da estrutura. Se você digitar
                    <strong>0 (zero)</strong>, o computador vai entender que
                    você quer analisar apenas um desenho plano no papel (2D). Se
                    você colocar qualquer número maior que zero (ex: 2 metros),
                    o sistema criará uma estrutura de verdade com volume (3D),
                    como um túnel ou uma caixa.
                  </p>
                </div>
                <div
                  class="bg-gray-800/30 p-5 rounded-xl border border-gray-700/50"
                >
                  <p class="font-bold text-white mb-1">
                    O que são Painéis e Divisões? Como esse número afeta a
                    estrutura?
                  </p>
                  <p>
                    As divisões dizem em quantos "quadradinhos" ou triângulos a
                    estrutura será cortada por dentro. Se você tiver um vão
                    enorme e poucas divisões, as barras de metal lá dentro
                    ficarão longas demais. Barras compridas dobram facilmente
                    igual a um espaguete (flambagem). Aumentar as divisões
                    encurta o tamanho das barras, deixando-as mais rígidas.
                  </p>
                </div>
                <div
                  class="bg-gray-800/30 p-5 rounded-xl border border-gray-700/50"
                >
                  <p class="font-bold text-white mb-1">
                    O que é a Largura do Topo? (exclusivo para torres)
                  </p>
                  <p>
                    Para torres, você pode fazer a base ser larga no chão e o
                    topo ser fininho lá no céu (formato de Torre Eiffel). Isso
                    corta o vento melhor e economiza muito metal.
                  </p>
                </div>
                <div
                  class="bg-gray-800/30 p-5 rounded-xl border border-gray-700/50"
                >
                  <p class="font-bold text-white mb-1">
                    O que são Seções? (exclusivo para torres)
                  </p>
                  <p>
                    São como se fossem os "andares" da sua torre. Se a torre tem
                    30 metros de altura e você coloca 10 seções, o programa
                    criará 10 blocos empilhados de 3 metros de altura cada.
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
                    O que é uma carga estrutural?
                  </p>
                  <p>
                    É absolutamente tudo que faz "peso" em cima do metal para
                    empurrá-lo para baixo (ou para os lados). Telhas de barro,
                    vento batendo forte, placas solares, máquinas presas,
                    pessoas andando... Tudo isso é carga.
                  </p>
                </div>
                <div
                  class="bg-gray-800/30 p-5 rounded-xl border border-gray-700/50"
                >
                  <p class="font-bold text-white mb-1">
                    Como estimar a carga total que minha estrutura vai receber?
                  </p>
                  <p>
                    Você precisa somar todos os pesos esperados. Exemplo: Se sua
                    cobertura tem 100 metros quadrados, e o telhado pesa 10 kg
                    por metro, você já tem 1.000 kg. Adicione ventos e uma boa
                    margem de segurança. (O sistema já calcula o peso do próprio
                    metal da treliça sozinho, então não precisa somar isso).
                  </p>
                </div>
                <div
                  class="bg-gray-800/30 p-5 rounded-xl border border-gray-700/50"
                >
                  <p class="font-bold text-white mb-1">
                    Em que unidade devo inserir o valor da carga?
                  </p>
                  <p>
                    A unidade solicitada é o
                    <strong>kgf (Quilograma-força)</strong>. Para efeitos
                    práticos, é o mesmo valor numérico que o peso em "quilos"
                    (kg) que você vê numa balança normal.
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
                    Por que o tipo de solo importa para uma estrutura metálica?
                  </p>
                  <p>
                    Você pode desenhar a estrutura mais forte do mundo no ar,
                    mas se ela for apoiada numa lama (argila mole), ela vai
                    afundar torta. Se uma perna afundar e a outra não, o metal
                    vai torcer e rasgar. O tipo de solo avisa ao programa se a
                    terra embaixo é firme ou mole.
                  </p>
                </div>
                <div
                  class="bg-gray-800/30 p-5 rounded-xl border border-gray-700/50"
                >
                  <p class="font-bold text-white mb-1">
                    Qual tipo de solo devo selecionar para o meu caso?
                  </p>
                  <p>
                    Tente usar o bom senso do local da obra: se for um terreno
                    muito duro, use <strong>Rocha</strong> ou
                    <strong>Areia Compacta</strong>. Se for área de alagadiço,
                    aterro novo ou terreno muito macio, escolha
                    <strong>Argila Mole</strong> ou <strong>Areia Fofa</strong>.
                  </p>
                </div>
                <div
                  class="bg-gray-800/30 p-5 rounded-xl border border-gray-700/50"
                >
                  <p class="font-bold text-white mb-1">
                    O que é o coeficiente de reação do subleito e quando usar o
                    valor customizado?
                  </p>
                  <p>
                    É o número técnico que mede a "dureza" do solo. Deixe o
                    programa cuidar disso sozinho escolhendo os solos da lista.
                    Só clique em "Customizado" se você tiver um laudo de
                    sondagem de solo feito por um engenheiro geotécnico que
                    forneça esse número exato.
                  </p>
                </div>
                <div
                  class="bg-gray-800/30 p-5 rounded-xl border border-gray-700/50"
                >
                  <p class="font-bold text-white mb-1">
                    O que são as dimensões da sapata (B e L)?
                  </p>
                  <p>
                    A sapata é o bloco de concreto que fica enterrado no chão
                    segurando o poste de metal (pilar).
                    <strong>B</strong> significa a Largura e
                    <strong>L</strong> o Comprimento dela em metros. Valores
                    maiores distribuem melhor o peso na terra.
                  </p>
                </div>
                <div
                  class="bg-gray-800/30 p-5 rounded-xl border border-gray-700/50"
                >
                  <p class="font-bold text-white mb-1">
                    Como o solo mole pode prejudicar minha estrutura?
                  </p>
                  <p>
                    Se o solo ceder, a estrutura vai tentar "puxar" e esticar as
                    peças de metal para compensar. O sistema será obrigado a
                    escolher metais muito mais grossos e caros para a estrutura
                    se aguentar enquanto o chão falha. Para evitar isso, aumente
                    o tamanho da sapata.
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
                    O que acontece quando clico em "Iniciar Análise Estrutural"?
                  </p>
                  <p>
                    A tela bloqueia por precaução e uma janela de carregamento
                    (log) aparece. Neste momento, o sistema está convertendo
                    todas as suas medidas em códigos matemáticos e enviando para
                    os nossos servidores na nuvem.
                  </p>
                </div>
                <div
                  class="bg-gray-800/30 p-5 rounded-xl border border-gray-700/50"
                >
                  <p class="font-bold text-white mb-1">
                    O que o software está fazendo durante o processamento?
                  </p>
                  <p>
                    Em vez de calcular uma vez só, ele simula a construção do
                    projeto milhares de vezes. Ele tenta usar a barra mais fina
                    possível; aplica as cargas e vê se ela quebra na simulação.
                    Se quebrar, ele troca por uma um pouco mais grossa e testa
                    de novo, até que a estrutura esteja 100% segura usando o
                    mínimo de metal possível.
                  </p>
                </div>
                <div
                  class="bg-gray-800/30 p-5 rounded-xl border border-gray-700/50"
                >
                  <p class="font-bold text-white mb-1">
                    O que significam os materiais que aparecem no log?
                  </p>
                  <p>
                    O computador coloca 4 materiais em uma corrida ao mesmo
                    tempo (Aço comum, Aço forte, Aço que não enferruja e
                    Alumínio). Ele testa todos simultaneamente para ver qual
                    gera o projeto mais barato no final.
                  </p>
                </div>
                <div
                  class="bg-gray-800/30 p-5 rounded-xl border border-gray-700/50"
                >
                  <p class="font-bold text-white mb-1">
                    Como interpretar o painel de progresso em tempo real?
                  </p>
                  <ul class="list-disc list-inside mt-2 space-y-2 ml-2">
                    <li>Ponto <strong>Cinza</strong>: na fila esperando.</li>
                    <li>
                      Ponto <strong>Laranja Pulsando</strong>: o robô está
                      calculando aquele metal agora.
                    </li>
                    <li>
                      Ponto <strong>Verde</strong>: finalizado com sucesso!
                    </li>
                    <li>
                      Ponto <strong>Vermelho</strong>: falhou, pois aquele
                      material não aguenta o peso mesmo usando as peças mais
                      grossas do catálogo.
                    </li>
                  </ul>
                </div>
                <div
                  class="bg-gray-800/30 p-5 rounded-xl border border-gray-700/50"
                >
                  <p class="font-bold text-white mb-1">
                    Posso cancelar a otimização a qualquer momento?
                  </p>
                  <p>
                    Com certeza. Se perceber que digitou um número errado (ex:
                    100.000 kg em vez de 1.000 kg), clique no botão de Cancelar
                    Análise. O processo para na hora e limpa a memória.
                  </p>
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
                    Como rotacionar, aproximar e afastar a visualização?
                  </p>
                  <ul class="list-disc list-inside mt-2 space-y-2 ml-2">
                    <li>
                      <strong>Rotacionar a câmera:</strong> Clique, segure e
                      arraste com o botão ESQUERDO do mouse (ou 1 dedo no
                      celular).
                    </li>
                    <li>
                      <strong>Mover para os lados (Pan):</strong> Clique, segure
                      e arraste com o botão DIREITO (ou 2 dedos no celular).
                    </li>
                    <li>
                      <strong>Dar Zoom:</strong> Gire a rodinha (scroll) do
                      mouse (ou faça formato de pinça com os dedos).
                    </li>
                  </ul>
                </div>
                <div
                  class="bg-gray-800/30 p-5 rounded-xl border border-gray-700/50"
                >
                  <p class="font-bold text-white mb-1">
                    O que representam as bolinhas e os cilindros no modelo?
                  </p>
                  <p>
                    Os tubos (cilindros) alongados são as barras metálicas que
                    você terá que comprar na siderúrgica. As pequenas bolinhas
                    brancas nos cantos são os <strong>Nós</strong> (onde os
                    soldador ou os parafusos vão emendar essas barras na vida
                    real).
                  </p>
                </div>
                <div
                  class="bg-gray-800/30 p-5 rounded-xl border border-gray-700/50"
                >
                  <p class="font-bold text-white mb-1">
                    O que são os símbolos de apoio (cones e blocos)?
                  </p>
                  <p>
                    Eles mostram onde a estrutura está presa no chão. O
                    <strong>Cone</strong> significa que ela está presa mas ainda
                    pode girar ligeiramente se forçada. O
                    <strong>Bloco</strong> quadrado significa que ela está
                    chumbada e completamente imóvel (engastada).
                  </p>
                </div>
                <div
                  class="bg-gray-800/30 p-5 rounded-xl border border-gray-700/50"
                >
                  <p class="font-bold text-white mb-1">
                    O que é o mapa de cores das barras (do azul ao vermelho)?
                  </p>
                  <p>
                    O TRUSS-OPT 3D pinta a estrutura com um "semáforo de perigo
                    e economia":
                  </p>
                  <ul class="list-disc list-inside mt-2 space-y-2 ml-2 text-sm">
                    <li>
                      <strong class="text-blue-400">Azul:</strong> A peça está
                      folgada, tem metal de sobra para pouco peso.
                    </li>
                    <li>
                      <strong class="text-green-400">Verde:</strong> O ideal!
                      Suporta a carga com segurança e sem desperdício de
                      material.
                    </li>
                    <li>
                      <strong class="text-yellow-400">Amarelo:</strong> Esforço
                      alto. A peça está sendo forçada, mas ainda é segura pelas
                      normas.
                    </li>
                    <li>
                      <strong class="text-red-400">Vermelho:</strong> Alerta
                      máximo de economia. A peça está trabalhando no limite de
                      segurança permitido. Foi aprovada para baratear a obra,
                      mas não permite erros na construção.
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
                    Como ver os detalhes de uma barra específica?
                  </p>
                  <p>
                    Basta clicar nela no desenho 3D. Imediatamente aparecerá uma
                    caixa com todos os detalhes técnicos daquela peça.
                  </p>
                </div>
                <div
                  class="bg-gray-800/30 p-5 rounded-xl border border-gray-700/50"
                >
                  <p class="font-bold text-white mb-1">
                    O que é a Taxa de Utilização e o que ela me diz?
                  </p>
                  <p>
                    Vai de 0% a 100%. Se a taxa for de 90%, quer dizer que ela
                    está usando 90% de toda a força que ela tem para não
                    quebrar. Quanto mais perto de 100%, mais otimizada e no
                    limite ela está.
                  </p>
                </div>
                <div
                  class="bg-gray-800/30 p-5 rounded-xl border border-gray-700/50"
                >
                  <p class="font-bold text-white mb-1">
                    O que é a Força Axial e como interpretar o valor?
                  </p>
                  <p>
                    É a quantidade de força que a barra está aguentando, medida
                    em kN (quilonewtons). Dica: multiplique esse valor por 100
                    para ter a ideia em quilos. Se a força for 10 kN, ela está
                    segurando quase 1.000 kg.
                  </p>
                </div>
                <div
                  class="bg-gray-800/30 p-5 rounded-xl border border-gray-700/50"
                >
                  <p class="font-bold text-white mb-1">
                    Qual é a diferença entre tração e compressão?
                  </p>
                  <ul class="list-disc list-inside mt-2 space-y-2 ml-2">
                    <li>
                      <strong>Tração:</strong> A força está "esticando" a peça,
                      puxando as pontas para fora (como um cabo de guerra).
                      Metais aguentam isso muito bem mesmo sendo finos.
                    </li>
                    <li>
                      <strong>Compressão:</strong> A força está "esmagando" a
                      peça para dentro. Isso é perigoso porque peças finas, ao
                      serem esmagadas, entortam para o lado e desabam (o que
                      chamamos de flambagem). O software sempre engrossa as
                      peças que sofrem compressão.
                    </li>
                  </ul>
                </div>
                <div
                  class="bg-gray-800/30 p-5 rounded-xl border border-gray-700/50"
                >
                  <p class="font-bold text-white mb-1">
                    O que é o perfil comercial atribuído a cada barra?
                  </p>
                  <p>
                    É o nome exato da peça que você vai pedir para comprar na
                    loja. O computador tenta usar o mesmo tamanho de perfil em
                    várias partes para facilitar a construção (ex: Tubo Quadrado
                    100x100).
                  </p>
                </div>
                <div
                  class="bg-gray-800/30 p-5 rounded-xl border border-gray-700/50"
                >
                  <p class="font-bold text-white mb-1">
                    O que é a análise de durabilidade e vida útil da estrutura?
                  </p>
                  <p>
                    É uma estimativa baseada no tipo de solo e ambiente
                    escolhido. Se o solo for agressivo (argila úmida) e o metal
                    escolhido for fraco à corrosão, o painel avisará sobre a
                    necessidade de manutenção.
                  </p>
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
                    Como interpretar o painel de resumo na parte inferior da
                    tela?
                  </p>
                  <p>
                    Abaixo do modelo 3D ficam os resultados numéricos finais (os
                    "troféus" do cálculo) que você usará para o orçamento e
                    fabricação.
                  </p>
                </div>
                <div
                  class="bg-gray-800/30 p-5 rounded-xl border border-gray-700/50"
                >
                  <p class="font-bold text-white mb-1">
                    O que significa "Material Recomendado"?
                  </p>
                  <p>
                    Significa que, depois do computador simular construir o
                    mesmo projeto 4 vezes com materiais diferentes, este
                    escolhido é o material que resolve o problema sem cair e que
                    resulta no menor valor financeiro final.
                  </p>
                </div>
                <div
                  class="bg-gray-800/30 p-5 rounded-xl border border-gray-700/50"
                >
                  <p class="font-bold text-white mb-1">
                    O que é o custo estimado e como ele é calculado?
                  </p>
                  <p>
                    É a multiplicação do peso total de todas as barras pelo
                    preço médio de mercado do quilo (R$/kg) daquele metal
                    específico. É uma ótima previsão para o custo de aquisição
                    (não inclui mão de obra).
                  </p>
                </div>
                <div
                  class="bg-gray-800/30 p-5 rounded-xl border border-gray-700/50"
                >
                  <p class="font-bold text-white mb-1">
                    O que representam o peso total, o comprimento total e a
                    quantidade de peças?
                  </p>
                  <ul class="list-disc list-inside mt-2 space-y-2 ml-2">
                    <li>
                      <strong>Peso Total:</strong> Essencial para alugar
                      caminhões ou guindastes para o transporte.
                    </li>
                    <li>
                      <strong>Comprimento Total:</strong> A soma do tamanho de
                      todas as barras em linha reta (para encomendar na
                      fábrica).
                    </li>
                    <li>
                      <strong>Quantidade de Peças:</strong> O número de cortes
                      individuais que o metalúrgico terá que fazer na montagem.
                    </li>
                  </ul>
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
                    Quais combinações de dimensões costumam gerar os melhores
                    resultados?
                  </p>
                  <p>
                    Regra de ouro: a Altura deve ser de 10% a 15% do Vão livre.
                    Ajuste a quantidade de divisões até que os triângulos
                    internos pareçam bem equilibrados (não esticados demais, nem
                    fechados demais).
                  </p>
                </div>
                <div
                  class="bg-gray-800/30 p-5 rounded-xl border border-gray-700/50"
                >
                  <p class="font-bold text-white mb-1">
                    O que significa o alerta de "esbeltez crítica"?
                  </p>
                  <p>
                    Significa que a estrutura é longa demais e rasteira demais.
                    Quando o vento bater, ela vai tremer e balançar muito, mesmo
                    que o metal aguente. É um aviso para você deixá-la mais
                    "robusta".
                  </p>
                </div>
                <div
                  class="bg-gray-800/30 p-5 rounded-xl border border-gray-700/50"
                >
                  <p class="font-bold text-white mb-1">
                    Por que a otimização pode não encontrar uma solução viável?
                  </p>
                  <p>
                    Se você exigir que uma pequena ponte carregue dezenas de
                    milhões de quilos, o programa vai testar o maior tubo
                    comercial possível e, ainda assim, a ponte vai quebrar no
                    simulador. Cargas extremas exigem perfis especiais
                    industriais, não tubos comuns.
                  </p>
                </div>
                <div
                  class="bg-gray-800/30 p-5 rounded-xl border border-gray-700/50"
                >
                  <p class="font-bold text-white mb-1">
                    Quando o alumínio é vantajoso em relação ao aço?
                  </p>
                  <p>
                    O Alumínio dobra fácil, então costuma perder se tiver muito
                    peso em cima dele. Mas se a estrutura for gigantesca e o seu
                    maior inimigo for tentar sustentar o próprio peso do metal
                    no ar, o alumínio vence porque é superleve.
                  </p>
                </div>
                <div
                  class="bg-gray-800/30 p-5 rounded-xl border border-gray-700/50"
                >
                  <p class="font-bold text-white mb-1">
                    Como o tipo de solo afeta o custo final da estrutura?
                  </p>
                  <p>
                    Solos ruins amolecem e fazem um dos apoios afundar mais que
                    o outro. A estrutura em cima se contorce toda, e o programa
                    precisa gastar dinheiro colocando aço extra para ela não
                    quebrar. Chão ruim custa caro.
                  </p>
                </div>
                <div
                  class="bg-gray-800/30 p-5 rounded-xl border border-gray-700/50"
                >
                  <p class="font-bold text-white mb-1">
                    Como usar o botão "Resetar Parâmetros"?
                  </p>
                  <p>
                    Se você digitou valores ruins e a estrutura travou ou ficou
                    inviável, basta apertar esse botão para esquecer tudo e
                    recomeçar do zero com um modelo padrão equilibrado.
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
                    O que fazer se a conexão com o servidor cair durante o
                    cálculo?
                  </p>
                  <p>
                    Às vezes os dados caem por instabilidade da sua internet.
                    Aguarde o alerta de erro fechar e apenas clique no botão de
                    "Iniciar Análise Estrutural" novamente.
                  </p>
                </div>
                <div
                  class="bg-gray-800/30 p-5 rounded-xl border border-gray-700/50"
                >
                  <p class="font-bold text-white mb-1">
                    O que significa "Instabilidade numérica detectada"?
                  </p>
                  <p>
                    Significa que o seu projeto desabou na matemática. A
                    estrutura ficou "solta" no ar sem apoios corretos, ou virou
                    um mecanismo (como um pêndulo) no simulador.
                  </p>
                </div>
                <div
                  class="bg-gray-800/30 p-5 rounded-xl border border-gray-700/50"
                >
                  <p class="font-bold text-white mb-1">
                    O que significa "Resistência máxima atingida. Estrutura
                    inviável"?
                  </p>
                  <p>
                    O computador pegou a barra de metal mais pesada e grossa
                    existente no catálogo e, mesmo assim, ela quebrou sob a
                    carga gigantesca que você inseriu. Diminua a carga ou mude o
                    formato.
                  </p>
                </div>
                <div
                  class="bg-gray-800/30 p-5 rounded-xl border border-gray-700/50"
                >
                  <p class="font-bold text-white mb-1">
                    Por que a tela de carregamento demora mais em estruturas
                    grandes?
                  </p>
                  <p>
                    Se você tiver um galpão enorme e colocar 20 divisões, criará
                    muitos triângulos extras. O computador terá que resolver uma
                    matriz de centenas de equações matemáticas gigantes para
                    calcular todas essas barras adicionais. Quanto maior, mais
                    segundos levará para a resposta chegar.
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
                <p class="font-bold text-white mb-4">
                  Glossário completo de termos técnicos em linguagem simples:
                </p>
                <ul class="list-disc list-inside space-y-3 ml-2 text-gray-300">
                  <li>
                    <strong class="text-blue-300">Treliça:</strong> Estrutura
                    composta somente por barras retas cujas pontas são ligadas
                    em nós, formando triângulos rígidos (sem flexão ao longo da
                    barra).
                  </li>
                  <li>
                    <strong class="text-blue-300">Nó:</strong> O "cotovelo" da
                    estrutura. O ponto exato onde várias pontas de barras se
                    encontram e são parafusadas/soldadas.
                  </li>
                  <li>
                    <strong class="text-blue-300">Banzo:</strong> A "linha da
                    coluna" da estrutura. O trilho horizontal que corre pela
                    parte superior é o Banzo Superior, e o que corre por baixo é
                    o Banzo Inferior.
                  </li>
                  <li>
                    <strong class="text-blue-300">Montante:</strong> As barras
                    internas que ficam perfeitamente retas na vertical.
                  </li>
                  <li>
                    <strong class="text-blue-300">Diagonal:</strong> As barras
                    internas que ficam inclinadas, cortando o espaço e
                    finalizando o formato do triângulo salvador.
                  </li>
                  <li>
                    <strong class="text-blue-300">Flambagem:</strong> É o
                    encurvamento de uma peça quando ela é esmagada nas pontas
                    (compressão). Pense em uma régua de plástico que, quando
                    apertada nas duas extremidades, em vez de diminuir de
                    tamanho, ela dá uma "barriga" e dobra para o lado.
                  </li>
                  <li>
                    <strong class="text-blue-300"
                      >MEF (Método dos Elementos Finitos):</strong
                    >
                    A tática matemática usada pelo servidor. Ele recorta a
                    treliça inteira em pequenos pedaços (elementos) no mundo
                    virtual e resolve uma matriz com milhares de variáveis para
                    saber exatamente qual a força que ataca cada "nó" e cada
                    barra.
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

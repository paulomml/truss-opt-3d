import { defineStore } from "pinia";
import type {
  TrussRequest,
  OptimizationResponse,
  MemberResult,
  RawTruss,
} from "@/types/truss";
import * as generators from "@/utils/trussGenerators";

export const useTrussStore = defineStore("truss", () => {
  // Estado reativo contendo os parâmetros geométricos e de carregamento da estrutura.
  // Estes dados alimentam o solver para a determinação dos esforços axiais.
  const form = reactive<TrussRequest>({
    length: 12.0,
    height: 2.5,
    width: 2.0,
    divisions: 6,
    total_load: 10000.0,
    topWidth: 1.0,
    sections: 5,
    selectedTemplate: "pratt_roof",
    soil_type: "Rocha",
    footing_b: 0.6,
    footing_l: 0.6,
    custom_ks: 80000,
  });

  const result = ref<OptimizationResponse | null>(null);
  const rawTruss = ref<RawTruss | null>(null);
  const loading = ref(false);
  const selectedMember = ref<MemberResult | null>(null);
  const showMobileMenu = ref(false);

  // Feedback de progresso multiprocessado e gerenciamento de conexão WebSocket.
  const mainProgress = ref(0);
  const currentLogs = ref<Record<string, string>>({});
  const ws = ref<WebSocket | null>(null);

  // Controle de cancelamento e integridade do estado da aplicação.
  const abortController = ref<AbortController | null>(null);
  const showTimeoutWarning = ref(false);

  const { addToast } = useToast();

  const cancelOptimization = () => {
    // Interrompe a conexão WebSocket e sinaliza para o backend abortar o pool de processos.
    if (ws.value) {
      ws.value.close();
      ws.value = null;
    }
    if (abortController.value) {
      abortController.value.abort();
      abortController.value = null;
    }

    // Reset rigoroso do estado da aplicação para limpeza de memória e retorno à tela inicial.
    // Portanto, garantimos que nenhum resíduo de cálculo anterior permaneça ativo.
    loading.value = false;
    rawTruss.value = null;
    result.value = null;
    selectedMember.value = null;
    mainProgress.value = 0;
    currentLogs.value = {};

    addToast("Operação cancelada. Estado da aplicação redefinido.", "info");
  };

  const generateRawTruss = () => {
    // Geração da topologia estrutural baseada em templates clássicos (Howe, Pratt, Warren).
    // A malha nodal e a incidência das barras são definidas antes do envio para o backend.
    let truss: RawTruss | null = null;
    const {
      length,
      height,
      width,
      divisions,
      topWidth,
      sections,
      selectedTemplate,
    } = form;

    switch (selectedTemplate) {
      case "pratt_roof":
        truss = generators.generatePrattRoof(length, height, width, divisions);
        break;
      case "howe_roof":
        truss = generators.generateHoweRoof(length, height, width, divisions);
        break;
      case "fink_roof":
        truss = generators.generateFinkRoof(length, height, width);
        break;
      case "warren_bridge":
        truss = generators.generateWarrenBridge(
          length,
          height,
          width,
          divisions,
        );
        break;
      case "pratt_bridge":
        truss = generators.generatePrattBridge(
          length,
          height,
          width,
          divisions,
        );
        break;
      case "square_tower":
        truss = generators.generateSquareTower(
          height,
          width,
          topWidth,
          sections,
        );
        break;
      case "triangular_tower":
        truss = generators.generateTriangularTower(
          height,
          width,
          topWidth,
          sections,
        );
        break;
      case "cantilever_pratt":
        truss = generators.generateCantileverPratt(
          length,
          height,
          width,
          divisions,
        );
        break;
      case "cantilever_warren":
        truss = generators.generateCantileverWarren(
          length,
          height,
          width,
          divisions,
        );
        break;
    }
    return truss;
  };

  const setRawTruss = (truss: RawTruss) => {
    rawTruss.value = truss;
    result.value = null;
    selectedMember.value = null;
  };

  const optimize = async () => {
    // Inicia o fluxo de otimização via WebSockets para feedback em tempo real.
    loading.value = true;
    mainProgress.value = 0;
    currentLogs.value = { Status: "Conectando ao servidor..." };
    showTimeoutWarning.value = false;

    try {
      let generated;
      try {
        generated = generateRawTruss();
      } catch (genErr: any) {
        throw new Error(
          "Erro na geração da geometria: " +
            (genErr.message || "parâmetros inválidos"),
        );
      }

      if (!generated) throw new Error("Falha ao gerar geometria");

      form.raw_truss = generated;
      rawTruss.value = generated;

      const payload = { ...form };
      if (
        payload.custom_ks === "" ||
        payload.custom_ks === null ||
        (typeof payload.custom_ks === "string" &&
          isNaN(Number(payload.custom_ks)))
      ) {
        payload.custom_ks = undefined;
      }

      // Definição da URL do WebSocket baseada no ambiente atual (Browser).
      const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
      const host = window.location.host;
      let wsUrl = "";

      // Tratamento específico para o ambiente de desenvolvimento do GitHub Codespaces.
      // Logo, se o usuário acessa via porta 3000, redirecionamos para a porta 8000 (Backend) diretamente.
      if (host.includes("-3000.app.github.dev")) {
        wsUrl = `${protocol}//${host.replace("-3000.", "-8000.")}/api/ws/optimize`;
      } else if (host.includes(":3000")) {
        // Caso local (ex: localhost:3000), tenta atingir o backend em localhost:8000.
        wsUrl = `${protocol}//${window.location.hostname}:8000/api/ws/optimize`;
      } else {
        // Padrão de produção: utiliza o mesmo host/porta (Nginx gerencia o roteamento).
        // Portanto, a conexão segue pelo proxy reverso unificado na porta 80.
        wsUrl = `${protocol}//${host}/api/ws/optimize`;
      }

      // Inicialização da conexão WebSocket para comunicação síncrona com o motor de cálculo.
      // Sendo assim, elimina-se o overhead de requisições HTTP repetitivas e timeouts de rede.
      ws.value = new WebSocket(wsUrl);

      ws.value.onopen = () => {
        // Envio dos parâmetros estruturais assim que o canal de comunicação é estabelecido.
        ws.value?.send(JSON.stringify(payload));
      };

      ws.value.onmessage = (event) => {
        // Processamento de eventos de progresso paralelo e resultados da análise.
        // Portanto, a interface reflete simultaneamente a atividade em todos os núcleos da CPU.
        const data = JSON.parse(event.data);

        if (data.type === "progress") {
          const payload = data.data;
          mainProgress.value = payload.main_progress || 0;
          currentLogs.value = payload.current_logs || {};
        } else if (data.type === "result") {
          // Processamento do resultado final após a convergência do solver.
          const resultData = data.data;
          const validatedData: OptimizationResponse = {
            is_structurally_stable: Boolean(resultData?.is_structurally_stable),
            status_message: String(
              resultData?.status_message || "Resposta desconhecida",
            ),
            total_weight: Number(resultData?.total_weight || 0),
            total_cost: Number(resultData?.total_cost || 0),
            winning_material: String(resultData?.winning_material || "N/A"),
            members: Array.isArray(resultData?.members)
              ? resultData.members
              : [],
            nodes:
              resultData?.nodes && typeof resultData.nodes === "object"
                ? resultData.nodes
                : {},
          };

          result.value = validatedData;
          if (validatedData.is_structurally_stable) {
            rawTruss.value = null;
            addToast("Sucesso! Estrutura otimizada com sucesso.", "success");
          } else {
            addToast(
              validatedData.status_message ||
                "A estrutura não pôde ser otimizada.",
              "warning",
            );
          }
          loading.value = false;
          ws.value?.close();
        } else if (data.type === "error") {
          addToast("Erro ao otimizar: " + data.message, "error");
          loading.value = false;
          ws.value?.close();
        }
      };

      ws.value.onerror = (err) => {
        console.error("WebSocket error:", err);
        addToast("Erro na conexão com o servidor de cálculo.", "error");
        loading.value = false;
      };

      ws.value.onclose = () => {
        if (loading.value) loading.value = false;
        ws.value = null;
      };
    } catch (err: any) {
      result.value = null;
      console.error("Optimization error:", err);
      const msg = err.message || "Erro interno no servidor de cálculo";
      addToast("Erro ao otimizar: " + msg, "error");
      loading.value = false;
    }
  };

  const selectMember = (member: MemberResult | null) => {
    selectedMember.value = member;
  };

  return {
    form,
    result,
    rawTruss,
    loading,
    mainProgress,
    currentLogs,
    selectedMember,
    showMobileMenu,
    showTimeoutWarning,
    cancelOptimization,
    setRawTruss,
    optimize,
    selectMember,
  };
});

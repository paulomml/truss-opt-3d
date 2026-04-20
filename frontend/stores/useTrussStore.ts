import { defineStore } from "pinia";
import type {
  TrussRequest,
  OptimizationResponse,
  MemberResult,
  RawTruss,
} from "@/types/truss";
import * as generators from "@/utils/trussGenerators";

export const useTrussStore = defineStore("truss", () => {
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

  // WebSocket lifecycle e tracking de progresso multiprocessado.
  const mainProgress = ref(0);
  const currentLogs = ref<Record<string, string>>({});
  const ws = ref<WebSocket | null>(null);

  // Controle de cancelamento e integridade do estado da aplicação.
  const abortController = ref<AbortController | null>(null);
  const showTimeoutWarning = ref(false);

  const { addToast } = useToast();

  const cancelOptimization = () => {
    // Force close do stream e sinalização de aborto para tasks assíncronas.
    if (ws.value) {
      ws.value.close();
      ws.value = null;
    }
    if (abortController.value) {
      abortController.value.abort();
      abortController.value = null;
    }

    // Cleanup do estado para prevenir memory leaks e inconsistência visual (stale state).
    loading.value = false;
    rawTruss.value = null;
    result.value = null;
    selectedMember.value = null;
    mainProgress.value = 0;
    currentLogs.value = {};
  };

  const handleCancel = () => {
    cancelOptimization();
    addToast(
      "O cálculo foi cancelado pelo usuário. Os parâmetros foram redefinidos para os valores padrão.",
      "info",
    );
  };

  const generateRawTruss = () => {
    // Graph factory: Converte parâmetros reativos em topologia nodal e de membros.
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
    // Workflow de otimização estrutural.
    // Justificativa: WebSockets eliminam o overhead de polling HTTP e mitigam timeouts em modelos CPU-bound.
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

      // Configuração de URL unificada que utiliza o proxy do Nuxt (Dev) ou Nginx (Prod).
      // Isso resolve problemas de CORS/Auth em ambientes como GitHub Codespaces.
      const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
      const host = window.location.host;
      const wsUrl = `${protocol}//${host}/api/ws/optimize`;

      // Trade-off: Statefulness e complexidade de handshake em troca de latência mínima e streaming granular.
      ws.value = new WebSocket(wsUrl);

      ws.value.onopen = () => {
        // Injeção do payload estrutural assim que o canal de sinalização é aberto.
        ws.value?.send(JSON.stringify(payload));
      };

      ws.value.onmessage = (event) => {
        // Stream de eventos de progresso e persistência dos resultados.
        const data = JSON.parse(event.data);

        if (data.type === "progress") {
          const payload = data.data;
          mainProgress.value = payload.main_progress || 0;
          currentLogs.value = payload.current_logs || {};
        } else if (data.type === "result") {
          // Commit do resultado final e validação de estabilidade estrutural.
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
            // Purge da malha preliminar para liberar a heap; o renderer consome o grafo otimizado.
            rawTruss.value = null;
            addToast(
              validatedData.status_message || "Análise concluída. O dimensionamento estrutural foi concluído com sucesso.",
              "success",
            );
          } else {
            addToast(
              validatedData.status_message ||
                "A análise estrutural não pôde ser concluída com os parâmetros atuais.",
              "warning",
            );
            // Justificativa: Não chamamos cancelOptimization() aqui para manter o result.value acessível na UI (ex: Sidebar).
          }
          loading.value = false;
          ws.value?.close();
        } else if (data.type === "error") {
          addToast(
            "Falha no processamento da estrutura: " + data.message,
            "error",
          );
          cancelOptimization();
          ws.value?.close();
        }
      };

      ws.value.onerror = (err) => {
        console.error("WebSocket error:", err);
        addToast(
          "Falha na comunicação com o servidor de cálculo. Verifique a conexão de rede e tente novamente.",
          "error",
        );
        cancelOptimization();
      };

      ws.value.onclose = () => {
        // Watcher para quedas silenciosas de socket durante processos CPU-bound no backend.
        if (loading.value) {
          addToast(
            "A conexão com o servidor foi perdida durante o processamento. É necessário reiniciar o cálculo.",
            "error",
          );
          cancelOptimization();
        }
        ws.value = null;
      };
    } catch (err: any) {
      result.value = null;
      console.error("Optimization error:", err);
      const msg = err.message || "Erro interno no servidor de cálculo";
      addToast("Falha no processamento da estrutura: " + msg, "error");
      cancelOptimization();
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
    cancelOptimization: handleCancel,
    setRawTruss,
    optimize,
    selectMember,
  };
});

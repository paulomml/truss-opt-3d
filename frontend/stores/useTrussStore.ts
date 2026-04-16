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

  const { addToast } = useToast();

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
    // Gatilho para execução da análise de elementos finitos e otimização de custo.
    // O processo é assíncrono devido à complexidade computacional da resolução do sistema matricial.
    loading.value = true;
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

      // Sincronização e sanitização dos dados para envio ao endpoint de cálculo.
      const payload = { ...form };
      if (
        payload.custom_ks === "" ||
        payload.custom_ks === null ||
        (typeof payload.custom_ks === "string" &&
          isNaN(Number(payload.custom_ks)))
      ) {
        payload.custom_ks = undefined;
      }

      const backendUrl = "/api/optimize";
      const data = await $fetch<OptimizationResponse>(backendUrl, {
        method: "POST",
        body: payload,
      });

      const validatedData: OptimizationResponse = {
        is_structurally_stable: Boolean(data?.is_structurally_stable),
        status_message: String(data?.status_message || "Resposta desconhecida"),
        total_weight: Number(data?.total_weight || 0),
        total_cost: Number(data?.total_cost || 0),
        winning_material: String(data?.winning_material || "N/A"),
        members: Array.isArray(data?.members) ? data.members : [],
        nodes: data?.nodes && typeof data.nodes === "object" ? data.nodes : {},
      };

      result.value = validatedData;
      if (validatedData.is_structurally_stable) {
        rawTruss.value = null;
        addToast("Sucesso! Estrutura otimizada com sucesso.", "success");
      } else {
        addToast(
          "Atenção: " +
            (validatedData.status_message ||
              "A estrutura não pôde ser otimizada."),
          "warning",
        );
      }
    } catch (err: any) {
      result.value = null;
      console.error("Optimization error:", err);
      const msg =
        err.data?.detail?.toString() ||
        err.message ||
        "Erro interno no servidor de cálculo";
      addToast("Erro ao otimizar: " + msg, "error");
    } finally {
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
    selectedMember,
    showMobileMenu,
    setRawTruss,
    optimize,
    selectMember,
  };
});

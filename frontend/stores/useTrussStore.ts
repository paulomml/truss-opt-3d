// stores/useTrussStore.ts: Store Pinia central do frontend.
import { defineStore } from 'pinia';
import type {
  RequisicaoOtimizacao,
  RespostaOtimizacao,
  BarraResultado,
  TrelicaBruta,
  RestricoesOtimizacao,
  ParametrosVento,
  Material,
  Perfil,
  StatusTarefa,
  TarefaResumo,
  HealthResponse,
  HealthWorkerResponse,
  NormasReferencia,
} from '@/types/truss';
import { watch } from 'vue';
import * as generators from '@/utils/trussGenerators';

export const useTrussStore = defineStore('truss', () => {
  // Estado do formulário
  const form = reactive<RequisicaoOtimizacao>({
    length: 12.0,
    height: 2.5,
    width: 2.0,
    divisions: 6,
    load_cases: [],
    soil_type: 'Rocha',
    water_lamina: 0.0,
    custom_ks: 80000,
    footing_b: 0.6,
    footing_l: 0.6,
    raw_truss: null,
    ag_geracoes: 25,
    ag_populacao: 30,
    ag_semente: 42,
    // Campos extras (não enviados ao backend).
    ...({
      dead_load: 2000.0,
      live_load: 5000.0,
      topWidth: 1.0,
      sections: 5,
      selectedTemplate: 'pratt_roof',
    } as any),
  });

  // Parâmetros de vento (NBR 6123).
  const parametrosVento = reactive<ParametrosVento>({
    v0_mps: 40.0,
    s1: 1.0,
    s2: 1.0,
    s3: 1.0,
    direcao_vento_graus: 0.0,
    ce_externo: 0.8,
    ci_interno: 0.0,
  });

  // Restrições do espaço de busca do GA.
  const restricoes = reactive<RestricoesOtimizacao>({
    materiais_permitidos: null,
    familias_permitidas: null,
    perfis_permitidos: null,
    perfis_excluidos: null,
    usar_penalidade_diversidade: true,
  });

  // Parâmetros avançados do GA (defaults do backend carregados via /api/normas).
  const agAvancado = reactive({
    usar_refinamento_local: true as boolean | null,
    probabilidade_cruzamento: null as number | null,
    probabilidade_mutacao: null as number | null,
    indice_torneio: null as number | null,
    max_perfis_distintos: null as number | null,
  });

  // Otimizações de performance (enviadas no payload ao backend).
  const modoRapido = ref<boolean>(true);
  const usarParalelismo = ref<boolean>(true);

  // Modo de desempenho do GA (frontend-only, não enviado ao backend).
  const modoDesempenho = ref<'rapido' | 'normal' | 'preciso' | 'customizado'>('normal');

  // Sincroniza presets com os campos do formulário.
  watch(modoDesempenho, (modo) => {
    switch (modo) {
      case 'rapido':
        form.ag_geracoes = 5;
        form.ag_populacao = 10;
        break;
      case 'normal':
        form.ag_geracoes = 25;
        form.ag_populacao = 30;
        break;
      case 'preciso':
        form.ag_geracoes = 50;
        form.ag_populacao = 50;
        break;
    }
  });

  // Estado da aplicação
  const result = ref<RespostaOtimizacao | null>(null);
  const rawTruss = ref<TrelicaBruta | null>(null);
  const loading = ref(false);
  const selectedMember = ref<BarraResultado | null>(null);
  const showMobileMenu = ref(false);
  const mainProgress = ref(0);
  const taskId = ref<string | null>(null);
  const showTimeoutWarning = ref(false);

  // Logs acumulados em texto (bruto, multi-linha, com prefixos [Material]).
  const logsTexto = ref('');
  // Metadados estruturados vindos do backend via WebSocket.
  const dadosProgresso = ref<Record<string, any>>({});
  // Timestamp de início da otimização (epoch ms).
  const tempoInicio = ref(0);
  // Catálogos carregados do backend.
  const materiais = ref<Material[]>([]);
  const perfis = ref<Perfil[]>([]);

  // Status de saúde do servidor e do worker Celery.
  const serverHealth = ref<HealthResponse | null>(null);
  const workerHealth = ref<HealthWorkerResponse | null>(null);
  const verificandoWorker = ref(false);

  // Histórico de tarefas (carregado sob demanda).
  const historicoTarefas = ref<TarefaResumo[]>([]);
  const carregandoHistorico = ref(false);

  // Referência de normas (caching local).
  const normasReferencia = ref<NormasReferencia | null>(null);

  // WebSocket para streaming.
  const ws = ref<WebSocket | null>(null);

  const { addToast } = useToast();

  // Ações
  const cancelOptimization = () => {
    if (ws.value) {
      ws.value.close();
      ws.value = null;
    }
    loading.value = false;
    rawTruss.value = null;
    selectedMember.value = null;
    mainProgress.value = 0;
    taskId.value = null;
    logsTexto.value = '';
    dadosProgresso.value = {};
    tempoInicio.value = 0;
  };

  const handleCancel = async () => {
    // Cancelamento real via REST: revoga a tarefa Celery no backend.
    if (taskId.value) {
      try {
        await $fetch(`/api/tarefas/${taskId.value}/cancelar`, { method: 'POST' });
        addToast('Tarefa cancelada no servidor.', 'info');
      } catch (e: any) {
        addToast('Aviso: não foi possível cancelar no servidor: ' + (e?.message || ''), 'warning');
      }
    }
    cancelOptimization();
  };

  const generateRawTruss = (): TrelicaBruta | null => {
    const { length: L, height: H, width: W, divisions: D, ...formExtra } = form as any;
    const { topWidth, sections, selectedTemplate } = formExtra;

    switch (selectedTemplate) {
      case 'pratt_roof':
        return generators.generatePrattRoof(L, H, W, D);
      case 'howe_roof':
        return generators.generateHoweRoof(L, H, W, D);
      case 'fink_roof':
        return generators.generateFinkRoof(L, H, W);
      case 'warren_bridge':
        return generators.generateWarrenBridge(L, H, W, D);
      case 'pratt_bridge':
        return generators.generatePrattBridge(L, H, W, D);
      case 'square_tower':
        return generators.generateSquareTower(H, W, topWidth, sections);
      case 'triangular_tower':
        return generators.generateTriangularTower(H, W, topWidth, sections);
      case 'cantilever_pratt':
        return generators.generateCantileverPratt(L, H, W, D);
      case 'cantilever_warren':
        return generators.generateCantileverWarren(L, H, W, D);
      default:
        return null;
    }
  };

  const setRawTruss = (truss: TrelicaBruta) => {
    rawTruss.value = truss;
    result.value = null;
    selectedMember.value = null;
  };

  const optimize = async () => {
    loading.value = true;
    mainProgress.value = 0;
    logsTexto.value = 'Status: Conectando ao servidor...';
    dadosProgresso.value = {};
    tempoInicio.value = Date.now();

    try {
      const generated = generateRawTruss();
      if (!generated) throw new Error('Falha ao gerar geometria.');

      form.raw_truss = generated;
      rawTruss.value = generated;

      // Constrói payload limpo com TODOS os parâmetros do GA + paralelismo.
      const formAny = form as any;
      const payload: RequisicaoOtimizacao = {
        length: form.length,
        height: form.height,
        width: form.width,
        divisions: form.divisions,
        soil_type: form.soil_type,
        water_lamina: form.water_lamina,
        custom_ks: form.custom_ks ?? undefined,
        footing_b: form.footing_b,
        footing_l: form.footing_l,
        raw_truss: generated,
        load_cases: [
          { type: 'G', direction: 'FY', value: -(formAny.dead_load || 0) },
          { type: 'Q', direction: 'FY', value: -(formAny.live_load || 0) },
        ],
        parametros_vento: { ...parametrosVento },
        restricoes: { ...restricoes },
        ag_geracoes: form.ag_geracoes,
        ag_populacao: form.ag_populacao,
        // Parâmetros avançados do GA (nulos = usa default do backend).
        ag_usar_refinamento_local: agAvancado.usar_refinamento_local,
        ag_probabilidade_cruzamento: agAvancado.probabilidade_cruzamento,
        ag_probabilidade_mutacao: agAvancado.probabilidade_mutacao,
        ag_indice_torneio: agAvancado.indice_torneio,
        ag_max_perfis_distintos: agAvancado.max_perfis_distintos,
        // Otimizações de performance.
        modo_rapido: modoRapido.value,
        usar_paralelismo: usarParalelismo.value,
        ag_semente: form.ag_semente || null,
      };

      // Configura WebSocket (proxy do Nuxt em dev ou Nginx em prod).
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const host = window.location.host;
      const wsUrl = `${protocol}//${host}/api/ws/otimizar`;

      ws.value = new WebSocket(wsUrl);

      ws.value.onopen = () => {
        ws.value?.send(JSON.stringify(payload));
      };

      ws.value.onmessage = (event) => {
        const data = JSON.parse(event.data);

        if (data.type === 'progress') {
          const p = data.data;
          taskId.value = p.task_id;
          mainProgress.value = p.progress || 0;
          logsTexto.value = p.logs || '';
          // Sempre mescla os dados de progresso no dadosProgresso para que
          // o frontend exiba status e progresso mesmo antes de material_atual.
          dadosProgresso.value = { ...dadosProgresso.value, ...p };
          tempoInicio.value = tempoInicio.value || Date.now();
        } else if (data.type === 'result') {
          const r = data.data;
          const validated: RespostaOtimizacao = {
            is_structurally_stable: Boolean(r?.is_structurally_stable),
            status_message: String(r?.status_message || 'Concluído'),
            total_weight: Number(r?.total_weight || 0),
            total_cost: Number(r?.total_cost || 0),
            winning_material: String(r?.winning_material || 'N/A'),
            precamber: Number(r?.precamber || 0),
            max_deflection: Number(r?.max_deflection || 0),
            real_span: Number(r?.real_span || 0),
            max_utilization: Number(r?.max_utilization || 0),
            num_perfis_distintos: Number(r?.num_perfis_distintos || 0),
            geracoes_executadas: Number(r?.geracoes_executadas || 0),
            tempo_execucao_segundos: Number(r?.tempo_execucao_segundos || 0),
            members: Array.isArray(r?.members) ? r.members : [],
            nodes: r?.nodes && typeof r.nodes === 'object' ? r.nodes : {},
            logs: Array.isArray(r?.logs) ? r.logs : [],
          };

          result.value = validated;
          if (validated.is_structurally_stable) {
            rawTruss.value = null;
            addToast(validated.status_message || 'Análise concluída com sucesso.', 'success');
          } else {
            addToast(validated.status_message || 'Estrutura não suporta a carga.', 'warning');
          }
          loading.value = false;
          if (timeoutWatcher) {
            clearInterval(timeoutWatcher);
            timeoutWatcher = null;
          }
          ws.value?.close();
        } else if (data.type === 'error') {
          addToast('Erro no cálculo: ' + data.message, 'error');
          cancelOptimization();
          ws.value?.close();
        }
      };

      ws.value.onerror = () => {
        addToast('Erro de conexão com o servidor.', 'error');
        cancelOptimization();
      };

      ws.value.onclose = () => {
        if (loading.value) {
          addToast('Conexão perdida. Tente novamente.', 'error');
          cancelOptimization();
        }
        ws.value = null;
      };
    } catch (err: any) {
      result.value = null;
      addToast('Erro: ' + (err.message || 'interno'), 'error');
      cancelOptimization();
    }
  };

  const selectMember = (member: BarraResultado | null) => {
    selectedMember.value = member;
  };

  const resetParameters = () => {
    const formAny = form as any;
    formAny.length = 12.0;
    formAny.height = 2.5;
    formAny.width = 2.0;
    formAny.divisions = 6;
    formAny.dead_load = 2000.0;
    formAny.live_load = 5000.0;
    form.water_lamina = 0.0;
    formAny.topWidth = 1.0;
    formAny.sections = 5;
    formAny.selectedTemplate = 'pratt_roof';
    form.soil_type = 'Rocha';
    form.custom_ks = 80000;
    form.footing_b = 0.6;
    form.footing_l = 0.6;
    form.ag_geracoes = 25;
    form.ag_populacao = 30;
    modoDesempenho.value = 'normal';
    agAvancado.usar_refinamento_local = true;
    agAvancado.probabilidade_cruzamento = null;
    agAvancado.probabilidade_mutacao = null;
    agAvancado.indice_torneio = null;
    agAvancado.max_perfis_distintos = null;
  };

  // Catálogos
  const carregarMateriais = async () => {
    try {
      const resp = await $fetch<Material[]>('/api/materiais');
      materiais.value = resp;
    } catch (e) {
      console.error('Erro ao carregar materiais:', e);
    }
  };

  const carregarPerfis = async () => {
    try {
      const resp = await $fetch<Perfil[]>('/api/perfis');
      perfis.value = resp;
    } catch (e) {
      console.error('Erro ao carregar perfis:', e);
    }
  };

  const baixarMemorial = async (formato: 'pdf' | 'docx') => {
    if (!taskId.value) {
      addToast('Nenhuma tarefa concluída para gerar memorial.', 'warning');
      return;
    }
    try {
      const blob = await $fetch<Blob>(`/api/tarefas/${taskId.value}/memorial/${formato}`, {
        responseType: 'blob',
      });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `memorial_tarefa_${taskId.value}.${formato}`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      addToast(`Memorial ${formato.toUpperCase()} baixado.`, 'success');
    } catch (e: any) {
      addToast('Erro ao gerar memorial: ' + (e.message || ''), 'error');
    }
  };

  // Saúde do servidor (CPU count, ambiente, versão).
  const verificarSaudeServidor = async () => {
    try {
      const resp = await $fetch<HealthResponse>('/api/health');
      serverHealth.value = resp;
      return resp;
    } catch (e) {
      console.error('Erro ao verificar saúde do servidor:', e);
      return null;
    }
  };

  // Diagnóstico do worker Celery: dispara tarefa_diagnostico e aguarda 5s.
  const verificarWorker = async () => {
    verificandoWorker.value = true;
    try {
      const resp = await $fetch<HealthWorkerResponse>('/api/health/worker', {
        timeout: 8000,
      });
      workerHealth.value = resp;
      return resp;
    } catch (e: any) {
      workerHealth.value = {
        worker_disponivel: false,
        erro: e?.message || 'Falha ao verificar worker.',
      };
      return workerHealth.value;
    } finally {
      verificandoWorker.value = false;
    }
  };

  // Histórico de tarefas: lista as N mais recentes.
  const carregarHistorico = async (limite = 20) => {
    carregandoHistorico.value = true;
    try {
      const resp = await $fetch<TarefaResumo[]>(`/api/tarefas`, {
        params: { limite },
      });
      historicoTarefas.value = resp;
      return resp;
    } catch (e) {
      console.error('Erro ao carregar histórico:', e);
      return [];
    } finally {
      carregandoHistorico.value = false;
    }
  };

  // Carrega a referência de normas NBR (cache local).
  const carregarNormas = async () => {
    if (normasReferencia.value) return normasReferencia.value;
    try {
      const resp = await $fetch<NormasReferencia>('/api/normas');
      normasReferencia.value = resp;
      // Aplica defaults do GA nos campos avançados (quando nulos).
      const defaults = resp.ga?.defaults || {};
      if (agAvancado.usar_refinamento_local === null && 'usar_refinamento_local' in defaults) {
        agAvancado.usar_refinamento_local = defaults.usar_refinamento_local as boolean;
      }
      return resp;
    } catch (e) {
      console.error('Erro ao carregar normas:', e);
      return null;
    }
  };

  return {
    // Estado
    form,
    parametrosVento,
    restricoes,
    agAvancado,
    modoRapido,
    usarParalelismo,
    result,
    rawTruss,
    loading,
    mainProgress,
    taskId,
    selectedMember,
    showMobileMenu,
    showTimeoutWarning,
    logsTexto,
    dadosProgresso,
    tempoInicio,
    modoDesempenho,
    materiais,
    perfis,
    serverHealth,
    workerHealth,
    verificandoWorker,
    historicoTarefas,
    carregandoHistorico,
    normasReferencia,
    // Ações
    cancelOptimization: handleCancel,
    setRawTruss,
    optimize,
    selectMember,
    resetParameters,
    carregarMateriais,
    carregarPerfis,
    baixarMemorial,
    verificarSaudeServidor,
    verificarWorker,
    carregarHistorico,
    carregarNormas,
  };
});

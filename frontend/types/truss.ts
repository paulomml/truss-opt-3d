// types/truss.ts: Tipos TypeScript espelhando os schemas Pydantic do backend.

export type SupportType = 'Pinned' | 'Roller' | 'Fixed' | 'None';

// Aliases de compatibilidade (usados em utils/trussGenerators.ts).
export type RawNode = NoBruto;
export type RawMember = BarraBruta;
export type RawTruss = TrelicaBruta;

export interface NoBruto {
  id: string;
  x: number;
  y: number;
  z: number;
  support: SupportType;
}

export interface BarraBruta {
  id: number;
  node_start: string;
  node_end: string;
  group?: string;
}

export interface TrelicaBruta {
  nodes: Record<string, NoBruto>;
  members: BarraBruta[];
}

export interface CasoCarga {
  type: 'G' | 'Q';
  direction: 'FX' | 'FY' | 'FZ' | 'MX' | 'MY' | 'MZ';
  value: number;
  nodes?: string[] | null;
}

export interface ParametrosVento {
  v0_mps: number;
  s1: number;
  s2: number;
  s3: number;
  direcao_vento_graus: number;
  ce_externo: number;
  ci_interno: number;
}

export interface RestricoesOtimizacao {
  materiais_permitidos?: string[] | null;
  familias_permitidas?: string[] | null;
  perfis_permitidos?: string[] | null;
  perfis_excluidos?: string[] | null;
  usar_penalidade_diversidade: boolean;
}

export interface RequisicaoOtimizacao {
  length: number;
  height: number;
  width: number;
  divisions: number;
  load_cases: CasoCarga[];
  soil_type: string;
  water_lamina: number;
  custom_ks?: number | null;
  footing_b: number;
  footing_l: number;
  raw_truss?: TrelicaBruta | null;
  parametros_vento?: ParametrosVento | null;
  restricoes?: RestricoesOtimizacao | null;
  ag_geracoes?: number | null;
  ag_populacao?: number | null;
  // Refinamento local (algoritmo memético): ativa hill climbing por geração.
  ag_usar_refinamento_local?: boolean | null;
  // Probabilidade de cruzamento (0 a 1).
  ag_probabilidade_cruzamento?: number | null;
  // Probabilidade de mutação (0 a 1).
  ag_probabilidade_mutacao?: number | null;
  // Tamanho do torneio de seleção.
  ag_indice_torneio?: number | null;
  // Máximo de perfis distintos sem penalidade.
  ag_max_perfis_distintos?: number | null;
  // Paralelismo entre materiais (legado, não usado mais).
  n_parallel?: number | null;
  // Modo rápido: pula combos de manutenção (1 kN/nó) durante o GA.
  modo_rapido?: boolean | null;
  // Paralelismo interno: avalia indivíduos em paralelo via multiprocessing.
  usar_paralelismo?: boolean | null;
  // Semente aleatória para reprodutibilidade (0 = aleatório, fixo = resultados idênticos).
  ag_semente?: number | null;
  // Tipo de estrutura/topologia (pratt_roof, howe_roof, etc.).
  truss_type?: string;
}

export interface NoResultado {
  id: string;
  x: number;
  y: number;
  z: number;
  support: SupportType;
  deslocamento_y?: number;
  deslocamento_x?: number;
  deslocamento_z?: number;
}

export interface BarraResultado {
  id: number;
  node_start: string;
  node_end: string;
  group: string;
  profile: string;
  material: string;
  axial_force: number;
  my?: number;
  mz?: number;
  utilization: number;
  stress_type: 'Tração' | 'Compressão';
  n_rd: number;
  m_rd: number;
  esbeltez: number;
  fator_chi: number;
  fator_q: number;
}

export interface RespostaOtimizacao {
  is_structurally_stable: boolean;
  status_message: string;
  total_weight: number;
  total_cost: number;
  winning_material: string;
  precamber: number;
  max_deflection: number;
  real_span: number;
  max_utilization: number;
  num_perfis_distintos: number;
  geracoes_executadas: number;
  tempo_execucao_segundos: number;
  members: BarraResultado[];
  nodes: Record<string, NoResultado>;
  logs: string[];
}

export type StatusTarefaTipo = 'PENDENTE' | 'EM_ANDAMENTO' | 'CONCLUIDO' | 'FALHOU' | 'CANCELADO';

export interface StatusTarefa {
  task_id: string;
  status: StatusTarefaTipo;
  progresso: number;
  mensagem?: string | null;
  resultado?: RespostaOtimizacao | null;
  criado_em?: string | null;
}

// Resumo de tarefa para listagem em histórico.
export interface TarefaResumo {
  task_id: string;
  status: StatusTarefaTipo;
  progresso: number;
  criado_em?: string | null;
  iniciado_em?: string | null;
  finalizado_em?: string | null;
  mensagem?: string | null;
  tem_resultado: boolean;
}

// Resposta do endpoint /api/health com metadados do servidor.
export interface HealthResponse {
  status: string;
  servico: string;
  versao: string;
  cpu_count: number;
  ambiente: string;
  celery_max_concorrencia: number;
}

// Resposta do endpoint /api/health/worker.
export interface HealthWorkerResponse {
  worker_disponivel: boolean;
  resposta?: Record<string, any>;
  erro?: string;
}

// Catálogos
export interface Material {
  id: number;
  nome: string;
  norma_referencia?: string | null;
  observacao?: string | null;
  e_gpa: number;
  fy_mpa: number;
  fu_mpa: number;
  rho_kg_m3: number;
  custo_kg: number;
}

export interface Perfil {
  id: number;
  nome: string;
  familia: string;
  h_mm: number;
  bf_mm: number;
  t_mm: number;
  area_m2: number;
  ix_m4: number;
  iy_m4: number;
  j_m4: number;
  uso_recomendado?: string | null;
  chapa_referencia?: string | null;
}

// Estrutura retornada por /api/normas (referência de constantes NBR).
export interface NormasReferencia {
  nbr_6120: {
    nome: string;
    descricao: string;
    constantes: Record<string, number>;
    combinacoes_elu: string[];
    combinacoes_els: string[];
  };
  nbr_6123: {
    nome: string;
    descricao: string;
    constantes: Record<string, number>;
    vento_default: Record<string, number>;
  };
  nbr_8800: {
    nome: string;
    descricao: string;
    constantes: Record<string, number>;
    equacoes: Array<{ id: string; nome: string }>;
  };
  ga: {
    defaults: Record<string, number | boolean>;
  };
}

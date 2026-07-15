// types/truss.ts: Tipos TypeScript espelhando os schemas Pydantic do backend.

export type SupportType = 'Pinned' | 'Roller' | 'Fixed' | 'None';

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

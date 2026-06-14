/**
 * Define um caso de carga vetorial conforme NBR 6120.
 */
export interface LoadCase {
  type: string; // 'G' (Permanente) ou 'Q' (Acidental)
  direction: string; // 'FY', 'FX', 'FZ'
  value: number; // Valor em N ou kgf
  nodes?: string[] | null; // Nós alvo (opcional)
}

/**
 * Objeto de requisição para o motor de otimização.
 */
export interface TrussRequest {
  length: number;
  height: number;
  width: number;
  divisions: number;
  load_cases: LoadCase[];
  water_lamina: number;
  dead_load?: number; // Atalho de UI
  live_load?: number; // Atalho de UI
  topWidth: number;
  sections: number;
  selectedTemplate: string;
  soil_type: string;
  custom_ks?: number;
  footing_b: number;
  footing_l: number;
  raw_truss?: RawTruss | null;
}

/**
 * Resultado da análise para um nó individual.
 */
export interface NodeResult {
  id: string;
  x: number;
  y: number;
  z: number;
  support: string;
}

/**
 * Resultado de dimensionamento para uma barra metálica.
 */
export interface MemberResult {
  id: number;
  node_start: string;
  node_end: string;
  group: string;
  profile: string;
  axial_force: number;
  utilization: number;
  stress_type: "Tração" | "Compressão" | "Nenhum" | string;
}

/**
 * Resposta final da API de otimização.
 */
export interface OptimizationResponse {
  is_structurally_stable: boolean;
  status_message: string;
  total_weight: number;
  total_cost: number;
  winning_material: string;
  precamber: number; // Contra-flecha recomendada (Item 10.2 NBR 8800)
  members: MemberResult[];
  nodes: Record<string, NodeResult>;
}

export type SupportType = "Pinned" | "Roller" | "Fixed" | "None";

export interface RawNode {
  id: string;
  x: number;
  y: number;
  z: number;
  support: SupportType;
}

export interface RawMember {
  id: number;
  node_start: string;
  node_end: string;
  profile?: string;
  group?: string;
}

export interface RawTruss {
  nodes: Record<string, RawNode>;
  members: RawMember[];
}

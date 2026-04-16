export interface TrussRequest {
  length: number;
  height: number;
  width: number;
  divisions: number;
  total_load: number;
  topWidth: number;
  sections: number;
  selectedTemplate: string;
  soil_type: string;
  custom_ks?: number;
  footing_b: number;
  footing_l: number;
  raw_truss?: RawTruss | null;
}

export interface NodeResult {
  id: string;
  x: number;
  y: number;
  z: number;
  support: string;
}

export interface MemberResult {
  id: number;
  node_start: string;
  node_end: string;
  group: string;
  profile: string;
  axial_force: number;
  utilization: number;
  stress_type: "Tension" | "Compression" | "None";
}

export interface OptimizationResponse {
  is_structurally_stable: boolean;
  status_message: string;
  total_weight: number;
  total_cost: number;
  winning_material: string;
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

// utils/truss3d.ts — Funções utilitárias para renderização 3D.
import { Vector3, Quaternion } from "three";
import type { BarraResultado, BarraBruta, NoResultado, NoBruto } from "@/types/truss";

/**
 * Calcula os dados geométricos de um cilindro que representa uma barra.
 * Retorna a posição (midpoint), quaternion (alinhamento Y → direção da barra) e comprimento.
 */
export function getCylinderData(
  member: BarraResultado | BarraBruta,
  nodes: Record<string, NoResultado | NoBruto>,
): {
  position: Vector3;
  quaternion: Quaternion;
  length: number;
} {
  const start = nodes[member.node_start];
  const end = nodes[member.node_end];

  if (!start || !end) {
    return {
      position: new Vector3(0, 0, 0),
      quaternion: new Quaternion(),
      length: 0,
    };
  }

  const startVec = new Vector3(start.x, start.y, start.z);
  const endVec = new Vector3(end.x, end.y, end.z);
  const midpoint = new Vector3().addVectors(startVec, endVec).multiplyScalar(0.5);
  const direction = new Vector3().subVectors(endVec, startVec);
  const length = direction.length();

  if (length < 0.001) {
    return { position: midpoint, quaternion: new Quaternion(), length: 0 };
  }

  // Alinha o eixo Y (default do CylinderGeometry) com a direção da barra.
  const yAxis = new Vector3(0, 1, 0);
  const quaternion = new Quaternion().setFromUnitVectors(
    yAxis,
    direction.clone().normalize(),
  );

  return { position: midpoint, quaternion, length };
}

/**
 * Retorna a cor de uma barra com base na sua taxa de utilização (U).
 * Escala: 0% = azul → 50% = verde → 80% = amarelo → 100% = vermelho.
 */
export function getMemberColor(utilization: number): string {
  const u = Math.max(0, Math.min(1, utilization));

  if (u < 0.5) {
    // Azul (0.0) → Verde (0.5).
    const t = u / 0.5;
    const r = Math.round(59 + (34 - 59) * t); // #3b82f6 → #22c55e
    const g = Math.round(130 + (197 - 130) * t);
    const b = Math.round(246 + (94 - 246) * t);
    return `#${r.toString(16).padStart(2, "0")}${g.toString(16).padStart(2, "0")}${b.toString(16).padStart(2, "0")}`;
  } else if (u < 0.8) {
    // Verde (0.5) → Amarelo (0.8).
    const t = (u - 0.5) / 0.3;
    const r = Math.round(34 + (234 - 34) * t); // #22c55e → #eab308
    const g = Math.round(197 + (179 - 197) * t);
    const b = Math.round(94 + (8 - 94) * t);
    return `#${r.toString(16).padStart(2, "0")}${g.toString(16).padStart(2, "0")}${b.toString(16).padStart(2, "0")}`;
  } else {
    // Amarelo (0.8) → Vermelho (1.0).
    const t = (u - 0.8) / 0.2;
    const r = Math.round(234 + (239 - 234) * t); // #eab308 → #ef4444
    const g = Math.round(179 + (68 - 179) * t);
    const b = Math.round(8 + (68 - 8) * t);
    return `#${r.toString(16).padStart(2, "0")}${g.toString(16).padStart(2, "0")}${b.toString(16).padStart(2, "0")}`;
  }
}

/**
 * Retorna uma cor legível para texto sobre fundo colorido.
 */
export function getContrastColor(hexColor: string): string {
  const r = parseInt(hexColor.slice(1, 3), 16);
  const g = parseInt(hexColor.slice(3, 5), 16);
  const b = parseInt(hexColor.slice(5, 7), 16);
  const luminancia = (0.299 * r + 0.587 * g + 0.114 * b) / 255;
  return luminancia > 0.5 ? "#111827" : "#ffffff";
}

/**
 * Formata um número em notação brasileira.
 */
export function formatarNumero(valor: number, casas = 2): string {
  return valor.toLocaleString("pt-BR", {
    minimumFractionDigits: casas,
    maximumFractionDigits: casas,
  });
}

/**
 * Formata um valor monetário em Real brasileiro.
 */
export function formatarMoeda(valor: number): string {
  return valor.toLocaleString("pt-BR", {
    style: "currency",
    currency: "BRL",
  });
}

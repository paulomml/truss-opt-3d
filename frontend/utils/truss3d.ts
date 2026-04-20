import { Vector3, Quaternion, Color } from "three";
import type { MemberResult, NodeResult } from "../types/truss";

export function getCylinderData(
  member: MemberResult,
  nodes: Record<string, NodeResult>,
) {
  /*
   Compute de transform para instanciamento dos cilindros (membros).
   Mapeia coordenadas nodais R3 para posição e rotação via Quaternion.
  */
  const start = nodes[member.node_start];
  const end = nodes[member.node_end];

  if (!start || !end) {
    return { position: new Vector3(), quaternion: new Quaternion(), length: 0 };
  }

  const vStart = new Vector3(start.x, start.y, start.z);
  const vEnd = new Vector3(end.x, end.y, end.z);

  const distance = vStart.distanceTo(vEnd);
  // Anchor point no centro do segmento (lerp 0.5).
  const position = vStart.clone().lerp(vEnd, 0.5);

  // Orientação via Quaternion para alinhar o eixo Y local (up) ao vetor diretor da barra.
  const direction = new Vector3().subVectors(vEnd, vStart).normalize();
  const quaternion = new Quaternion().setFromUnitVectors(
    new Vector3(0, 1, 0),
    direction,
  );

  return {
    position,
    quaternion,
    length: distance,
  };
}

export function getMemberColor(utilization: number) {
  /*
   Heatmap de utilização estrutural.
   Escala: Blue (0%) -> Green (50%) -> Red (100%+).
  */
  const u = Math.max(0, Math.min(1, utilization));
  let r, g, b;
  if (u < 0.5) {
    const t = u / 0.5;
    r = 0;
    g = t;
    b = 1 - t;
  } else {
    const t = (u - 0.5) / 0.5;
    r = t;
    g = 1 - t;
    b = 0;
  }
  return new Color(r, g, b);
}

import { Vector3, Quaternion, Color } from "three";
import type { MemberResult, NodeResult } from "../types/truss";

export function getCylinderData(
  member: MemberResult,
  nodes: Record<string, NodeResult>,
) {
  /*
   Transformação geométrica para representação espacial dos elementos de barra (cilindros).
   A posição e orientação são calculadas a partir dos vetores de posição dos nós de incidência.
  */
  const start = nodes[member.node_start];
  const end = nodes[member.node_end];

  if (!start || !end) {
    return { position: new Vector3(), quaternion: new Quaternion(), length: 0 };
  }

  const vStart = new Vector3(start.x, start.y, start.z);
  const vEnd = new Vector3(end.x, end.y, end.z);

  const distance = vStart.distanceTo(vEnd);
  // Posicionamento do centro de massa do elemento cilíndrico no ponto médio entre os nós.
  const position = vStart.clone().lerp(vEnd, 0.5);

  // Cálculo do quatérnio de rotação para alinhamento do eixo Y local ao vetor diretor da barra.
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
   Mapeamento térmico da taxa de utilização estrutural.
   A escala cromática transita do Azul (0% de solicitação) ao Vermelho (100% ou falha), passando pelo Verde.
   Sendo assim, o usuário identifica visualmente as regiões críticas da treliça.
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

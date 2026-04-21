import type { RawTruss, RawNode, RawMember, SupportType } from "@/types/truss";

function createNodeId(
  prefix: string,
  index: number,
  suffix: string = "",
): string {
  return `${prefix}${suffix}_${index}`;
}

function addNode(
  nodes: Record<string, RawNode>,
  id: string,
  x: number,
  y: number,
  z: number,
  support: SupportType = "None",
) {
  nodes[id] = { id, x, y, z, support };
}

function addMember(
  members: RawMember[],
  nodeStart: string,
  nodeEnd: string,
  group: string = "Padrão",
) {
  members.push({
    id: members.length + 1,
    node_start: nodeStart,
    node_end: nodeEnd,
    group: group,
  });
}

/**
 * Extrusão 3D via duplicação de malha e injeção de X-bracing.
 * Transforma grafos planares em estruturas espacialmente estáveis contra flambagem global e torção.
 */
function extrude3D(planar: RawTruss, width: number): RawTruss {
  if (width <= 0) return planar;

  const nodes: Record<string, RawNode> = {};
  const members: RawMember[] = [];

  // Duplicação da malha para as faces frontal (z=0) e traseira (z=width).
  for (const [id, node] of Object.entries(planar.nodes)) {
    addNode(nodes, id + "F", node.x, node.y, 0, node.support);
    addNode(nodes, id + "B", node.x, node.y, width, node.support);
  }

  // Réplica dos membros planares em ambas as camadas do espaço R3.
  for (const m of planar.members) {
    addMember(members, m.node_start + "F", m.node_end + "F", m.group);
    addMember(members, m.node_start + "B", m.node_end + "B", m.group);
  }

  // Estabilização global via X-Bracing e membros transversais.
  const nodeIds = Object.keys(planar.nodes);

  // Membros transversais (conectores de profundidade).
  for (const id of nodeIds) {
    addMember(members, id + "F", id + "B", "Transversal");
  }

  // Contraventamento cruzado para mitigar esforços de torção e flambagem global da estrutura.
  for (const m of planar.members) {
    const n1 = planar.nodes[m.node_start];
    const n2 = planar.nodes[m.node_end];
    if (Math.abs(n1.x - n2.x) > 0.01) {
      addMember(
        members,
        m.node_start + "F",
        m.node_end + "B",
        "Contraventamento",
      );
      addMember(
        members,
        m.node_start + "B",
        m.node_end + "F",
        "Contraventamento",
      );
    }
  }

  return { nodes, members };
}

// --- CONFIGURAÇÕES DE TELHADO (ROOFS) ---

export function generatePrattRoof(
  span: number,
  height: number,
  width: number,
  panels: number,
): RawTruss {
  // Treliça Pratt: montantes sob compressão e diagonais sob tração para cargas gravitacionais.
  span = Math.max(0.1, span);
  height = Math.max(0.1, height);
  width = Math.max(0, width);
  panels = Math.max(2, Math.floor(panels));

  const nodes: Record<string, RawNode> = {};
  const members: RawMember[] = [];
  const dx = span / panels;

  for (let i = 0; i <= panels; i++) {
    const x = i * dx;
    const bId = createNodeId("B", i);
    addNode(
      nodes,
      bId,
      x,
      0,
      0,
      i === 0 ? "Pinned" : i === panels ? "Roller" : "None",
    );

    const ty =
      i <= panels / 2
        ? (i * dx * height) / (span / 2)
        : ((panels - i) * dx * height) / (span / 2);
    if (i > 0 && i < panels) {
      addNode(nodes, createNodeId("T", i), x, ty, 0);
    }
  }

  for (let i = 0; i < panels; i++) {
    const bC = createNodeId("B", i);
    const bN = createNodeId("B", i + 1);
    const tC = i === 0 ? bC : createNodeId("T", i);
    const tN = i + 1 === panels ? bN : createNodeId("T", i + 1);

    addMember(members, bC, bN, "Banzo Inferior");
    addMember(members, tC, tN, "Banzo Superior");

    if (i > 0 && i < panels) addMember(members, bC, tC, "Montante");

    if (i < panels / 2) addMember(members, bC, tN, "Diagonal");
    else addMember(members, tC, bN, "Diagonal");
  }
  if (panels % 2 === 0)
    addMember(
      members,
      createNodeId("B", panels / 2),
      createNodeId("T", panels / 2),
      "Montante",
    );

  return extrude3D({ nodes, members }, width);
}

export function generateHoweRoof(
  span: number,
  height: number,
  width: number,
  panels: number,
): RawTruss {
  // Treliça Howe: diagonais comprimidas e montantes tracionados.
  // Eficiente para inclinações convencionais e superposição de cargas pontuais.
  span = Math.max(0.1, span);
  height = Math.max(0.1, height);
  width = Math.max(0, width);
  panels = Math.max(2, Math.floor(panels));

  const nodes: Record<string, RawNode> = {};
  const members: RawMember[] = [];
  const dx = span / panels;

  for (let i = 0; i <= panels; i++) {
    const x = i * dx;
    addNode(
      nodes,
      createNodeId("B", i),
      x,
      0,
      0,
      i === 0 ? "Pinned" : i === panels ? "Roller" : "None",
    );
    const ty =
      i <= panels / 2
        ? (i * dx * height) / (span / 2)
        : ((panels - i) * dx * height) / (span / 2);
    if (i > 0 && i < panels) addNode(nodes, createNodeId("T", i), x, ty, 0);
  }

  for (let i = 0; i < panels; i++) {
    const bC = createNodeId("B", i);
    const bN = createNodeId("B", i + 1);
    const tC = i === 0 ? bC : createNodeId("T", i);
    const tN = i + 1 === panels ? bN : createNodeId("T", i + 1);

    addMember(members, bC, bN, "Banzo Inferior");
    addMember(members, tC, tN, "Banzo Superior");
    if (i > 0 && i < panels) addMember(members, bC, tC, "Montante");
    if (i < panels / 2) addMember(members, tC, bN, "Diagonal");
    else addMember(members, bC, tN, "Diagonal");
  }
  if (panels % 2 === 0)
    addMember(
      members,
      createNodeId("B", panels / 2),
      createNodeId("T", panels / 2),
      "Montante",
    );

  return extrude3D({ nodes, members }, width);
}

export function generateFinkRoof(
  span: number,
  height: number,
  width: number,
): RawTruss {
  // Treliça Fink: ideal para vãos curtos e alta inclinação devido à subdivisão geométrica das diagonais.
  span = Math.max(0.1, span);
  height = Math.max(0.1, height);
  width = Math.max(0, width);

  const nodes: Record<string, RawNode> = {};
  const members: RawMember[] = [];
  const panels = 8;
  const dx = span / panels;

  for (let i = 0; i <= panels; i++) {
    const x = i * dx;
    addNode(
      nodes,
      createNodeId("B", i),
      x,
      0,
      0,
      i === 0 ? "Pinned" : i === panels ? "Roller" : "None",
    );
    const ty =
      i <= panels / 2
        ? (i * dx * height) / (span / 2)
        : ((panels - i) * dx * height) / (span / 2);
    if (i > 0 && i < panels) addNode(nodes, createNodeId("T", i), x, ty, 0);
  }

  for (let i = 0; i < panels; i++) {
    addMember(
      members,
      createNodeId("B", i),
      createNodeId("B", i + 1),
      "Banzo Inferior",
    );
    const tC = i === 0 ? createNodeId("B", 0) : createNodeId("T", i);
    const tN =
      i + 1 === panels ? createNodeId("B", panels) : createNodeId("T", i + 1);
    addMember(members, tC, tN, "Banzo Superior");
  }

  addMember(members, createNodeId("B", 4), createNodeId("T", 4), "Montante");
  addMember(members, createNodeId("B", 0), createNodeId("T", 2), "Diagonal");
  addMember(members, createNodeId("T", 2), createNodeId("B", 2), "Diagonal");
  addMember(members, createNodeId("B", 2), createNodeId("T", 4), "Diagonal");
  addMember(members, createNodeId("B", 2), createNodeId("T", 1), "Diagonal");
  addMember(members, createNodeId("B", 2), createNodeId("T", 3), "Diagonal");
  addMember(members, createNodeId("B", 8), createNodeId("T", 6), "Diagonal");
  addMember(members, createNodeId("T", 6), createNodeId("B", 6), "Diagonal");
  addMember(members, createNodeId("B", 6), createNodeId("T", 4), "Diagonal");
  addMember(members, createNodeId("B", 6), createNodeId("T", 5), "Diagonal");
  addMember(members, createNodeId("B", 6), createNodeId("T", 7), "Diagonal");

  return extrude3D({ nodes, members }, width);
}

// --- TIPOLOGIAS DE PONTE (BRIDGES) ---

export function generateWarrenBridge(
  span: number,
  height: number,
  width: number,
  panels: number,
): RawTruss {
  // Treliça Warren: redução de montantes verticais para otimização de peso próprio (Dead Load).
  span = Math.max(0.1, span);
  height = Math.max(0.1, height);
  width = Math.max(0, width);
  panels = Math.max(1, Math.floor(panels));

  const nodes: Record<string, RawNode> = {};
  const members: RawMember[] = [];
  const dx = span / panels;

  for (let i = 0; i <= panels; i++)
    addNode(
      nodes,
      createNodeId("B", i),
      i * dx,
      0,
      0,
      i === 0 ? "Pinned" : i === panels ? "Roller" : "None",
    );
  for (let i = 0; i < panels; i++)
    addNode(nodes, createNodeId("T", i), (i + 0.5) * dx, height, 0);

  for (let i = 0; i < panels; i++) {
    addMember(
      members,
      createNodeId("B", i),
      createNodeId("B", i + 1),
      "Banzo Inferior",
    );
    if (i < panels - 1)
      addMember(
        members,
        createNodeId("T", i),
        createNodeId("T", i + 1),
        "Banzo Superior",
      );
    addMember(members, createNodeId("B", i), createNodeId("T", i), "Diagonal");
    addMember(
      members,
      createNodeId("T", i),
      createNodeId("B", i + 1),
      "Diagonal",
    );
  }

  return extrude3D({ nodes, members }, width);
}

export function generatePrattBridge(
  span: number,
  height: number,
  width: number,
  panels: number,
): RawTruss {
  // Pratt Bridge: topologia com diagonais predominantemente tracionadas sob carga distribuída.
  span = Math.max(0.1, span);
  height = Math.max(0.1, height);
  width = Math.max(0, width);
  panels = Math.max(2, Math.floor(panels));

  const nodes: Record<string, RawNode> = {};
  const members: RawMember[] = [];
  const dx = span / panels;

  for (let i = 0; i <= panels; i++) {
    addNode(
      nodes,
      createNodeId("B", i),
      i * dx,
      0,
      0,
      i === 0 ? "Pinned" : i === panels ? "Roller" : "None",
    );
    addNode(nodes, createNodeId("T", i), i * dx, height, 0);
  }

  for (let i = 0; i < panels; i++) {
    addMember(
      members,
      createNodeId("B", i),
      createNodeId("B", i + 1),
      "Banzo Inferior",
    );
    addMember(
      members,
      createNodeId("T", i),
      createNodeId("T", i + 1),
      "Banzo Superior",
    );
    addMember(members, createNodeId("B", i), createNodeId("T", i), "Montante");
    if (i === panels - 1)
      addMember(
        members,
        createNodeId("B", i + 1),
        createNodeId("T", i + 1),
        "Montante",
      );
    if (i < panels / 2)
      addMember(
        members,
        createNodeId("B", i),
        createNodeId("T", i + 1),
        "Diagonal",
      );
    else
      addMember(
        members,
        createNodeId("T", i),
        createNodeId("B", i + 1),
        "Diagonal",
      );
  }

  return extrude3D({ nodes, members }, width);
}

// --- TIPOLOGIAS DE TORRE (TOWERS) ---

export function generateSquareTower(
  height: number,
  width: number,
  topWidth: number,
  sections: number,
): RawTruss {
  // Torre de seção quadrada: estabilidade contra esforços de torção e momentos fletores biaxiais.
  height = Math.max(0.1, height);
  width = Math.max(0, width);
  topWidth = Math.max(0.01, topWidth);
  sections = Math.max(1, Math.floor(sections));

  const nodes: Record<string, RawNode> = {};
  const members: RawMember[] = [];
  const dh = height / sections;

  for (let i = 0; i <= sections; i++) {
    const w = width - (i / sections) * (width - topWidth);
    const h = i * dh;
    const support: SupportType = i === 0 ? "Pinned" : "None";

    if (width === 0) {
      // Caso bidimensional da torre.
      addNode(nodes, createNodeId("N1", i), -w / 2, h, 0, support);
      addNode(nodes, createNodeId("N2", i), w / 2, h, 0, support);
      if (i > 0) {
        addMember(
          members,
          createNodeId("N1", i - 1),
          createNodeId("N1", i),
          "Principal",
        );
        addMember(
          members,
          createNodeId("N2", i - 1),
          createNodeId("N2", i),
          "Principal",
        );
        addMember(
          members,
          createNodeId("N1", i - 1),
          createNodeId("N2", i),
          "Diagonal",
        );
        addMember(
          members,
          createNodeId("N2", i - 1),
          createNodeId("N1", i),
          "Diagonal",
        );
      }
      addMember(
        members,
        createNodeId("N1", i),
        createNodeId("N2", i),
        "Transversal",
      );
    } else {
      // Geração espacial 3D com contraventamento em todas as faces.
      addNode(nodes, createNodeId("N1", i), -w / 2, h, -w / 2, support);
      addNode(nodes, createNodeId("N2", i), w / 2, h, -w / 2, support);
      addNode(nodes, createNodeId("N3", i), w / 2, h, w / 2, support);
      addNode(nodes, createNodeId("N4", i), -w / 2, h, w / 2, support);

      if (i > 0) {
        for (let j = 1; j <= 4; j++) {
          const nextJ = j === 4 ? 1 : j + 1;
          addMember(
            members,
            createNodeId("N" + j, i - 1),
            createNodeId("N" + j, i),
            "Montante",
          );
          addMember(
            members,
            createNodeId("N" + j, i - 1),
            createNodeId("N" + nextJ, i),
            "Diagonal",
          );
          addMember(
            members,
            createNodeId("N" + nextJ, i - 1),
            createNodeId("N" + j, i),
            "Diagonal",
          );
        }
      }
      addMember(
        members,
        createNodeId("N1", i),
        createNodeId("N2", i),
        "Transversal",
      );
      addMember(
        members,
        createNodeId("N2", i),
        createNodeId("N3", i),
        "Transversal",
      );
      addMember(
        members,
        createNodeId("N3", i),
        createNodeId("N4", i),
        "Transversal",
      );
      addMember(
        members,
        createNodeId("N4", i),
        createNodeId("N1", i),
        "Transversal",
      );
    }
  }
  return { nodes, members };
}

export function generateTriangularTower(
  height: number,
  width: number,
  topWidth: number,
  sections: number,
): RawTruss {
  // Torre triangular: configuração isostática estável com redução de membros transversais.
  height = Math.max(0.1, height);
  width = Math.max(0, width);
  topWidth = Math.max(0.01, topWidth);
  sections = Math.max(1, Math.floor(sections));

  const nodes: Record<string, RawNode> = {};
  const members: RawMember[] = [];
  const dh = height / sections;
  const cos30 = Math.cos(Math.PI / 6);
  const sin30 = Math.sin(Math.PI / 6);

  for (let i = 0; i <= sections; i++) {
    const w = width - (i / sections) * (width - topWidth);
    const h = i * dh;
    const r = w / Math.sqrt(3);
    const support: SupportType = i === 0 ? "Pinned" : "None";

    if (width === 0) {
      addNode(nodes, createNodeId("N1", i), 0, h, 0, support);
      addNode(nodes, createNodeId("N2", i), 1, h, 0, support);
      if (i > 0) {
        addMember(
          members,
          createNodeId("N1", i - 1),
          createNodeId("N1", i),
          "Montante",
        );
        addMember(
          members,
          createNodeId("N2", i - 1),
          createNodeId("N2", i),
          "Montante",
        );
        addMember(
          members,
          createNodeId("N1", i - 1),
          createNodeId("N2", i),
          "Diagonal",
        );
      }
      addMember(
        members,
        createNodeId("N1", i),
        createNodeId("N2", i),
        "Transversal",
      );
    } else {
      addNode(nodes, createNodeId("N1", i), 0, h, r, support);
      addNode(nodes, createNodeId("N2", i), r * cos30, h, -r * sin30, support);
      addNode(nodes, createNodeId("N3", i), -r * cos30, h, -r * sin30, support);

      if (i > 0) {
        for (let j = 1; j <= 3; j++) {
          const nextJ = j === 3 ? 1 : j + 1;
          addMember(
            members,
            createNodeId("N" + j, i - 1),
            createNodeId("N" + j, i),
            "Montante",
          );
          addMember(
            members,
            createNodeId("N" + j, i - 1),
            createNodeId("N" + nextJ, i),
            "Diagonal",
          );
          addMember(
            members,
            createNodeId("N" + nextJ, i - 1),
            createNodeId("N" + j, i),
            "Diagonal",
          );
        }
      }
      addMember(
        members,
        createNodeId("N1", i),
        createNodeId("N2", i),
        "Transversal",
      );
      addMember(
        members,
        createNodeId("N2", i),
        createNodeId("N3", i),
        "Transversal",
      );
      addMember(
        members,
        createNodeId("N3", i),
        createNodeId("N1", i),
        "Transversal",
      );
    }
  }
  return { nodes, members };
}

// --- BALANÇOS E MARQUISES (CANTILEVERS) ---

export function generateCantileverPratt(
  span: number,
  height: number,
  width: number,
  panels: number,
): RawTruss {
  // Cantilever Pratt: diagonais tracionadas para otimizar a transferência de carga ao apoio rígido.
  span = Math.max(0.1, span);
  height = Math.max(0.1, height);
  width = Math.max(0, width);
  panels = Math.max(1, Math.floor(panels));

  const nodes: Record<string, RawNode> = {};
  const members: RawMember[] = [];
  const dx = span / panels;

  for (let i = 0; i <= panels; i++) {
    const x = i * dx;
    addNode(nodes, createNodeId("B", i), x, 0, 0, i === 0 ? "Fixed" : "None");
    addNode(
      nodes,
      createNodeId("T", i),
      x,
      height,
      0,
      i === 0 ? "Fixed" : "None",
    );
  }

  for (let i = 0; i < panels; i++) {
    addMember(
      members,
      createNodeId("B", i),
      createNodeId("B", i + 1),
      "Banzo Inferior",
    );
    addMember(
      members,
      createNodeId("T", i),
      createNodeId("T", i + 1),
      "Banzo Superior",
    );
    addMember(
      members,
      createNodeId("B", i + 1),
      createNodeId("T", i + 1),
      "Montante",
    );
    addMember(
      members,
      createNodeId("B", i),
      createNodeId("T", i + 1),
      "Diagonal",
    );
  }
  addMember(members, createNodeId("B", 0), createNodeId("T", 0), "Montante");

  return extrude3D({ nodes, members }, width);
}

export function generateCantileverWarren(
  span: number,
  height: number,
  width: number,
  panels: number,
): RawTruss {
  // Cantilever Warren: redução de redundância nodal para estruturas leves em balanço.
  span = Math.max(0.1, span);
  height = Math.max(0.1, height);
  width = Math.max(0, width);
  panels = Math.max(1, Math.floor(panels));

  const nodes: Record<string, RawNode> = {};
  const members: RawMember[] = [];
  const dx = span / panels;

  for (let i = 0; i <= panels; i++)
    addNode(
      nodes,
      createNodeId("B", i),
      i * dx,
      0,
      0,
      i === 0 ? "Fixed" : "None",
    );
  for (let i = 0; i < panels; i++)
    addNode(nodes, createNodeId("T", i), (i + 0.5) * dx, height, 0);
  addNode(nodes, "T_base", 0, height, 0, "Fixed");

  for (let i = 0; i < panels; i++) {
    addMember(
      members,
      createNodeId("B", i),
      createNodeId("B", i + 1),
      "Banzo Inferior",
    );
    const tC = i === 0 ? "T_base" : createNodeId("T", i - 1);
    const tN = createNodeId("T", i);
    addMember(members, tC, tN, "Banzo Superior");
    addMember(members, createNodeId("B", i), tN, "Diagonal");
    addMember(members, tN, createNodeId("B", i + 1), "Diagonal");
  }

  return extrude3D({ nodes, members }, width);
}

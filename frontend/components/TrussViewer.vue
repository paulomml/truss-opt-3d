<script setup lang="ts">
import { getCylinderData, getMemberColor, formatarNumero } from '@/utils/truss3d';
import type { BarraResultado, BarraBruta, NoResultado, NoBruto } from '@/types/truss';
import { Vector3, Quaternion } from 'three';

const store = useTrussStore();
const cameraRef = ref();
const controlsRef = ref();

// Modo de visualização: 'tensao' (utilização) | 'deformada' (deslocamentos).
const modoVisualizacao = ref<'tensao' | 'deformada'>('tensao');

// Fator de escala para visualização da deformada (ampliação visual).
const fatorDeformada = ref(50);

// Computa dados das barras otimizadas.
const membersWithData = computed(() => {
  if (!store.result?.members?.length || !store.result?.nodes) return [];

  return store.result.members
    .map((m) => {
      const cylinderData = getCylinderData(m, store.result!.nodes);
      let valorHeatmap = m.utilization;

      // Modo deformada: usa deslocamentos nodais relativos.
      if (modoVisualizacao.value === 'deformada' && store.result?.nodes) {
        const noStart = store.result.nodes[m.node_start];
        const noEnd = store.result.nodes[m.node_end];
        if (noStart && noEnd) {
          const dy1 = noStart.deslocamento_y || 0;
          const dy2 = noEnd.deslocamento_y || 0;
          valorHeatmap = Math.abs((dy1 + dy2) / 2) * fatorDeformada.value;
        }
      }

      return {
        ...m,
        ...cylinderData,
        color: getMemberColor(Math.min(valorHeatmap, 1)),
        utilization: m.utilization,
      };
    })
    .filter((m) => m.length > 0);
});

// Computa dados da malha bruta (preview sem esforços).
const rawMembersWithData = computed(() => {
  if (!store.rawTruss?.members) return [];
  const nodes = store.rawTruss.nodes;

  return store.rawTruss.members
    .map((m) => {
      const cylinderData = getCylinderData(m as any, nodes as any);
      return {
        ...m,
        ...cylinderData,
        color: '#9CA3AF',
      };
    })
    .filter((m) => m.length > 0);
});

// Nós com deslocamento ampliado (para visualização da deformada).
const nodesDeformed = computed(() => {
  if (!store.result?.nodes || modoVisualizacao.value !== 'deformada') return null;
  const resultado: Record<string, NoResultado> = {};
  for (const [id, n] of Object.entries(store.result.nodes)) {
    resultado[id] = {
      ...n,
      x: n.x + (n.deslocamento_x || 0) * fatorDeformada.value,
      y: n.y + (n.deslocamento_y || 0) * fatorDeformada.value,
      z: n.z + (n.deslocamento_z || 0) * fatorDeformada.value,
    };
  }
  return resultado;
});

// Nós ativos (deformados ou originais).
const activeNodes = computed(() => {
  return nodesDeformed.value || store.result?.nodes || store.rawTruss?.nodes;
});

function onPointerClick(ev: any, member: BarraResultado | BarraBruta) {
  ev.stopPropagation();
  if ('utilization' in member) {
    store.selectMember(member as BarraResultado);
  }
}
</script>

<template>
  <div class="h-full w-full relative group">
    <!-- Controles de modo de visualização -->
    <div
      v-if="store.result"
      class="absolute top-4 left-4 z-10 bg-gray-800/90 backdrop-blur-sm rounded-lg shadow-lg p-2 flex gap-2"
    >
      <button
        @click="modoVisualizacao = 'tensao'"
        :class="[
          'px-3 py-1.5 rounded text-xs font-bold transition',
          modoVisualizacao === 'tensao'
            ? 'bg-blue-600 text-white'
            : 'bg-gray-700 text-gray-300 hover:bg-gray-600',
        ]"
        title="Heatmap por taxa de utilização (NBR 8800)"
      >
        Tensões
      </button>
      <button
        @click="modoVisualizacao = 'deformada'"
        :class="[
          'px-3 py-1.5 rounded text-xs font-bold transition',
          modoVisualizacao === 'deformada'
            ? 'bg-blue-600 text-white'
            : 'bg-gray-700 text-gray-300 hover:bg-gray-600',
        ]"
        title="Visualização da estrutura deformada (amplificada)"
      >
        Deformada ×{{ fatorDeformada }}
      </button>
    </div>

    <!-- Legenda de cores -->
    <div
      v-if="store.result"
      class="absolute bottom-4 left-4 z-10 bg-gray-800/90 backdrop-blur-sm rounded-lg shadow-lg p-3"
    >
      <div class="text-[10px] text-gray-300 font-bold mb-2 uppercase">
        {{ modoVisualizacao === 'tensao' ? 'Utilização' : 'Deslocamento' }}
      </div>
      <div
        class="w-40 h-3 rounded-full mb-1 bg-gradient-to-r from-blue-500 via-green-500 via-yellow-500 to-red-500"
      />
      <div class="flex justify-between text-[9px] text-gray-400">
        <span>0%</span>
        <span>50%</span>
        <span>80%</span>
        <span>100%</span>
      </div>
    </div>

    <!-- Indicador de barra selecionada -->
    <div
      v-if="store.selectedMember"
      class="absolute top-4 right-4 z-10 bg-gray-800/90 backdrop-blur-sm rounded-lg shadow-lg p-3 max-w-xs"
    >
      <div class="text-[10px] text-gray-400 font-bold uppercase">Barra Selecionada</div>
      <div class="text-white font-mono text-sm mt-1">
        #{{ store.selectedMember.id }} — {{ store.selectedMember.group }}
      </div>
      <div class="text-gray-300 text-xs mt-1">
        Perfil: <span class="font-mono">{{ store.selectedMember.profile }}</span>
      </div>
      <div class="text-gray-300 text-xs">
        Material: <span class="font-mono">{{ store.selectedMember.material }}</span>
      </div>
      <div class="text-gray-300 text-xs">
        Força axial:
        <span class="font-mono"
          >{{ formatarNumero(store.selectedMember.axial_force / 1000, 1) }} kN</span
        >
      </div>
      <div class="text-gray-300 text-xs">
        Utilização:
        <span class="font-mono"
          >{{ formatarNumero(store.selectedMember.utilization * 100, 1) }}%</span
        >
      </div>
    </div>

    <TresCanvas
      v-if="
        (store.result && store.result.members.length > 0) ||
        (store.rawTruss && store.rawTruss.members.length > 0)
      "
      alpha
      clear-color="#111827"
      shadows
      power-preference="high-performance"
    >
      <TresPerspectiveCamera ref="cameraRef" :position="[15, 10, 15]" :look-at="[6, 0, 0]" />
      <OrbitControls ref="controlsRef" />

      <TresAmbientLight :intensity="0.5" />
      <TresDirectionalLight :position="[10, 10, 5]" :intensity="1" cast-shadow />
      <TresGridHelper :args="[40, 40, '#374151', '#1f2937']" :position="[0, -0.01, 0]" />

      <!-- Nós (esferas) -->
      <template
        v-if="activeNodes"
        v-for="node in Object.values(activeNodes)"
        :key="`node-${node.id}`"
      >
        <TresMesh :position="[node.x, node.y, node.z]">
          <TresSphereGeometry :args="[0.08, 16, 16]" />
          <TresMeshStandardMaterial color="#ffffff" :metalness="0.8" :roughness="0.2" />
        </TresMesh>

        <!-- Apoios -->
        <template v-if="node.support !== 'None'">
          <TresMesh v-if="node.support === 'Pinned'" :position="[node.x, node.y - 0.2, node.z]">
            <TresConeGeometry :args="[0.15, 0.3, 4]" />
            <TresMeshStandardMaterial color="#EF4444" />
          </TresMesh>
          <TresGroup
            v-else-if="node.support === 'Roller'"
            :position="[node.x, node.y - 0.2, node.z]"
          >
            <TresMesh>
              <TresBoxGeometry :args="[0.6, 0.1, 0.6]" />
              <TresMeshStandardMaterial color="#F59E0B" />
            </TresMesh>
          </TresGroup>
          <TresMesh v-else-if="node.support === 'Fixed'" :position="[node.x, node.y, node.z]">
            <TresBoxGeometry :args="[0.6, 0.3, 0.6]" />
            <TresMeshStandardMaterial color="#6B7280" />
          </TresMesh>
        </template>
      </template>

      <!-- Barras otimizadas (com heatmap) -->
      <template v-for="member in membersWithData" :key="`opt-${member.id}`">
        <TresMesh
          :position="member.position"
          :quaternion="member.quaternion"
          @click="(ev) => onPointerClick(ev, member)"
        >
          <TresCylinderGeometry :args="[0.04, 0.04, member.length, 12]" />
          <TresMeshStandardMaterial
            :color="member.color"
            :emissive="member.color"
            :emissive-intensity="store.selectedMember?.id === member.id ? 1.5 : 0.4"
          />
        </TresMesh>
      </template>

      <!-- Malha bruta (preview) -->
      <template v-if="!store.result && store.rawTruss">
        <template v-for="member in rawMembersWithData" :key="`raw-${member.id}`">
          <TresMesh :position="member.position" :quaternion="member.quaternion">
            <TresCylinderGeometry :args="[0.03, 0.03, member.length, 8]" />
            <TresMeshStandardMaterial
              :color="member.color"
              :emissive="member.color"
              :emissive-intensity="0.2"
            />
          </TresMesh>
        </template>
      </template>
    </TresCanvas>

    <!-- Placeholder quando não há modelo -->
    <div
      v-else
      class="flex flex-col items-center justify-center h-full w-full bg-gray-900 text-white italic p-8 text-center"
    >
      <Icon name="lucide:building-2" class="w-16 h-16 mb-4 text-gray-500" />
      <p class="max-w-md text-gray-300">
        Selecione um <b>Tipo de Estrutura</b> no painel lateral, defina os parâmetros e clique em
        <b>Iniciar Análise Estrutural</b>.
      </p>
    </div>
  </div>
</template>

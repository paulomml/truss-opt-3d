<script setup lang="ts">
import { getCylinderData, getMemberColor } from "@/utils/truss3d";
import type { MemberResult, RawMember, RawNode } from "@/types/truss";
import { Vector3, Quaternion } from "three";

const store = useTrussStore();
const cameraRef = ref();
const controlsRef = ref();

const membersWithData = computed(() => {
  if (
    !store.result ||
    !store.result.members ||
    store.result.members.length === 0
  )
    return [];
  if (!store.result.nodes || Object.keys(store.result.nodes).length === 0)
    return [];

  try {
    return store.result.members
      .map((m) => {
        const cylinderData = getCylinderData(m, store.result!.nodes);
        return {
          ...m,
          ...cylinderData,
          color: getMemberColor(m.utilization),
        };
      })
      .filter((m) => m.length > 0);
  } catch (e) {
    console.error("Erro no processamento dos elementos finitos:", e);
    return [];
  }
});

const rawMembersWithData = computed(() => {
  if (!store.rawTruss || !store.rawTruss.members) return [];
  const nodes = store.rawTruss.nodes;

  return store.rawTruss.members
    .map((m) => {
      // Reutilização da lógica de transformação geométrica para a malha paramétrica.
      const cylinderData = getCylinderData(m as any, nodes as any);
      return {
        ...m,
        ...cylinderData,
        color: "#9CA3AF", // Tonalidade neutra para representação da geometria sem esforços.
      };
    })
    .filter((m) => m.length > 0);
});

function onPointerClick(ev: any, member: MemberResult | RawMember) {
  ev.stopPropagation();
  if ("utilization" in member) {
    store.selectMember(member as MemberResult);
  }
}

const getSupportRotation = (node: RawNode) => {
  return [0, 0, 0];
};
</script>

<template>
  <div class="h-full w-full relative group">
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
      <TresPerspectiveCamera
        ref="cameraRef"
        :position="[15, 10, 15]"
        :look-at="[6, 0, 0]"
      />
      <OrbitControls ref="controlsRef" />

      <TresAmbientLight :intensity="0.5" />
      <TresDirectionalLight
        :position="[10, 10, 5]"
        :intensity="1"
        cast-shadow
      />
      <!-- Grade de referência espacial para orientação no modelo R³. -->
      <TresGridHelper
        :args="[40, 40, '#374151', '#1f2937']"
        :position="[0, -0.01, 0]"
      />

      <!-- Representação dos nós do modelo discreto (esferas). -->
      <template
        v-if="store.result?.nodes"
        v-for="node in Object.values(store.result.nodes)"
        :key="`result-${node.id}-${node.x}-${node.y}-${node.z}`"
      >
        <TresMesh :position="[node.x, node.y, node.z]">
          <TresSphereGeometry :args="[0.08, 16, 16]" />
          <TresMeshStandardMaterial
            color="#ffffff"
            :metalness="0.8"
            :roughness="0.2"
          />
        </TresMesh>

        <!-- Simbolização das restrições de movimento (Apoios). -->
        <template v-if="node.support !== 'None'">
          <!-- Apoio de 2º Gênero (Pinned): Cone representativo de restrição de translação. -->
          <TresMesh
            v-if="node.support === 'Pinned'"
            :position="[node.x, node.y - 0.2, node.z]"
          >
            <TresConeGeometry :args="[0.15, 0.3, 4]" />
            <TresMeshStandardMaterial color="#EF4444" />
          </TresMesh>

          <!-- Apoio de 1º Gênero (Roller): Base móvel representando a interação solo-estrutura. -->
          <TresGroup
            v-else-if="node.support === 'Roller'"
            :position="[node.x, node.y - 0.2, node.z]"
          >
            <TresMesh>
              <TresBoxGeometry
                :args="[store.form.footing_b, 0.1, store.form.footing_l]"
              />
              <TresMeshStandardMaterial color="#F59E0B" />
            </TresMesh>
            <TresMesh :position="[0, -0.1, 0]">
              <TresCylinderGeometry
                :args="[0.03, 0.03, 0.2, 8]"
                :rotation="[0, 0, Math.PI / 2]"
              />
              <TresMeshStandardMaterial color="#F59E0B" />
            </TresMesh>
          </TresGroup>

          <!-- Engastamento (Fixed): Bloco rígido simulando restrição total de graus de liberdade. -->
          <TresMesh
            v-else-if="node.support === 'Fixed'"
            :position="[node.x, node.y, node.z]"
          >
            <TresBoxGeometry
              :args="[store.form.footing_b, 0.3, store.form.footing_l]"
            />
            <TresMeshStandardMaterial color="#6B7280" />
          </TresMesh>
        </template>
      </template>

      <!-- Renderização dos elementos de barra do modelo otimizado. -->
      <template v-for="member in membersWithData" :key="member.id">
        <TresMesh
          :position="member.position"
          :quaternion="member.quaternion"
          @click="(ev) => onPointerClick(ev, member)"
        >
          <TresCylinderGeometry :args="[0.04, 0.04, member.length, 8]" />
          <TresMeshStandardMaterial
            :color="member.color"
            :emissive="member.color"
            :emissive-intensity="
              store.selectedMember?.id === member.id ? 1.5 : 0.2
            "
          />
        </TresMesh>
      </template>

      <!-- Visualização da malha paramétrica bruta para pré-análise. -->
      <template v-if="!store.result && store.rawTruss">
        <!-- Nós da malha inicial. -->
        <template
          v-for="node in Object.values(store.rawTruss.nodes)"
          :key="`raw-${node.id}-${node.x}-${node.y}-${node.z}`"
        >
          <TresMesh :position="[node.x, node.y, node.z]">
            <TresSphereGeometry :args="[0.06, 12, 12]" />
            <TresMeshStandardMaterial color="#D1D5DB" />
          </TresMesh>

          <template v-if="node.support !== 'None'">
            <TresMesh
              v-if="node.support === 'Pinned'"
              :position="[node.x, node.y - 0.2, node.z]"
            >
              <TresConeGeometry :args="[0.15, 0.3, 4]" />
              <TresMeshStandardMaterial color="#EF4444" />
            </TresMesh>

            <TresGroup
              v-else-if="node.support === 'Roller'"
              :position="[node.x, node.y - 0.2, node.z]"
            >
              <TresMesh>
                <TresBoxGeometry
                  :args="[store.form.footing_b, 0.1, store.form.footing_l]"
                />
                <TresMeshStandardMaterial color="#F59E0B" />
              </TresMesh>
              <TresMesh :position="[0, -0.1, 0]">
                <TresCylinderGeometry
                  :args="[0.03, 0.03, 0.2, 8]"
                  :rotation="[0, 0, Math.PI / 2]"
                />
                <TresMeshStandardMaterial color="#F59E0B" />
              </TresMesh>
            </TresGroup>

            <TresMesh
              v-else-if="node.support === 'Fixed'"
              :position="[node.x, node.y, node.z]"
            >
              <TresBoxGeometry
                :args="[store.form.footing_b, 0.3, store.form.footing_l]"
              />
              <TresMeshStandardMaterial color="#6B7280" />
            </TresMesh>
          </template>
        </template>

        <!-- Barras da malha inicial. -->
        <template v-for="member in rawMembersWithData" :key="member.id">
          <TresMesh
            :position="member.position"
            :quaternion="member.quaternion"
            @click="(ev) => onPointerClick(ev, member)"
          >
            <TresCylinderGeometry :args="[0.03, 0.03, member.length, 6]" />
            <TresMeshStandardMaterial
              :color="member.color"
              :emissive="member.color"
              :emissive-intensity="
                store.selectedMember?.id === member.id ? 1.5 : 0.2
              "
            />
          </TresMesh>
        </template>
      </template>
    </TresCanvas>
    <!-- Interface de orientação inicial: exibida quando nenhum modelo estrutural foi processado. -->
    <div
      v-else
      class="flex flex-col items-center justify-center h-full w-full bg-gray-900 text-white italic p-8 text-center"
      title="Área de visualização tridimensional da estrutura."
    >
      <Icon name="lucide:building-2" class="w-16 h-16 mb-4 text-gray-500" />
      <p class="max-w-md text-gray-300">
        Selecione um <b>Tipo de Estrutura</b> no painel lateral, defina os
        parâmetros desejados e clique em <b>Iniciar Análise Estrutural</b> para
        visualizar o modelo.
      </p>
    </div>
  </div>
</template>

<style scoped>
.fade-fast-enter-active,
.fade-fast-leave-active {
  transition:
    opacity 0.2s ease,
    transform 0.2s ease;
}
.fade-fast-enter-from,
.fade-fast-leave-to {
  opacity: 0;
  transform: translateX(-10px);
}
</style>

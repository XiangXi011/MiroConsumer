<template>
  <section v-if="visible" class="evidence-graph-panel">
    <div class="eg-header">
      <div>
        <p class="eg-kicker">Evidence Graph</p>
        <h2 class="eg-title">Finding -> Evidence -> Source</h2>
      </div>
      <div class="eg-stats">
        <span class="eg-stat mono">{{ nodeCount }} nodes</span>
        <span class="eg-stat mono">{{ edgeCount }} edges</span>
      </div>
    </div>

    <div v-if="loading" class="eg-state">Loading evidence graph...</div>
    <div v-else-if="error" class="eg-state eg-state--error">{{ error }}</div>
    <div v-else-if="!hasGraph" class="eg-state">No citation graph available.</div>
    <div v-else class="eg-body">
      <svg class="eg-canvas" viewBox="0 0 720 260" role="img" aria-label="Evidence graph">
        <g class="eg-edges">
          <path
            v-for="edge in positionedEdges"
            :key="edge.id"
            :d="edge.path"
            class="eg-edge"
            :class="'eg-edge--' + edge.type"
          />
        </g>
        <g class="eg-nodes">
          <g
            v-for="node in positionedNodes"
            :key="node.id"
            class="eg-node"
            :class="['eg-node--' + node.type, { 'eg-node--low': node.low_confidence }]"
            :transform="`translate(${node.x}, ${node.y})`"
          >
            <rect x="-86" y="-26" width="172" height="52" rx="6" />
            <text class="eg-node-type" text-anchor="middle" y="-7">{{ node.type }}</text>
            <text class="eg-node-label" text-anchor="middle" y="12">{{ node.shortLabel }}</text>
          </g>
        </g>
      </svg>

      <div class="eg-lanes">
        <div v-for="lane in lanes" :key="lane.type" class="eg-lane" :class="'eg-lane--' + lane.type">
          <span class="eg-lane-label">{{ lane.label }}</span>
          <span class="eg-lane-count mono">{{ lane.count }}</span>
        </div>
      </div>

      <div v-if="warnings.length > 0" class="eg-warnings">
        <span v-for="warning in warnings" :key="warning" class="eg-warning mono">{{ warning }}</span>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
// @ts-nocheck
import { computed } from 'vue'

const props = defineProps({
  graph: { type: Object, default: null },
  loading: Boolean,
  error: { type: String, default: '' },
})

const nodes = computed(() => Array.isArray(props.graph?.nodes) ? props.graph.nodes : [])
const edges = computed(() => Array.isArray(props.graph?.edges) ? props.graph.edges : [])
const warnings = computed(() => Array.isArray(props.graph?.warnings) ? props.graph.warnings : [])
const nodeCount = computed(() => props.graph?.node_count ?? nodes.value.length)
const edgeCount = computed(() => props.graph?.edge_count ?? edges.value.length)
const hasGraph = computed(() => nodes.value.length > 0 && edges.value.length > 0)
const visible = computed(() => Boolean(props.loading || props.error || props.graph))

const lanes = computed(() => {
  const counts = { finding: 0, evidence: 0, source: 0 }
  nodes.value.forEach((node) => {
    if (counts[node.type] !== undefined) counts[node.type] += 1
  })
  return [
    { type: 'finding', label: 'Findings', count: counts.finding },
    { type: 'evidence', label: 'Evidence', count: counts.evidence },
    { type: 'source', label: 'Sources', count: counts.source },
  ]
})

const positionedNodes = computed(() => {
  const laneX = { finding: 120, evidence: 360, source: 600 }
  const laneIndexes = { finding: 0, evidence: 0, source: 0 }
  const laneTotals = lanes.value.reduce((acc, lane) => {
    acc[lane.type] = Math.max(lane.count, 1)
    return acc
  }, {})

  return nodes.value.map((node) => {
    const type = ['finding', 'evidence', 'source'].includes(node.type) ? node.type : 'evidence'
    const index = laneIndexes[type]++
    const total = laneTotals[type]
    const spacing = Math.min(62, 180 / Math.max(total - 1, 1))
    const startY = 130 - ((total - 1) * spacing) / 2
    return {
      ...node,
      type,
      x: laneX[type],
      y: startY + index * spacing,
      shortLabel: shorten(node.label || node.resource_id || node.id),
    }
  })
})

const positionedEdges = computed(() => {
  const byId = new Map(positionedNodes.value.map(node => [node.id, node]))
  return edges.value
    .map((edge) => {
      const source = byId.get(edge.source)
      const target = byId.get(edge.target)
      if (!source || !target) return null
      const midX = (source.x + target.x) / 2
      return {
        ...edge,
        id: edge.id || `${edge.source}-${edge.target}`,
        type: edge.type || 'supported_by',
        path: `M ${source.x + 86} ${source.y} C ${midX} ${source.y}, ${midX} ${target.y}, ${target.x - 86} ${target.y}`,
      }
    })
    .filter(Boolean)
})

function shorten(value) {
  const text = String(value || '').trim()
  if (text.length <= 24) return text
  return `${text.slice(0, 21)}...`
}
</script>

<style scoped>
.evidence-graph-panel {
  margin: 18px 0 22px;
  border: 1px solid #D1D5DB;
  background: #FBFAF7;
  border-radius: 8px;
  overflow: hidden;
}

.eg-header {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  align-items: flex-start;
  padding: 16px 18px;
  border-bottom: 1px solid #E5E7EB;
  background: #FFFFFF;
}

.eg-kicker {
  margin: 0 0 4px;
  color: #6B7280;
  font-size: 11px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.eg-title {
  margin: 0;
  color: #111827;
  font-size: 17px;
  line-height: 1.25;
}

.eg-stats {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  justify-content: flex-end;
}

.eg-stat {
  border: 1px solid #E5E7EB;
  color: #374151;
  background: #F9FAFB;
  border-radius: 999px;
  padding: 4px 8px;
  font-size: 11px;
}

.eg-body {
  padding: 14px 16px 16px;
}

.eg-canvas {
  width: 100%;
  min-height: 230px;
  background: linear-gradient(180deg, var(--mc-surface) 0%, var(--mc-bg-subtle) 100%);
  border: 1px solid var(--mc-border);
  border-radius: 6px;
}

.eg-edge {
  fill: none;
  stroke: var(--mc-border-strong);
  stroke-width: 2;
}

.eg-edge--supported_by {
  stroke: var(--mc-status-info);
}

.eg-edge--sourced_from {
  stroke: #059669;
}

.eg-node rect {
  fill: var(--mc-surface);
  stroke: var(--mc-border-strong);
  stroke-width: 1.5;
}

.eg-node--finding rect {
  stroke: var(--mc-status-info);
}

.eg-node--evidence rect {
  stroke: var(--mc-accent);
}

.eg-node--source rect {
  stroke: #059669;
}

.eg-node--low rect {
  fill: #FFF7ED;
  stroke: #EA580C;
  stroke-dasharray: 4 3;
}

.eg-node-type {
  fill: #6B7280;
  font-size: 9px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.eg-node-label {
  fill: #111827;
  font-size: 11px;
  font-weight: 700;
}

.eg-lanes {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
  margin-top: 12px;
}

.eg-lane {
  display: flex;
  justify-content: space-between;
  align-items: center;
  border: 1px solid #E5E7EB;
  background: #FFFFFF;
  border-radius: 6px;
  padding: 9px 10px;
}

.eg-lane-label {
  color: #374151;
  font-size: 12px;
  font-weight: 700;
}

.eg-lane-count {
  color: #111827;
  font-size: 12px;
}

.eg-warnings {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 12px;
}

.eg-warning {
  color: #9A3412;
  background: #FFEDD5;
  border: 1px solid #FED7AA;
  border-radius: 999px;
  padding: 3px 7px;
  font-size: 10px;
}

.eg-state {
  padding: 14px 18px;
  color: #6B7280;
  font-size: 13px;
}

.eg-state--error {
  color: #B91C1C;
}

.mono {
  font-family: 'JetBrains Mono', monospace;
}

@media (max-width: 720px) {
  .eg-header {
    flex-direction: column;
  }

  .eg-lanes {
    grid-template-columns: 1fr;
  }
}
</style>

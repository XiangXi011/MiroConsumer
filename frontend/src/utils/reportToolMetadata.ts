// @ts-nocheck
export const toolConfig = {
  insight_forge: {
    name: 'Deep Insight',
    color: 'purple',
    icon: 'lightbulb',
  },
  panorama_search: {
    name: 'Panorama Search',
    color: 'blue',
    icon: 'globe',
  },
  interview_agents: {
    name: 'Agent Interview',
    color: 'green',
    icon: 'users',
  },
  quick_search: {
    name: 'Quick Search',
    color: 'orange',
    icon: 'zap',
  },
  get_graph_statistics: {
    name: 'Graph Stats',
    color: 'cyan',
    icon: 'chart',
  },
  get_entities_by_type: {
    name: 'Entity Query',
    color: 'pink',
    icon: 'database',
  },
}

export function resolveToolMetadata(toolName) {
  const config = toolConfig[toolName]
  return {
    name: config?.name || toolName,
    color: config?.color || 'gray',
    icon: config?.icon || 'tool',
  }
}

export function getToolDisplayName(toolName) {
  return resolveToolMetadata(toolName).name
}

export function getToolColor(toolName) {
  return resolveToolMetadata(toolName).color
}

export function getToolIcon(toolName) {
  return resolveToolMetadata(toolName).icon
}

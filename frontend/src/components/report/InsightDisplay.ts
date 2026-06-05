// @ts-nocheck
import { h, ref } from 'vue'
import { useI18n } from 'vue-i18n'

// Insight Display Component - Enhanced with full data rendering (Interview-like style)
export const InsightDisplay = {
  props: ['result', 'resultLength'],
  setup(props) {
    const { t } = useI18n()
    const activeTab = ref('facts') // 'facts', 'entities', 'relations', 'subqueries'
    const expandedFacts = ref(false)
    const expandedEntities = ref(false)
    const expandedRelations = ref(false)
    const INITIAL_SHOW_COUNT = 5

    // Format result size for display
    const formatSize = (length) => {
      if (!length) return ''
      if (length >= 1000) {
        return `${(length / 1000).toFixed(1)}k chars`
      }
      return `${length} chars`
    }

    return () => h('div', { class: 'insight-display' }, [
      // Header Section - like interview header
      h('div', { class: 'insight-header' }, [
        h('div', { class: 'header-main' }, [
          h('div', { class: 'header-title' }, 'Deep Insight'),
          h('div', { class: 'header-stats' }, [
            h('span', { class: 'stat-item' }, [
              h('span', { class: 'stat-value' }, props.result.stats.facts || props.result.facts.length),
              h('span', { class: 'stat-label' }, 'Facts')
            ]),
            h('span', { class: 'stat-divider' }, '/'),
            h('span', { class: 'stat-item' }, [
              h('span', { class: 'stat-value' }, props.result.stats.entities || props.result.entities.length),
              h('span', { class: 'stat-label' }, 'Entities')
            ]),
            h('span', { class: 'stat-divider' }, '/'),
            h('span', { class: 'stat-item' }, [
              h('span', { class: 'stat-value' }, props.result.stats.relationships || props.result.relations.length),
              h('span', { class: 'stat-label' }, 'Relations')
            ]),
            props.resultLength && h('span', { class: 'stat-divider' }, '·'),
            props.resultLength && h('span', { class: 'stat-size' }, formatSize(props.resultLength))
          ])
        ]),
        props.result.query && h('div', { class: 'header-topic' }, props.result.query),
        props.result.simulationRequirement && h('div', { class: 'header-scenario' }, [
          h('span', { class: 'scenario-label' }, t('step4.scenarioLabel')),
          h('span', { class: 'scenario-text' }, props.result.simulationRequirement)
        ])
      ]),

      // Tab Navigation
      h('div', { class: 'insight-tabs' }, [
        h('button', {
          class: ['insight-tab', { active: activeTab.value === 'facts' }],
          onClick: () => { activeTab.value = 'facts' }
        }, [
          h('span', { class: 'tab-label' }, t('step4.tabKeyFacts', { count: props.result.facts.length }))
        ]),
        h('button', {
          class: ['insight-tab', { active: activeTab.value === 'entities' }],
          onClick: () => { activeTab.value = 'entities' }
        }, [
          h('span', { class: 'tab-label' }, t('step4.tabCoreEntities', { count: props.result.entities.length }))
        ]),
        h('button', {
          class: ['insight-tab', { active: activeTab.value === 'relations' }],
          onClick: () => { activeTab.value = 'relations' }
        }, [
          h('span', { class: 'tab-label' }, t('step4.tabRelationChains', { count: props.result.relations.length }))
        ]),
        props.result.subQueries.length > 0 && h('button', {
          class: ['insight-tab', { active: activeTab.value === 'subqueries' }],
          onClick: () => { activeTab.value = 'subqueries' }
        }, [
          h('span', { class: 'tab-label' }, t('step4.tabSubQueries', { count: props.result.subQueries.length }))
        ])
      ]),

      // Tab Content
      h('div', { class: 'insight-content' }, [
        // Facts Tab
        activeTab.value === 'facts' && props.result.facts.length > 0 && h('div', { class: 'facts-panel' }, [
          h('div', { class: 'panel-header' }, [
            h('span', { class: 'panel-title' }, t('step4.panelKeyFacts')),
            h('span', { class: 'panel-count' }, t('step4.totalCount', { count: props.result.facts.length }))
          ]),
          h('div', { class: 'facts-list' },
            (expandedFacts.value ? props.result.facts : props.result.facts.slice(0, INITIAL_SHOW_COUNT)).map((fact, i) =>
              h('div', { class: 'fact-item', key: i }, [
                h('span', { class: 'fact-number' }, i + 1),
                h('div', { class: 'fact-content' }, fact)
              ])
            )
          ),
          props.result.facts.length > INITIAL_SHOW_COUNT && h('button', {
            class: 'expand-btn',
            onClick: () => { expandedFacts.value = !expandedFacts.value }
          }, expandedFacts.value ? t('step4.collapse') : t('step4.expandAll', { count: props.result.facts.length }))
        ]),

        // Entities Tab
        activeTab.value === 'entities' && props.result.entities.length > 0 && h('div', { class: 'entities-panel' }, [
          h('div', { class: 'panel-header' }, [
            h('span', { class: 'panel-title' }, t('step4.panelCoreEntities')),
            h('span', { class: 'panel-count' }, t('step4.totalEntityCount', { count: props.result.entities.length }))
          ]),
          h('div', { class: 'entities-grid' },
            (expandedEntities.value ? props.result.entities : props.result.entities.slice(0, 12)).map((entity, i) =>
              h('div', { class: 'entity-tag', key: i, title: entity.summary || '' }, [
                h('span', { class: 'entity-name' }, entity.name),
                h('span', { class: 'entity-type' }, entity.type),
                entity.relatedFactsCount > 0 && h('span', { class: 'entity-fact-count' }, t('step4.factCount', { count: entity.relatedFactsCount }))
              ])
            )
          ),
          props.result.entities.length > 12 && h('button', {
            class: 'expand-btn',
            onClick: () => { expandedEntities.value = !expandedEntities.value }
          }, expandedEntities.value ? t('step4.collapse') : t('step4.expandAllEntities', { count: props.result.entities.length }))
        ]),

        // Relations Tab
        activeTab.value === 'relations' && props.result.relations.length > 0 && h('div', { class: 'relations-panel' }, [
          h('div', { class: 'panel-header' }, [
            h('span', { class: 'panel-title' }, t('step4.panelRelationChains')),
            h('span', { class: 'panel-count' }, t('step4.totalCount', { count: props.result.relations.length }))
          ]),
          h('div', { class: 'relations-list' },
            (expandedRelations.value ? props.result.relations : props.result.relations.slice(0, INITIAL_SHOW_COUNT)).map((rel, i) =>
              h('div', { class: 'relation-item', key: i }, [
                h('span', { class: 'rel-source' }, rel.source),
                h('span', { class: 'rel-arrow' }, [
                  h('span', { class: 'rel-line' }),
                  h('span', { class: 'rel-label' }, rel.relation),
                  h('span', { class: 'rel-line' })
                ]),
                h('span', { class: 'rel-target' }, rel.target)
              ])
            )
          ),
          props.result.relations.length > INITIAL_SHOW_COUNT && h('button', {
            class: 'expand-btn',
            onClick: () => { expandedRelations.value = !expandedRelations.value }
          }, expandedRelations.value ? t('step4.collapse') : t('step4.expandAll', { count: props.result.relations.length }))
        ]),

        // Sub-queries Tab
        activeTab.value === 'subqueries' && props.result.subQueries.length > 0 && h('div', { class: 'subqueries-panel' }, [
          h('div', { class: 'panel-header' }, [
            h('span', { class: 'panel-title' }, t('step4.panelSubQueries')),
            h('span', { class: 'panel-count' }, t('step4.totalEntityCount', { count: props.result.subQueries.length }))
          ]),
          h('div', { class: 'subqueries-list' },
            props.result.subQueries.map((sq, i) =>
              h('div', { class: 'subquery-item', key: i }, [
                h('span', { class: 'subquery-number' }, `Q${i + 1}`),
                h('div', { class: 'subquery-text' }, sq)
              ])
            )
          )
        ]),

        // Empty state
        activeTab.value === 'facts' && props.result.facts.length === 0 && h('div', { class: 'empty-state' }, t('step4.emptyKeyFacts')),
        activeTab.value === 'entities' && props.result.entities.length === 0 && h('div', { class: 'empty-state' }, t('step4.emptyCoreEntities')),
        activeTab.value === 'relations' && props.result.relations.length === 0 && h('div', { class: 'empty-state' }, t('step4.emptyRelationChains'))
      ])
    ])
  }
}

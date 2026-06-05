// @ts-nocheck
const COMPLETED_STATUSES = new Set(['completed', 'complete', 'success', 'ready'])

function normalizeText(value) {
  return typeof value === 'string' ? value.trim() : ''
}

function normalizeStatus(reportData = {}) {
  return normalizeText(
    reportData.status
      || reportData.state
      || reportData.generation_task?.status
      || reportData.report_context?.generation_task?.status
      || reportData.report_context?.generation_task?.stage
  ).toLowerCase()
}

function pickMarkdown(reportData = {}) {
  return normalizeText(
    reportData.markdown_content
      || reportData.report_content
      || reportData.content
      || reportData.final_report
  )
}

function pickFallbackTitle(reportData = {}) {
  return normalizeText(
    reportData.report_context?.test_type_profile?.report_strategy?.report_title
      || reportData.report_context?.report_strategy?.report_title
      || reportData.title
      || reportData.report_title
      || reportData.report_id
      || 'Insight Report'
  )
}

function extractSummary(lines, firstSectionIndex) {
  const startIndex = lines.findIndex(line => /^#\s+/.test(line))
  const from = startIndex >= 0 ? startIndex + 1 : 0
  const to = firstSectionIndex >= 0 ? firstSectionIndex : lines.length
  return lines
    .slice(from, to)
    .map(line => line.trim())
    .filter(line => line && !/^#{1,6}\s+/.test(line))
    .slice(0, 3)
    .join('\n')
}

function parseMarkdownReport(markdown, reportData = {}) {
  const source = normalizeText(markdown).replace(/\r\n/g, '\n')
  const lines = source.split('\n')
  const h1 = lines.find(line => /^#\s+/.test(line))
  const title = h1 ? h1.replace(/^#\s+/, '').trim() : pickFallbackTitle(reportData)
  const sectionStarts = []

  lines.forEach((line, index) => {
    const match = line.match(/^##\s+(.+)$/)
    if (match) {
      sectionStarts.push({
        index,
        title: match[1].trim(),
      })
    }
  })

  if (sectionStarts.length === 0) {
    return {
      title,
      summary: extractSummary(lines, -1),
      sections: [{ title }],
      generatedSections: { 1: source },
    }
  }

  const generatedSections = {}
  const sections = sectionStarts.map((section, idx) => {
    const next = sectionStarts[idx + 1]?.index ?? lines.length
    generatedSections[idx + 1] = lines.slice(section.index, next).join('\n').trim()
    return { title: section.title }
  })

  return {
    title,
    summary: extractSummary(lines, sectionStarts[0].index),
    sections,
    generatedSections,
  }
}

export function deriveReportRenderState(reportData = {}) {
  const status = normalizeStatus(reportData)
  const markdown = pickMarkdown(reportData)

  if (!COMPLETED_STATUSES.has(status) || !markdown) {
    return {
      isComplete: false,
      outline: null,
      generatedSections: {},
    }
  }

  const parsed = parseMarkdownReport(markdown, reportData)
  return {
    isComplete: true,
    outline: {
      title: parsed.title,
      summary: parsed.summary,
      sections: parsed.sections,
    },
    generatedSections: parsed.generatedSections,
  }
}

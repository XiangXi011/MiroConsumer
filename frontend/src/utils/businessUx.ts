// @ts-nocheck
const ITEM_SPLIT_PATTERN = /[\n,，;；]+/

const BUSINESS_FLOW_STEPS = [
  {
    key: 'brief',
    title: '准备测试素材',
    description: '整理测试目标、素材和目标人群',
  },
  {
    key: 'audience',
    title: '生成消费者画像',
    description: '根据 brief 准备受众与测试场景',
  },
  {
    key: 'run',
    title: '运行传播测试',
    description: '观察消费者反应、扩散和误读风险',
  },
  {
    key: 'report',
    title: '生成洞察报告',
    description: '沉淀结论、机会、风险和证据可信度',
  },
  {
    key: 'followup',
    title: '追问与验证',
    description: '继续追问结论、验证证据或比较方案',
  },
]

const STATUS_COPY = {
  brief: {
    idle: ['等待填写', '补齐测试素材、目标人群和研究目标后即可开始。'],
    processing: ['正在准备测试素材', '系统正在整理 brief 和背景资料。'],
    completed: ['测试素材已准备好', '可以进入消费者画像和测试场景准备。'],
    error: ['素材准备遇到问题', '请检查 brief 或补充必要信息后重试。'],
  },
  audience: {
    idle: ['等待生成画像', '系统会根据 brief 生成消费者画像与测试场景。'],
    processing: ['正在生成消费者画像', '请稍等，系统正在准备受众、场景和初始讨论线索。'],
    completed: ['消费者画像已准备好', '可以进入传播测试。'],
    error: ['画像生成遇到问题', '可重试或打开技术详情查看原因。'],
  },
  run: {
    idle: ['等待运行', '测试环境已准备好，可以开始传播测试。'],
    processing: ['正在运行传播测试', '系统正在模拟消费者初见反应、讨论扩散和风险放大。'],
    completed: ['传播测试已完成', '可以生成洞察报告。'],
    error: ['传播测试遇到问题', '请稍后重试或查看技术详情。'],
  },
  report: {
    idle: ['等待生成报告', '测试完成后会整理业务结论与证据。'],
    processing: ['正在生成洞察报告', '系统正在提炼机会点、风险点、人群差异和证据。'],
    completed: ['洞察报告已完成', '可以阅读结论，也可以继续追问。'],
    error: ['报告生成遇到问题', '可重试生成或查看技术详情。'],
  },
  followup: {
    idle: ['可以继续追问', '选择一个业务动作，继续验证结论或追问消费者。'],
    processing: ['正在处理追问', '系统正在根据报告和消费者反馈生成回答。'],
    completed: ['追问已完成', '可以继续追加问题或比较方案。'],
    error: ['追问遇到问题', '请调整问题后重试。'],
  },
}

function normalizeText(value) {
  return typeof value === 'string' ? value.trim() : ''
}

function splitLines(value) {
  return normalizeText(value)
    .split('\n')
    .map(item => item.trim())
    .filter(Boolean)
}

function splitItems(value) {
  return normalizeText(value)
    .split(ITEM_SPLIT_PATTERN)
    .map(item => item.trim())
    .filter(Boolean)
}

function normalizeStatus(status) {
  if (status === 'completed' || status === 'ready' || status === 'success') return 'completed'
  if (status === 'error' || status === 'failed') return 'error'
  if (status === 'processing' || status === 'running' || status === 'generating') return 'processing'
  return 'idle'
}

export function getBusinessFlowSteps() {
  return BUSINESS_FLOW_STEPS.map(step => ({ ...step }))
}

export function getBusinessStep(indexOrKey) {
  if (typeof indexOrKey === 'string') {
    return BUSINESS_FLOW_STEPS.find(step => step.key === indexOrKey) || BUSINESS_FLOW_STEPS[0]
  }
  const index = Math.max(0, Math.min(BUSINESS_FLOW_STEPS.length - 1, Number(indexOrKey || 1) - 1))
  return BUSINESS_FLOW_STEPS[index]
}

export function getBusinessStatusCopy(stepKey, status) {
  const key = getBusinessStep(stepKey).key
  const normalized = normalizeStatus(status)
  const [label, description] = STATUS_COPY[key]?.[normalized] || STATUS_COPY.brief.idle
  return {
    key,
    status: normalized,
    label,
    description,
  }
}

export function buildBriefValidationItems(formData = {}) {
  const taskType = normalizeText(formData.consumerTaskType) || 'concept_test'
  const items = []

  const addMissing = (field, label, group, hint) => {
    items.push({ field, label, group, hint })
  }

  if (splitItems(formData.consumerAudience).length === 0) {
    addMissing('consumerAudience', '目标人群', '目标人群', '说明要测试的消费者是谁，例如职场妈妈、健身初学者。')
  }

  if (normalizeText(formData.consumerResearchGoal) === '') {
    addMissing('consumerResearchGoal', '研究目标', '研究目标', '说明这次测试最想回答的问题。')
  }

  if (taskType === 'concept_test') {
    if (splitLines(formData.consumerConcept).length === 0) {
      addMissing('consumerConcept', '产品概念', '测试素材', '粘贴要验证的产品概念。')
    }
    if (splitLines(formData.consumerCopy).length === 0) {
      addMissing('consumerCopy', '测试文案', '测试素材', '粘贴消费者会看到的文案。')
    }
  } else if (taskType === 'packaging_test') {
    if (splitLines(formData.consumerPackagingAssets).length === 0) {
      addMissing('consumerPackagingAssets', '包装素材', '测试素材', '上传包装 PDF 或图片素材。')
    }
  } else if (taskType === 'ab_test') {
    if (splitLines(formData.consumerTestVariants).length < 2) {
      addMissing('consumerTestVariants', '至少 2 个测试变体', '测试素材', '每行输入一个方案，例如 A 版标题、B 版标题。')
    }
  } else if (taskType === 'price_test') {
    if (splitItems(formData.consumerPricePoints).length === 0) {
      addMissing('consumerPricePoints', '价格点', '测试素材', '输入一个或多个要测试的价格。')
    }
  }

  return items
}

export function isBriefFieldMissing(formData = {}, field) {
  return buildBriefValidationItems(formData).some(item => item.field === field)
}

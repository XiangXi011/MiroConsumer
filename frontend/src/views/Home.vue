<template>
  <div class="home-container">
    <nav class="navbar">
      <button class="nav-brand" type="button">MIROCONSUMER</button>
      <div class="nav-links">
        <LanguageSwitcher />
      </div>
    </nav>

    <main class="business-workspace">
      <section class="workspace-intro">
        <div>
          <p class="eyebrow">品牌/市场消费者测试工作台</p>
          <h1>新建一次消费者传播测试</h1>
          <p class="intro-copy">
            填入要测试的概念、包装、价格或文案，系统会生成消费者画像、运行传播反应，并输出可追问的业务洞察报告。
          </p>
        </div>
      </section>

      <section class="workspace-grid">
        <form class="brief-form" @submit.prevent="startSimulation">
          <section class="form-section">
            <div class="section-heading">
              <span class="section-index">01</span>
              <div>
                <h2>选择测试类型</h2>
                <p>先告诉系统这次业务问题属于哪一类。</p>
              </div>
            </div>
            <div class="task-type-grid">
              <button
                v-for="task in taskTypes"
                :key="task.value"
                type="button"
                class="task-card"
                :class="{ active: formData.consumerTaskType === task.value }"
                @click="formData.consumerTaskType = task.value"
                :disabled="loading"
              >
                <span class="task-title">{{ task.label }}</span>
                <span class="task-desc">{{ task.desc }}</span>
              </button>
            </div>
          </section>

          <section class="form-section">
            <div class="section-heading">
              <span class="section-index">02</span>
              <div>
                <h2>输入测试素材</h2>
                <p>填写或上传消费者会看到的内容，每行一条更利于对比。</p>
              </div>
            </div>

            <div class="field-grid">
              <div
                v-if="formData.consumerTaskType === 'concept_test' || formData.consumerTaskType === 'price_test'"
                class="field wide"
                :class="{ missing: isMissing('consumerConcept') }"
              >
                <label for="consumerConcept">产品概念</label>
                <textarea
                  id="consumerConcept"
                  ref="consumerConceptRef"
                  v-model="formData.consumerConcept"
                  rows="4"
                  placeholder="例如：舒客酵素亮白牙膏，主打去黄提亮、温和护龈和清新口气，适合日常通勤和约会前使用。"
                  :disabled="loading"
                ></textarea>
              </div>

              <div
                v-if="formData.consumerTaskType === 'concept_test' || formData.consumerTaskType === 'packaging_test' || formData.consumerTaskType === 'price_test'"
                class="field wide"
                :class="{ missing: isMissing('consumerCopy') }"
              >
                <label for="consumerCopy">测试文案</label>
                <textarea
                  id="consumerCopy"
                  ref="consumerCopyRef"
                  v-model="formData.consumerCopy"
                  rows="4"
                  placeholder="例如：舒客酵素亮白牙膏｜温和去黄不刺激｜早晚刷出自然亮白笑容"
                  :disabled="loading"
                ></textarea>
              </div>

              <div
                v-if="formData.consumerTaskType === 'packaging_test'"
                class="field wide"
                :class="{ missing: isMissing('consumerPackagingAssets') }"
              >
                <label for="consumerPackagingAssetsInput">包装素材</label>
                <div
                  id="consumerPackagingAssets"
                  ref="consumerPackagingAssetsRef"
                  class="upload-zone packaging-upload packaging-tray"
                  :class="{ 'drag-over': isPackagingDragOver, 'has-files': packagingFiles.length > 0 }"
                  tabindex="0"
                  role="button"
                  @dragover.prevent="handlePackagingDragOver"
                  @dragleave.prevent="handlePackagingDragLeave"
                  @drop.prevent="handlePackagingDrop"
                  @click="triggerPackagingFileInput"
                  @keydown.enter.prevent="triggerPackagingFileInput"
                  @keydown.space.prevent="triggerPackagingFileInput"
                >
                  <input
                    id="consumerPackagingAssetsInput"
                    ref="packagingFileInput"
                    type="file"
                    multiple
                    accept=".pdf,.png,.jpg,.jpeg,.webp"
                    @change="handlePackagingFileSelect"
                    style="display: none"
                    :disabled="loading"
                  />
                  <div v-if="packagingFiles.length === 0" class="upload-placeholder">
                    <span class="upload-title">上传包装 PDF / 图片素材，或拖入文件</span>
                    <span class="upload-hint">支持 PDF、PNG、JPG、JPEG、WebP；可上传包装正面、背面、外盒或陈列图。</span>
                  </div>
                  <div v-else class="file-list">
                    <div v-for="(file, index) in packagingFiles" :key="`${file.name}-${index}`" class="file-item">
                      <span class="file-name">{{ file.name }}</span>
                      <button type="button" @click.stop="removePackagingFile(index)" class="remove-btn">移除</button>
                    </div>
                  </div>
                </div>
                <p class="field-hint">包装测试会优先分析你上传的包装素材，文件名会同步写入测试 brief。</p>
              </div>

              <div
                v-if="formData.consumerTaskType === 'ab_test'"
                class="field wide"
                :class="{ missing: isMissing('consumerTestVariants') }"
              >
                <label for="consumerTestVariants">测试变体</label>
                <textarea
                  id="consumerTestVariants"
                  ref="consumerTestVariantsRef"
                  v-model="formData.consumerTestVariants"
                  rows="5"
                  placeholder="A 版：舒客酵素亮白牙膏，温和去黄，刷出自然亮白&#10;B 版：舒客清新护龈牙膏，减少牙龈负担，口气更清新"
                  :disabled="loading"
                ></textarea>
              </div>

              <div
                v-if="formData.consumerTaskType === 'price_test'"
                class="field"
                :class="{ missing: isMissing('consumerPricePoints') }"
              >
                <label for="consumerPricePoints">价格点</label>
                <textarea
                  id="consumerPricePoints"
                  ref="consumerPricePointsRef"
                  v-model="formData.consumerPricePoints"
                  rows="3"
                  placeholder="例如：19.9 元、29.9 元、39.9 元"
                  :disabled="loading"
                ></textarea>
              </div>

              <div v-if="formData.consumerTaskType === 'price_test'" class="field">
                <label for="consumerPriceContext">价格语境</label>
                <textarea
                  id="consumerPriceContext"
                  v-model="formData.consumerPriceContext"
                  rows="3"
                  placeholder="例如：120g 单支装，线上旗舰店和商超渠道，首发第二件半价。"
                  :disabled="loading"
                ></textarea>
              </div>

              <div v-if="formData.consumerTaskType !== 'packaging_test'" class="field">
                <label for="consumerClaims">核心 Claim</label>
                <textarea
                  id="consumerClaims"
                  v-model="formData.consumerClaims"
                  rows="3"
                  placeholder="选填，例如：酵素亮白、温和去黄、护龈、清新口气"
                  :disabled="loading"
                ></textarea>
              </div>

              <div class="field wide">
                <label for="consumerBackgroundMaterials">背景材料</label>
                <textarea
                  id="consumerBackgroundMaterials"
                  v-model="formData.consumerBackgroundMaterials"
                  rows="3"
                  placeholder="选填。粘贴已有调研、竞品信息、风险假设或客服反馈。"
                  :disabled="loading"
                ></textarea>
              </div>
            </div>
          </section>

          <section class="form-section">
            <div class="section-heading">
              <span class="section-index">03</span>
              <div>
                <h2>定义目标人群与研究目标</h2>
                <p>让报告围绕具体业务问题作答。</p>
              </div>
            </div>

            <div class="field-grid">
              <div class="field" :class="{ missing: isMissing('consumerAudience') }">
                <label for="consumerAudience">目标人群</label>
                <textarea
                  id="consumerAudience"
                  ref="consumerAudienceRef"
                  v-model="formData.consumerAudience"
                  rows="3"
                  placeholder="例如：一二线城市 20-35 岁重视口气和牙齿美观的职场人、咖啡茶饮高频用户。"
                  :disabled="loading"
                ></textarea>
              </div>

              <div class="field">
                <label for="consumerScene">使用/购买场景</label>
                <textarea
                  id="consumerScene"
                  v-model="formData.consumerScene"
                  rows="3"
                  placeholder="选填，例如：早晚刷牙、约会/面试前、喝咖啡或茶后担心牙黄和口气。"
                  :disabled="loading"
                ></textarea>
              </div>

              <div class="field wide" :class="{ missing: isMissing('consumerResearchGoal') }">
                <label for="consumerResearchGoal">研究目标</label>
                <textarea
                  id="consumerResearchGoal"
                  ref="consumerResearchGoalRef"
                  v-model="formData.consumerResearchGoal"
                  rows="4"
                  placeholder="例如：判断“酵素亮白”是否有记忆点，消费者是否担心刺激牙龈，以及哪类人群最愿意尝试。"
                  :disabled="loading"
                ></textarea>
              </div>

              <div class="field wide">
                <label for="simulationRequirement">补充说明</label>
                <textarea
                  id="simulationRequirement"
                  v-model="formData.simulationRequirement"
                  rows="3"
                  :placeholder="simulationPromptPlaceholder"
                  :disabled="loading"
                ></textarea>
              </div>
            </div>
          </section>

          <section class="form-section optional-section">
            <button
              class="advanced-toggle"
              type="button"
              @click="showAdvanced = !showAdvanced"
            >
              <span>高级设置与辅助材料</span>
              <span>{{ showAdvanced ? '收起' : '展开' }}</span>
            </button>

            <div v-if="showAdvanced" class="advanced-content">
              <div class="field wide">
                <label>消费者画像包</label>
                <div class="pack-options">
                  <button
                    v-for="pack in availablePacks"
                    :key="pack.pack_id"
                    type="button"
                    class="mode-btn"
                    :class="{ active: formData.personaPackSelection?.pack_id === pack.pack_id && !formData.personaPackSelection?.custom_upload }"
                    @click="selectPersonaPack(pack)"
                    :disabled="loading"
                    :title="pack.description"
                  >
                    {{ pack.label }}
                  </button>
                  <button
                    type="button"
                    class="mode-btn"
                    :class="{ active: formData.personaPackSelection?.custom_upload }"
                    @click="$refs.personaPackFileInput?.click()"
                    :disabled="loading"
                  >
                    {{ personaPackFileName ? '自定义：' + personaPackFileName : '上传自定义画像包' }}
                  </button>
                </div>
                <input
                  ref="personaPackFileInput"
                  type="file"
                  accept=".json"
                  @change="handlePersonaPackFileSelect"
                  style="display: none"
                  :disabled="loading"
                />
                <p class="field-hint">{{ selectedPackLabel }}</p>
              </div>

              <div class="settings-grid">
                <div class="setting-card">
                  <span class="setting-title">预研增强</span>
                  <p>自动补充品类语境和潜在风险。</p>
                  <div class="segmented">
                    <button
                      type="button"
                      :class="{ active: formData.consumerResearchMode === 'manual_only' }"
                      @click="formData.consumerResearchMode = 'manual_only'"
                    >
                      仅使用输入材料
                    </button>
                    <button
                      type="button"
                      :class="{ active: formData.consumerResearchMode === 'auto_enrich' }"
                      @click="formData.consumerResearchMode = 'auto_enrich'"
                    >
                      自动增强
                    </button>
                  </div>
                </div>

                <div class="setting-card">
                  <span class="setting-title">公开资料补充</span>
                  <p>当内部素材不足时，允许使用公开网络来源补足背景。</p>
                  <div class="segmented">
                    <button
                      type="button"
                      :class="{ active: !formData.consumerEnableLaneB }"
                      @click="formData.consumerEnableLaneB = false"
                    >
                      关闭
                    </button>
                    <button
                      type="button"
                      :class="{ active: formData.consumerEnableLaneB }"
                      @click="formData.consumerEnableLaneB = true"
                    >
                      开启
                    </button>
                  </div>
                </div>
              </div>

              <div class="field wide">
                <label>上传辅助材料</label>
                <div
                  class="upload-zone"
                  :class="{ 'drag-over': isDragOver, 'has-files': files.length > 0 }"
                  @dragover.prevent="handleDragOver"
                  @dragleave.prevent="handleDragLeave"
                  @drop.prevent="handleDrop"
                  @click="triggerFileInput"
                >
                  <input
                    ref="fileInput"
                    type="file"
                    multiple
                    accept=".pdf,.md,.txt"
                    @change="handleFileSelect"
                    style="display: none"
                    :disabled="loading"
                  />
                  <div v-if="files.length === 0" class="upload-placeholder">
                    <span class="upload-title">拖入 PDF / Markdown / 文本，或点击选择</span>
                    <span class="upload-hint">可选，用于补充已有调研、竞品资料或产品说明。</span>
                  </div>
                  <div v-else class="file-list">
                    <div v-for="(file, index) in files" :key="index" class="file-item">
                      <span class="file-name">{{ file.name }}</span>
                      <button type="button" @click.stop="removeFile(index)" class="remove-btn">移除</button>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </section>

          <div v-if="error" class="error-message">{{ error }}</div>

          <div class="submit-bar">
            <div class="submit-copy">
              <strong>{{ canSubmit ? '可以开始测试' : '请先补齐必填信息' }}</strong>
              <span>{{ canSubmit ? '下一步会自动准备测试素材和消费者画像。' : '右侧会提示缺少哪些信息。' }}</span>
            </div>
            <button class="start-btn" type="submit" :disabled="!canSubmit || loading">
              开始消费者测试
            </button>
          </div>
        </form>

        <aside class="side-panel">
          <BriefValidationSummary
            :items="briefValidationItems"
            @focus-field="focusField"
          />

          <div class="flow-card">
            <h2>接下来会发生什么</h2>
            <div class="flow-list">
              <div v-for="(step, idx) in flowSteps" :key="step.key" class="flow-item">
                <span>{{ idx + 1 }}</span>
                <div>
                  <strong>{{ step.title }}</strong>
                  <p>{{ step.description }}</p>
                </div>
              </div>
            </div>
          </div>
        </aside>
      </section>

      <section class="history-section">
        <div class="history-heading">
          <p class="eyebrow">历史测试</p>
          <h2>继续查看已有项目</h2>
        </div>
        <HistoryDatabase />
      </section>
    </main>
  </div>
</template>

<script setup lang="ts">
// @ts-nocheck
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import HistoryDatabase from '../components/HistoryDatabase.vue'
import LanguageSwitcher from '../components/LanguageSwitcher.vue'
import BriefValidationSummary from '../components/BriefValidationSummary.vue'
import {
  buildPackagingAssetSummary,
  buildConsumerBrief,
  isPackagingAssetFile,
  isConsumerBriefComplete,
  resolveSimulationRequirement
} from '../utils/consumerBrief'
import {
  buildBriefValidationItems,
  getBusinessFlowSteps,
  isBriefFieldMissing
} from '../utils/businessUx'
import { setPendingUpload } from '../store/pendingUpload.ts'
import { listPersonaPacks } from '../api/graph.ts'

const router = useRouter()
const { t } = useI18n()

const formData = ref({
  projectType: 'consumer_test',
  simulationRequirement: '',
  consumerTaskType: 'concept_test',
  consumerConcept: '',
  consumerCopy: '',
  consumerClaims: '',
  consumerAudience: '',
  consumerScene: '',
  consumerResearchGoal: '',
  consumerResearchMode: 'manual_only',
  consumerEnableLaneB: false,
  consumerBackgroundMaterials: '',
  consumerPackagingAssets: '',
  consumerTestVariants: '',
  consumerPricePoints: '',
  consumerPriceContext: '',
  personaPackSelection: null
})

const taskTypes = [
  { value: 'concept_test', label: '概念测试', desc: '验证概念是否清楚、有吸引力、会不会被误读。' },
  { value: 'packaging_test', label: '包装测试', desc: '观察包装信息、视觉线索和信任感。' },
  { value: 'ab_test', label: 'A/B 测试', desc: '比较多个方案在不同人群中的共鸣差异。' },
  { value: 'price_test', label: '价格测试', desc: '判断价格接受度、价值感和价格异议。' },
  { value: 'copy_feedback', label: '文案反馈', desc: '快速收集消费者对文案表达的反应。' },
]

const fieldRefs = {
  consumerConcept: ref(null),
  consumerCopy: ref(null),
  consumerPackagingAssets: ref(null),
  consumerTestVariants: ref(null),
  consumerPricePoints: ref(null),
  consumerAudience: ref(null),
  consumerResearchGoal: ref(null),
}

const {
  consumerConcept: consumerConceptRef,
  consumerCopy: consumerCopyRef,
  consumerPackagingAssets: consumerPackagingAssetsRef,
  consumerTestVariants: consumerTestVariantsRef,
  consumerPricePoints: consumerPricePointsRef,
  consumerAudience: consumerAudienceRef,
  consumerResearchGoal: consumerResearchGoalRef,
} = fieldRefs

const availablePacks = ref([])
const personaPackFile = ref(null)
const personaPackFileName = ref('')
const files = ref([])
const packagingFiles = ref([])
const loading = ref(false)
const error = ref('')
const isDragOver = ref(false)
const isPackagingDragOver = ref(false)
const fileInput = ref(null)
const packagingFileInput = ref(null)
const showAdvanced = ref(false)

const isConsumerMode = computed(() => formData.value.projectType === 'consumer_test')
const flowSteps = computed(() => getBusinessFlowSteps())
const briefValidationItems = computed(() => buildBriefValidationItems(formData.value))

const simulationPromptPlaceholder = computed(() => (
  isConsumerMode.value
    ? '选填。补充这次测试需要特别关注的角度，例如「更关注消费者是否相信酵素亮白」或「比较咖啡用户与普通用户的接受差异」。'
    : t('home.promptPlaceholder')
))

const resolvedSimulationRequirement = computed(() => (
  resolveSimulationRequirement(
    formData.value.projectType,
    formData.value.simulationRequirement,
    t('home.consumerDefaultPrompt')
  )
))

const canSubmit = computed(() => {
  if (isConsumerMode.value) {
    return isConsumerBriefComplete(formData.value)
  }
  if (files.value.length === 0 && formData.value.simulationRequirement.trim() === '') {
    return false
  }
  return formData.value.simulationRequirement.trim() !== ''
})

const isMissing = (field) => isBriefFieldMissing(formData.value, field)

const focusField = (field) => {
  const target = fieldRefs[field]?.value
  if (target?.focus) {
    target.focus()
    target.scrollIntoView({ behavior: 'smooth', block: 'center' })
  }
}

const triggerFileInput = () => {
  if (!loading.value) {
    fileInput.value?.click()
  }
}

const triggerPackagingFileInput = () => {
  if (!loading.value) {
    packagingFileInput.value?.click()
  }
}

const handleFileSelect = (event) => {
  const selectedFiles = Array.from(event.target.files)
  addFiles(selectedFiles)
  event.target.value = ''
}

const handlePackagingFileSelect = (event) => {
  const selectedFiles = Array.from(event.target.files)
  addPackagingFiles(selectedFiles)
  event.target.value = ''
}

const handleDragOver = () => {
  if (!loading.value) {
    isDragOver.value = true
  }
}

const handleDragLeave = () => {
  isDragOver.value = false
}

const handleDrop = (e) => {
  isDragOver.value = false
  if (loading.value) return
  const droppedFiles = Array.from(e.dataTransfer.files)
  addFiles(droppedFiles)
}

const handlePackagingDragOver = () => {
  if (!loading.value) {
    isPackagingDragOver.value = true
  }
}

const handlePackagingDragLeave = () => {
  isPackagingDragOver.value = false
}

const handlePackagingDrop = (e) => {
  isPackagingDragOver.value = false
  if (loading.value) return
  const droppedFiles = Array.from(e.dataTransfer.files)
  addPackagingFiles(droppedFiles)
}

const addFiles = (newFiles) => {
  const validFiles = newFiles.filter(file => {
    const ext = file.name.split('.').pop().toLowerCase()
    return ['pdf', 'md', 'txt'].includes(ext)
  })
  files.value.push(...validFiles)
}

const syncPackagingAssetSummary = () => {
  formData.value.consumerPackagingAssets = buildPackagingAssetSummary(packagingFiles.value)
}

const addPackagingFiles = (newFiles) => {
  const validFiles = newFiles.filter(isPackagingAssetFile)
  const invalidCount = newFiles.length - validFiles.length
  if (invalidCount > 0) {
    error.value = '包装素材仅支持 PDF、PNG、JPG、JPEG、WebP 文件。'
  } else {
    error.value = ''
  }
  packagingFiles.value.push(...validFiles)
  syncPackagingAssetSummary()
}

const removeFile = (index) => {
  files.value.splice(index, 1)
}

const removePackagingFile = (index) => {
  packagingFiles.value.splice(index, 1)
  syncPackagingAssetSummary()
}

const selectPersonaPack = (pack) => {
  formData.value.personaPackSelection = {
    pack_id: pack.pack_id,
    pack_class: pack.pack_class,
    custom_upload: false
  }
  personaPackFile.value = null
  personaPackFileName.value = ''
}

const handlePersonaPackFileSelect = (event) => {
  const file = event.target.files?.[0]
  if (!file) return
  if (!file.name.toLowerCase().endsWith('.json')) {
    error.value = '画像包必须是 JSON 文件。'
    event.target.value = ''
    return
  }
  error.value = ''
  personaPackFile.value = file
  personaPackFileName.value = file.name
  formData.value.personaPackSelection = {
    pack_id: 'custom_upload',
    pack_class: 'custom',
    custom_upload: true
  }
}

const selectedPackLabel = computed(() => {
  if (formData.value.personaPackSelection?.custom_upload) {
    return '自定义画像包：' + personaPackFileName.value
  }
  const pack = availablePacks.value.find(
    p => p.pack_id === formData.value.personaPackSelection?.pack_id
  )
  return pack?.description ? `${pack.label}：${pack.description}` : (pack?.label || '默认消费者画像包')
})

const fetchPersonaPacks = async () => {
  try {
    const res = await listPersonaPacks()
    if (res.success && res.data) {
      availablePacks.value = res.data
      if (!formData.value.personaPackSelection) {
        const defaultPack = res.data.find(p => p.pack_id === 'default_persona_pack')
        if (defaultPack) {
          selectPersonaPack(defaultPack)
        }
      }
    }
  } catch (e) {
    console.warn('Failed to load persona packs:', e)
  }
}

const startSimulation = () => {
  if (!canSubmit.value || loading.value) {
    const firstMissing = briefValidationItems.value[0]
    if (firstMissing) focusField(firstMissing.field)
    return
  }

  const uploadFiles = formData.value.consumerTaskType === 'packaging_test'
    ? [...packagingFiles.value, ...files.value]
    : files.value

  setPendingUpload({
    files: uploadFiles,
    simulationRequirement: resolvedSimulationRequirement.value,
    projectType: formData.value.projectType,
    consumerBrief: isConsumerMode.value ? buildConsumerBrief(formData.value) : null,
    researchMode: isConsumerMode.value ? (formData.value.consumerResearchMode || 'manual_only') : 'manual_only',
    enableLaneB: isConsumerMode.value ? Boolean(formData.value.consumerEnableLaneB) : false,
    personaPackSelection: isConsumerMode.value ? formData.value.personaPackSelection : null,
    personaPackFile: isConsumerMode.value ? personaPackFile.value : null
  })

  router.push({
    name: 'Process',
    params: { projectId: 'new' }
  })
}

onMounted(() => {
  fetchPersonaPacks()
})
</script>

<style scoped>
.home-container {
  min-height: 100vh;
  background: var(--mc-bg-canvas);
  color: var(--mc-text-primary);
  font-family: var(--mc-font-body);
}

.navbar {
  min-height: 60px;
  background: rgba(255, 253, 250, 0.94);
  border-bottom: 1px solid var(--mc-border);
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0 32px;
  position: sticky;
  top: 0;
  z-index: 20;
  backdrop-filter: blur(14px);
}

.nav-brand {
  border: none;
  background: transparent;
  font-family: var(--mc-font-mono);
  font-weight: 800;
  font-size: 18px;
  letter-spacing: 1px;
  color: var(--mc-text-primary);
}

.nav-links {
  display: flex;
  align-items: center;
  gap: 12px;
}

.business-workspace {
  width: min(1440px, 100%);
  margin: 0 auto;
  padding: 30px 32px 46px;
}

.workspace-intro {
  max-width: 820px;
  margin-bottom: 24px;
}

.eyebrow {
  margin: 0 0 10px;
  font-size: 12px;
  font-weight: 800;
  color: var(--mc-accent);
  letter-spacing: 0.08em;
}

h1 {
  margin: 0;
  font-size: clamp(32px, 4vw, 56px);
  line-height: 1.08;
  letter-spacing: 0;
  font-weight: 800;
  color: var(--mc-text-primary);
}

.intro-copy {
  max-width: 760px;
  margin: 18px 0 0;
  color: var(--mc-text-secondary);
  font-size: 17px;
  line-height: 1.8;
}

.workspace-grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 360px;
  gap: 24px;
  align-items: start;
}

.brief-form {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.form-section,
.side-panel > *,
.history-section {
  background: var(--mc-surface);
  border: 1px solid var(--mc-border);
  border-radius: var(--mc-radius-card);
  box-shadow: var(--mc-shadow-card);
}

.form-section {
  padding: 22px;
}

.section-heading {
  display: flex;
  gap: 14px;
  align-items: flex-start;
  margin-bottom: 18px;
}

.section-index {
  width: 32px;
  height: 32px;
  border-radius: 999px;
  background: var(--mc-accent);
  color: #fffdfa;
  font-family: var(--mc-font-mono);
  font-size: 12px;
  font-weight: 800;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.section-heading h2,
.flow-card h2,
.history-heading h2 {
  margin: 0;
  font-size: 20px;
  line-height: 1.25;
}

.section-heading p,
.flow-card p {
  margin: 6px 0 0;
  color: var(--mc-text-secondary);
  line-height: 1.6;
}

.task-type-grid {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 8px;
}

.task-card {
  min-height: 88px;
  border: 1px solid var(--mc-border);
  background: var(--mc-surface-muted);
  border-radius: var(--mc-radius-card);
  padding: 12px;
  display: flex;
  flex-direction: column;
  gap: 8px;
  text-align: left;
  cursor: pointer;
  transition: all 0.2s ease;
}

.task-card:hover:not(:disabled) {
  border-color: var(--mc-border-strong);
  background: var(--mc-surface);
  transform: translateY(-1px);
}

.task-card.active {
  border-color: var(--mc-accent);
  background: linear-gradient(180deg, var(--mc-accent), var(--mc-accent-strong));
  color: #fffdfa;
  box-shadow: 0 12px 28px rgba(34, 92, 75, 0.18);
}

.task-title {
  font-size: 15px;
  font-weight: 800;
}

.task-desc {
  font-size: 12px;
  line-height: 1.5;
  color: var(--mc-text-secondary);
}

.task-card.active .task-desc {
  color: #e8f2ed;
}

.field-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.field.wide {
  grid-column: 1 / -1;
}

.field label {
  font-size: 13px;
  font-weight: 800;
  color: var(--mc-text-primary);
}

.field textarea {
  width: 100%;
  border: 1px solid var(--mc-border);
  background: var(--mc-surface-raised);
  border-radius: var(--mc-radius-control);
  padding: 12px 14px;
  font: inherit;
  font-size: 14px;
  line-height: 1.6;
  resize: vertical;
  outline: none;
}

.field textarea:focus {
  border-color: var(--mc-accent);
  box-shadow: var(--mc-focus-ring);
}

.field.missing textarea {
  border-color: var(--mc-status-warning);
  background: var(--mc-status-warning-bg);
}

.field-hint {
  margin: 0;
  color: var(--mc-text-secondary);
  font-size: 12px;
  line-height: 1.5;
}

.optional-section {
  padding: 0;
  overflow: hidden;
}

.advanced-toggle {
  width: 100%;
  border: none;
  background: var(--mc-surface);
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 18px 22px;
  font-size: 15px;
  font-weight: 800;
  color: var(--mc-text-primary);
  cursor: pointer;
}

.advanced-content {
  border-top: 1px solid var(--mc-border);
  padding: 22px;
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.pack-options,
.segmented {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.mode-btn,
.segmented button {
  border: 1px solid var(--mc-border);
  background: var(--mc-surface);
  color: var(--mc-text-secondary);
  padding: 9px 12px;
  border-radius: 6px;
  font-size: 13px;
  font-weight: 700;
  cursor: pointer;
}

.mode-btn.active,
.segmented button.active {
  background: var(--mc-accent);
  border-color: var(--mc-accent);
  color: #fffdfa;
}

.settings-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px;
}

.setting-card {
  border: 1px solid var(--mc-border);
  background: var(--mc-surface-muted);
  border-radius: var(--mc-radius-card);
  padding: 14px;
}

.setting-title {
  display: block;
  font-weight: 800;
  margin-bottom: 6px;
}

.setting-card p {
  margin: 0 0 12px;
  color: var(--mc-text-secondary);
  font-size: 13px;
  line-height: 1.5;
}

.upload-zone {
  border: 1px dashed var(--mc-border-strong);
  background: var(--mc-bg-subtle);
  border-radius: var(--mc-radius-card);
  min-height: 130px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  padding: 16px;
  outline: none;
}

.upload-zone.drag-over,
.upload-zone:hover {
  border-color: var(--mc-accent);
  background: var(--mc-surface);
}

.upload-zone:focus {
  border-color: var(--mc-accent);
  box-shadow: var(--mc-focus-ring);
}

.field.missing .upload-zone {
  border-color: var(--mc-status-warning);
  background: var(--mc-status-warning-bg);
}

.packaging-tray {
  min-height: 148px;
  background:
    linear-gradient(135deg, rgba(34, 92, 75, 0.08), transparent 34%),
    var(--mc-bg-subtle);
  border-style: solid;
}

.packaging-tray.has-files {
  align-items: stretch;
}

.upload-placeholder {
  display: flex;
  flex-direction: column;
  gap: 6px;
  text-align: center;
}

.upload-title {
  font-weight: 800;
}

.upload-hint {
  color: var(--mc-text-secondary);
  font-size: 13px;
}

.file-list {
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.file-item {
  background: var(--mc-surface);
  border: 1px solid var(--mc-border);
  border-radius: var(--mc-radius-control);
  padding: 9px 10px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.file-name {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.remove-btn {
  border: none;
  background: transparent;
  color: var(--mc-status-error);
  font-weight: 700;
  cursor: pointer;
}

.error-message {
  border: 1px solid rgba(180, 35, 24, 0.22);
  background: var(--mc-status-error-bg);
  color: var(--mc-status-error);
  border-radius: var(--mc-radius-card);
  padding: 12px 14px;
}

.submit-bar {
  position: sticky;
  bottom: 0;
  z-index: 10;
  background: rgba(255, 253, 250, 0.94);
  backdrop-filter: blur(8px);
  border: 1px solid var(--mc-border);
  border-radius: var(--mc-radius-card);
  padding: 14px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
  box-shadow: 0 -12px 30px rgba(24, 45, 35, 0.08);
}

.submit-copy {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.submit-copy span {
  color: var(--mc-text-secondary);
  font-size: 13px;
}

.start-btn {
  border: none;
  background: var(--mc-accent);
  color: #fffdfa;
  border-radius: var(--mc-radius-control);
  padding: 13px 18px;
  font-size: 15px;
  font-weight: 800;
  cursor: pointer;
  white-space: nowrap;
}

.start-btn:disabled {
  background: var(--mc-border);
  color: var(--mc-text-tertiary);
  cursor: not-allowed;
}

.side-panel {
  display: flex;
  flex-direction: column;
  gap: 16px;
  position: sticky;
  top: 84px;
}

.flow-card {
  padding: 18px;
}

.flow-list {
  display: flex;
  flex-direction: column;
  gap: 14px;
  margin-top: 16px;
}

.flow-item {
  display: grid;
  grid-template-columns: 28px 1fr;
  gap: 10px;
}

.flow-item > span {
  width: 28px;
  height: 28px;
  border-radius: 999px;
  background: var(--mc-surface-muted);
  color: var(--mc-text-secondary);
  display: flex;
  align-items: center;
  justify-content: center;
  font-family: var(--mc-font-mono);
  font-size: 12px;
  font-weight: 800;
}

.flow-item strong {
  font-size: 14px;
}

.flow-item p {
  font-size: 12px;
}

.history-section {
  margin-top: 28px;
  padding: 22px;
}

.history-heading {
  margin-bottom: 16px;
}

@media (max-width: 1180px) {
  .workspace-grid {
    grid-template-columns: 1fr;
  }

  .side-panel {
    position: static;
  }

  .task-type-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 720px) {
  .navbar {
    padding: 0 18px;
  }

  .business-workspace {
    padding: 20px 14px 28px;
  }

  .field-grid,
  .settings-grid,
  .task-type-grid {
    grid-template-columns: 1fr;
  }

  .submit-bar {
    position: static;
    flex-direction: column;
    align-items: stretch;
  }

  .start-btn {
    width: 100%;
  }
}
</style>

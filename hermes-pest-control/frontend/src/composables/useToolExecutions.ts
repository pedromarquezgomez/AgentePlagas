import { ref, computed } from 'vue'
import {
  fetchToolExecutionRecords,
  fetchHumanReviewItems,
  listShadowDecisionRecords,
  type ToolExecutionRecord,
  type HumanReviewItem,
  type ShadowDecisionRecord
} from '../services/api'

export function useToolExecutions() {
  // 1. Tool Executions (Acciones IA)
  const toolExecutionRecords = ref<ToolExecutionRecord[]>([])
  const toolStatusFilter = ref('')
  const toolNameFilter = ref('')
  const toolProviderFilter = ref('')
  const toolDecisionFilter = ref('')
  const toolRiskFilter = ref('')
  const toolRequiresApprovalFilter = ref('')
  const toolLimitFilter = ref('100')
  const loadingTools = ref(false)
  const errorTools = ref<string | null>(null)

  const hasToolFilters = computed(() => {
    return Boolean(
      toolStatusFilter.value ||
      toolNameFilter.value ||
      toolProviderFilter.value ||
      toolDecisionFilter.value ||
      toolRiskFilter.value ||
      toolRequiresApprovalFilter.value ||
      toolLimitFilter.value !== '100'
    )
  })

  async function loadToolExecutionRecords() {
    loadingTools.value = true
    errorTools.value = null
    try {
      toolExecutionRecords.value = await fetchToolExecutionRecords({
        status: toolStatusFilter.value || undefined,
        tool_name: toolNameFilter.value || undefined,
        provider: toolProviderFilter.value || undefined,
        decision: toolDecisionFilter.value || undefined,
        risk_level: toolRiskFilter.value === '' ? undefined : Number(toolRiskFilter.value),
        requires_approval: toolRequiresApprovalFilter.value === ''
          ? undefined
          : toolRequiresApprovalFilter.value === 'true',
        limit: Number(toolLimitFilter.value || '100')
      })
    } catch (err) {
      errorTools.value = err instanceof Error ? err.message : 'No se pudieron cargar las acciones IA'
      toolExecutionRecords.value = []
    } finally {
      loadingTools.value = false
    }
  }

  function clearToolFilters() {
    toolStatusFilter.value = ''
    toolNameFilter.value = ''
    toolProviderFilter.value = ''
    toolDecisionFilter.value = ''
    toolRiskFilter.value = ''
    toolRequiresApprovalFilter.value = ''
    toolLimitFilter.value = '100'
    void loadToolExecutionRecords()
  }

  // 2. Human Review (Revisión Humana)
  const reviewItems = ref<HumanReviewItem[]>([])
  const reviewStatusFilter = ref('')
  const reviewPriorityFilter = ref('')
  const loadingReviews = ref(false)
  const errorReviews = ref<string | null>(null)

  const hasReviewFilters = computed(() => {
    return Boolean(reviewStatusFilter.value || reviewPriorityFilter.value)
  })

  async function loadHumanReviewItems() {
    loadingReviews.value = true
    errorReviews.value = null
    try {
      reviewItems.value = await fetchHumanReviewItems({
        status: reviewStatusFilter.value || undefined,
        priority: reviewPriorityFilter.value || undefined,
        limit: 100
      })
    } catch (err) {
      errorReviews.value = err instanceof Error ? err.message : 'No se pudo cargar la cola de revisión'
      reviewItems.value = []
    } finally {
      loadingReviews.value = false
    }
  }

  function clearReviewFilters() {
    reviewStatusFilter.value = ''
    reviewPriorityFilter.value = ''
    void loadHumanReviewItems()
  }

  // 3. Shadow Decisions (Evaluaciones en Sombra)
  const shadowDecisionRecords = ref<ShadowDecisionRecord[]>([])
  const shadowChannelFilter = ref('')
  const shadowActionFilter = ref('')
  const shadowLimitFilter = ref('100')
  const loadingShadow = ref(false)
  const errorShadow = ref<string | null>(null)

  const hasShadowFilters = computed(() => {
    return Boolean(shadowChannelFilter.value || shadowActionFilter.value || shadowLimitFilter.value !== '100')
  })

  async function loadShadowDecisionRecords() {
    loadingShadow.value = true
    errorShadow.value = null
    try {
      shadowDecisionRecords.value = await listShadowDecisionRecords({
        channel: shadowChannelFilter.value || undefined,
        shadow_action_type: shadowActionFilter.value || undefined,
        limit: Number(shadowLimitFilter.value || '100')
      })
    } catch (err) {
      errorShadow.value = err instanceof Error ? err.message : 'No se pudieron cargar las evaluaciones IA'
      shadowDecisionRecords.value = []
    } finally {
      loadingShadow.value = false
    }
  }

  function clearShadowFilters() {
    shadowChannelFilter.value = ''
    shadowActionFilter.value = ''
    shadowLimitFilter.value = '100'
    void loadShadowDecisionRecords()
  }

  return {
    // Tools
    toolExecutionRecords,
    toolStatusFilter,
    toolNameFilter,
    toolProviderFilter,
    toolDecisionFilter,
    toolRiskFilter,
    toolRequiresApprovalFilter,
    toolLimitFilter,
    loadingTools,
    errorTools,
    hasToolFilters,
    loadToolExecutionRecords,
    clearToolFilters,

    // Reviews
    reviewItems,
    reviewStatusFilter,
    reviewPriorityFilter,
    loadingReviews,
    errorReviews,
    hasReviewFilters,
    loadHumanReviewItems,
    clearReviewFilters,

    // Shadow Decisions
    shadowDecisionRecords,
    shadowChannelFilter,
    shadowActionFilter,
    shadowLimitFilter,
    loadingShadow,
    errorShadow,
    hasShadowFilters,
    loadShadowDecisionRecords,
    clearShadowFilters
  }
}

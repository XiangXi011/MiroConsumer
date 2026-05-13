// @ts-nocheck
import { ref } from 'vue'

export function useResearchAssetState() {
  const researchAssets = ref([])
  const exportingAsset = ref(false)
  const assetExportName = ref('')

  function setResearchAssets(list) {
    researchAssets.value = list
  }

  function addResearchAsset(item) {
    researchAssets.value = [...researchAssets.value, item]
  }

  function removeResearchAsset(id) {
    researchAssets.value = researchAssets.value.filter(a => a.id !== id)
  }

  function setExportingAsset(flag) {
    exportingAsset.value = flag
  }

  function setAssetExportName(name) {
    assetExportName.value = name
  }

  function reset() {
    researchAssets.value = []
    exportingAsset.value = false
    assetExportName.value = ''
  }

  return {
    researchAssets,
    exportingAsset,
    assetExportName,
    setResearchAssets,
    addResearchAsset,
    removeResearchAsset,
    setExportingAsset,
    setAssetExportName,
    reset
  }
}

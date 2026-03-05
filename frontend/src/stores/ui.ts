import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useUIStore = defineStore('ui', () => {
  // Panel states
  const leftPanelWidth = ref(280)
  const rightPanelWidth = ref(350)
  const leftPanelCollapsed = ref(false)
  const rightPanelCollapsed = ref(false)

  // Right panel tabs
  const rightPanelActiveTab = ref<'files' | 'console' | 'logs' | 'tasks'>('files')

  // Theme
  const theme = ref<'light' | 'dark'>(
    (localStorage.getItem('theme') as 'light' | 'dark') || 'dark'
  )

  // Settings
  const autoScroll = ref(localStorage.getItem('autoScroll') !== 'false')
  const showTimestamps = ref(localStorage.getItem('showTimestamps') !== 'false')

  // Modal states
  const showNewProjectModal = ref(false)
  const showSettingsModal = ref(false)

  // Actions
  function toggleLeftPanel() {
    leftPanelCollapsed.value = !leftPanelCollapsed.value
  }

  function toggleRightPanel() {
    rightPanelCollapsed.value = !rightPanelCollapsed.value
  }

  function setRightPanelTab(tab: 'files' | 'console' | 'logs' | 'tasks') {
    rightPanelActiveTab.value = tab
    if (rightPanelCollapsed.value) {
      rightPanelCollapsed.value = false
    }
  }

  function setTheme(newTheme: 'light' | 'dark') {
    theme.value = newTheme
    localStorage.setItem('theme', newTheme)
    applyTheme(newTheme)
  }

  function applyTheme(theme: 'light' | 'dark') {
    document.documentElement.setAttribute('data-theme', theme)
  }

  function setAutoScroll(value: boolean) {
    autoScroll.value = value
    localStorage.setItem('autoScroll', String(value))
  }

  function setShowTimestamps(value: boolean) {
    showTimestamps.value = value
    localStorage.setItem('showTimestamps', String(value))
  }

  function openNewProjectModal() {
    showNewProjectModal.value = true
  }

  function closeNewProjectModal() {
    showNewProjectModal.value = false
  }

  function openSettingsModal() {
    showSettingsModal.value = true
  }

  function closeSettingsModal() {
    showSettingsModal.value = false
  }

  // Initialize theme on load
  applyTheme(theme.value)

  return {
    // Panel states
    leftPanelWidth,
    rightPanelWidth,
    leftPanelCollapsed,
    rightPanelCollapsed,
    rightPanelActiveTab,
    // Theme
    theme,
    // Settings
    autoScroll,
    showTimestamps,
    // Modal states
    showNewProjectModal,
    showSettingsModal,
    // Actions
    toggleLeftPanel,
    toggleRightPanel,
    setRightPanelTab,
    setTheme,
    setAutoScroll,
    setShowTimestamps,
    openNewProjectModal,
    closeNewProjectModal,
    openSettingsModal,
    closeSettingsModal,
  }
})

<template>
  <div class="main-layout">
    <!-- Left Panel - Project List -->
    <aside
      class="left-panel"
      :class="{ collapsed: uiStore.leftPanelCollapsed }"
      :style="{ width: uiStore.leftPanelCollapsed ? '48px' : `${uiStore.leftPanelWidth}px` }"
    >
      <LeftPanel />
    </aside>

    <!-- Center Panel - Chat Area -->
    <main class="center-panel">
      <CenterPanel />
    </main>

    <!-- Right Panel - Console & Files -->
    <aside
      class="right-panel"
      :class="{ collapsed: uiStore.rightPanelCollapsed }"
      :style="{ width: uiStore.rightPanelCollapsed ? '48px' : `${uiStore.rightPanelWidth}px` }"
    >
      <RightPanel />
    </aside>

    <!-- Modals -->
    <NewProjectModal v-if="uiStore.showNewProjectModal" />
    <SettingsModal v-if="uiStore.showSettingsModal" />
  </div>
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import { useProjectStore } from '@/stores/project'
import { useUIStore } from '@/stores/ui'
import LeftPanel from './panels/LeftPanel.vue'
import CenterPanel from './panels/CenterPanel.vue'
import RightPanel from './panels/RightPanel.vue'
import NewProjectModal from './modals/NewProjectModal.vue'
import SettingsModal from './modals/SettingsModal.vue'

const projectStore = useProjectStore()
const uiStore = useUIStore()

onMounted(async () => {
  await projectStore.fetchProjects()
  projectStore.setupWebSocketHandlers()
})
</script>

<style scoped>
.main-layout {
  display: flex;
  height: 100vh;
  width: 100vw;
  overflow: hidden;
  background: var(--bg-primary);
}

.left-panel,
.right-panel {
  flex-shrink: 0;
  background: var(--bg-secondary);
  border-right: 1px solid var(--border-color);
  transition: width var(--transition-normal);
  overflow: hidden;
}

.right-panel {
  border-right: none;
  border-left: 1px solid var(--border-color);
}

.center-panel {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  background: var(--bg-primary);
}

.left-panel.collapsed,
.right-panel.collapsed {
  width: 48px !important;
}
</style>

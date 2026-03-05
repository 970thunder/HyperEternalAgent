<template>
  <div class="right-panel-content">
    <!-- Header -->
    <div class="panel-header">
      <template v-if="!uiStore.rightPanelCollapsed">
        <div class="tabs">
          <button
            v-for="tab in tabs"
            :key="tab.id"
            class="tab-btn"
            :class="{ active: uiStore.rightPanelActiveTab === tab.id }"
            @click="uiStore.setRightPanelTab(tab.id)"
          >
            <component :is="tab.icon" />
            <span>{{ tab.label }}</span>
          </button>
        </div>
      </template>
      <button class="btn btn-icon btn-ghost collapse-btn" @click="uiStore.toggleRightPanel">
        <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <template v-if="uiStore.rightPanelCollapsed">
            <polyline points="15 18 9 12 15 6"></polyline>
          </template>
          <template v-else>
            <polyline points="9 18 15 12 9 6"></polyline>
          </template>
        </svg>
      </button>
    </div>

    <!-- Content -->
    <div v-if="!uiStore.rightPanelCollapsed" class="panel-body">
      <FilesTab v-if="uiStore.rightPanelActiveTab === 'files'" />
      <ConsoleTab v-else-if="uiStore.rightPanelActiveTab === 'console'" />
      <LogsTab v-else-if="uiStore.rightPanelActiveTab === 'logs'" />
      <TasksTab v-else-if="uiStore.rightPanelActiveTab === 'tasks'" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { h } from 'vue'
import { useUIStore } from '@/stores/ui'
import FilesTab from './right-panel/FilesTab.vue'
import ConsoleTab from './right-panel/ConsoleTab.vue'
import LogsTab from './right-panel/LogsTab.vue'
import TasksTab from './right-panel/TasksTab.vue'

const uiStore = useUIStore()

// Icon components
const FilesIcon = () => h('svg', { xmlns: 'http://www.w3.org/2000/svg', width: 16, height: 16, viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', 'stroke-width': 2, 'stroke-linecap': 'round', 'stroke-linejoin': 'round' }, [
  h('path', { d: 'M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z' })
])

const ConsoleIcon = () => h('svg', { xmlns: 'http://www.w3.org/2000/svg', width: 16, height: 16, viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', 'stroke-width': 2, 'stroke-linecap': 'round', 'stroke-linejoin': 'round' }, [
  h('polyline', { points: '4 17 10 11 4 5' }),
  h('line', { x1: 12, y1: 19, x2: 20, y2: 19 })
])

const LogsIcon = () => h('svg', { xmlns: 'http://www.w3.org/2000/svg', width: 16, height: 16, viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', 'stroke-width': 2, 'stroke-linecap': 'round', 'stroke-linejoin': 'round' }, [
  h('path', { d: 'M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z' }),
  h('polyline', { points: '14 2 14 8 20 8' }),
  h('line', { x1: 16, y1: 13, x2: 8, y2: 13 }),
  h('line', { x1: 16, y1: 17, x2: 8, y2: 17 }),
  h('polyline', { points: '10 9 9 9 8 9' })
])

const TasksIcon = () => h('svg', { xmlns: 'http://www.w3.org/2000/svg', width: 16, height: 16, viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', 'stroke-width': 2, 'stroke-linecap': 'round', 'stroke-linejoin': 'round' }, [
  h('path', { d: 'M9 11l3 3L22 4' }),
  h('path', { d: '21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11' })
])

const tabs = [
  { id: 'files' as const, label: 'Files', icon: FilesIcon },
  { id: 'console' as const, label: 'Console', icon: ConsoleIcon },
  { id: 'logs' as const, label: 'Logs', icon: LogsIcon },
  { id: 'tasks' as const, label: 'Tasks', icon: TasksIcon },
]
</script>

<style scoped>
.right-panel-content {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--spacing-sm);
  border-bottom: 1px solid var(--border-color);
  min-height: 48px;
}

.tabs {
  display: flex;
  gap: 2px;
  flex: 1;
}

.tab-btn {
  display: flex;
  align-items: center;
  gap: var(--spacing-xs);
  padding: var(--spacing-xs) var(--spacing-sm);
  background: transparent;
  border: none;
  border-radius: var(--radius-sm);
  color: var(--text-secondary);
  font-size: 0.75rem;
  cursor: pointer;
  transition: all var(--transition-fast);
}

.tab-btn:hover {
  background: var(--bg-hover);
  color: var(--text-primary);
}

.tab-btn.active {
  background: var(--bg-active);
  color: var(--accent-primary);
}

.collapse-btn {
  margin-left: auto;
}

.panel-body {
  flex: 1;
  overflow: hidden;
}
</style>

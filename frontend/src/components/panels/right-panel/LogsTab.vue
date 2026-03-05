<template>
  <div class="logs-tab">
    <div v-if="!projectStore.currentProject" class="empty-state">
      <p>Select a project to view logs</p>
    </div>

    <template v-else>
      <div class="logs-header">
        <div class="log-filters">
          <button
            v-for="level in logLevels"
            :key="level"
            class="filter-btn"
            :class="{ active: activeFilters.has(level) }"
            @click="toggleFilter(level)"
          >
            {{ level }}
          </button>
        </div>
        <div class="logs-actions">
          <span class="logs-count">{{ filteredLogs.length }} logs</span>
          <button class="btn btn-ghost btn-sm" @click="clearLogs">
            <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <polyline points="3 6 5 6 21 6"></polyline>
              <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
            </svg>
          </button>
        </div>
      </div>

      <div class="logs-list" ref="logsContainer">
        <div v-if="filteredLogs.length === 0" class="no-logs">
          No logs to display
        </div>

        <div
          v-for="log in filteredLogs"
          :key="log.id"
          class="log-entry"
          :class="log.level"
        >
          <span class="log-time">{{ formatTime(log.timestamp) }}</span>
          <span class="log-level">{{ log.level.toUpperCase() }}</span>
          <span class="log-source">{{ log.source }}</span>
          <span class="log-message">{{ log.message }}</span>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { useProjectStore } from '@/stores/project'
import { useUIStore } from '@/stores/ui'
import type { LogLevel } from '@/types'

const projectStore = useProjectStore()
const uiStore = useUIStore()

const logLevels: LogLevel[] = ['debug', 'info', 'warning', 'error', 'critical']
const activeFilters = ref(new Set<LogLevel>(['info', 'warning', 'error', 'critical']))
const logsContainer = ref<HTMLElement | null>(null)

const filteredLogs = computed(() => {
  return projectStore.logs.filter(log => activeFilters.value.has(log.level))
})

function toggleFilter(level: LogLevel) {
  if (activeFilters.value.has(level)) {
    activeFilters.value.delete(level)
  } else {
    activeFilters.value.add(level)
  }
}

function clearLogs() {
  projectStore.logs = []
}

function formatTime(timestamp: string): string {
  const date = new Date(timestamp)
  return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })
}

// Auto-scroll to bottom when new logs arrive
watch(
  () => projectStore.logs.length,
  () => {
    if (logsContainer.value && uiStore.autoScroll) {
      logsContainer.value.scrollTop = logsContainer.value.scrollHeight
    }
  }
)
</script>

<style scoped>
.logs-tab {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.empty-state {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--text-muted);
  font-size: 0.875rem;
}

.logs-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--spacing-sm);
  border-bottom: 1px solid var(--border-color);
  flex-wrap: wrap;
  gap: var(--spacing-sm);
}

.log-filters {
  display: flex;
  gap: 4px;
}

.filter-btn {
  padding: 2px 8px;
  font-size: 0.65rem;
  font-weight: 600;
  text-transform: uppercase;
  background: var(--bg-tertiary);
  border: none;
  border-radius: var(--radius-sm);
  color: var(--text-muted);
  cursor: pointer;
  transition: all var(--transition-fast);
}

.filter-btn:hover {
  background: var(--bg-hover);
}

.filter-btn.active {
  color: var(--text-primary);
}

.logs-actions {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
}

.logs-count {
  font-size: 0.7rem;
  color: var(--text-muted);
}

.logs-list {
  flex: 1;
  overflow-y: auto;
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.7rem;
}

.no-logs {
  padding: var(--spacing-md);
  text-align: center;
  color: var(--text-muted);
}

.log-entry {
  display: grid;
  grid-template-columns: 70px 50px 80px 1fr;
  gap: var(--spacing-sm);
  padding: 4px var(--spacing-sm);
  border-bottom: 1px solid var(--border-color);
}

.log-entry:hover {
  background: var(--bg-hover);
}

.log-time {
  color: var(--text-muted);
}

.log-level {
  font-weight: 600;
}

.log-entry.debug .log-level { color: var(--text-muted); }
.log-entry.info .log-level { color: var(--accent-info); }
.log-entry.warning .log-level { color: var(--accent-warning); }
.log-entry.error .log-level { color: var(--accent-error); }
.log-entry.critical .log-level { color: var(--accent-error); font-weight: 700; }

.log-source {
  color: var(--accent-primary);
}

.log-message {
  white-space: pre-wrap;
  word-break: break-word;
  color: var(--text-primary);
}
</style>

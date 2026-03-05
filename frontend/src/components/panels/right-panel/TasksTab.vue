<template>
  <div class="tasks-tab">
    <div v-if="!projectStore.currentProject" class="empty-state">
      <p>Select a project to view tasks</p>
    </div>

    <template v-else>
      <div class="tasks-header">
        <span class="tasks-count">{{ tasks.length }} tasks</span>
        <div class="tasks-stats">
          <span class="stat running" v-if="runningCount > 0">
            {{ runningCount }} running
          </span>
          <span class="stat completed" v-if="completedCount > 0">
            {{ completedCount }} done
          </span>
        </div>
      </div>

      <div class="tasks-list">
        <div v-if="tasks.length === 0" class="no-tasks">
          No tasks yet
        </div>

        <div v-for="task in tasks" :key="task.id" class="task-item" :class="task.status">
          <div class="task-header">
            <span class="task-status">
              <template v-if="task.status === 'running'">
                <div class="spinner-tiny animate-spin"></div>
              </template>
              <template v-else-if="task.status === 'completed'">
                <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <polyline points="20 6 9 17 4 12"></polyline>
                </svg>
              </template>
              <template v-else-if="task.status === 'failed'">
                <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <line x1="18" y1="6" x2="6" y2="18"></line>
                  <line x1="6" y1="6" x2="18" y2="18"></line>
                </svg>
              </template>
              <template v-else>
                <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <circle cx="12" cy="12" r="10"></circle>
                </svg>
              </template>
            </span>
            <span class="task-name">{{ task.name }}</span>
            <span class="task-priority" v-if="task.priority > 0">
              P{{ task.priority }}
            </span>
          </div>

          <div v-if="task.description" class="task-description">
            {{ task.description }}
          </div>

          <div v-if="task.result" class="task-result">
            <div v-if="task.result.success" class="result-success">
              {{ task.result.output || 'Completed successfully' }}
            </div>
            <div v-else class="result-error">
              {{ task.result.error || 'Task failed' }}
            </div>
            <div v-if="task.result.artifacts?.length" class="result-artifacts">
              <span v-for="artifact in task.result.artifacts" :key="artifact" class="artifact">
                {{ artifact }}
              </span>
            </div>
          </div>

          <div class="task-meta">
            <span v-if="task.started_at" class="meta-item">
              Started: {{ formatTime(task.started_at) }}
            </span>
            <span v-if="task.completed_at" class="meta-item">
              Completed: {{ formatTime(task.completed_at) }}
            </span>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useProjectStore } from '@/stores/project'

const projectStore = useProjectStore()

const tasks = computed(() => projectStore.tasks)

const runningCount = computed(() =>
  tasks.value.filter(t => t.status === 'running').length
)

const completedCount = computed(() =>
  tasks.value.filter(t => t.status === 'completed').length
)

function formatTime(timestamp: string): string {
  const date = new Date(timestamp)
  return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
}
</script>

<style scoped>
.tasks-tab {
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

.tasks-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--spacing-sm);
  border-bottom: 1px solid var(--border-color);
}

.tasks-count {
  font-size: 0.75rem;
  color: var(--text-muted);
}

.tasks-stats {
  display: flex;
  gap: var(--spacing-sm);
}

.stat {
  font-size: 0.7rem;
  padding: 2px 6px;
  border-radius: var(--radius-sm);
}

.stat.running {
  background: rgba(59, 130, 246, 0.2);
  color: var(--accent-info);
}

.stat.completed {
  background: rgba(16, 185, 129, 0.2);
  color: var(--accent-success);
}

.tasks-list {
  flex: 1;
  overflow-y: auto;
  padding: var(--spacing-sm);
}

.no-tasks {
  color: var(--text-muted);
  font-size: 0.8rem;
  text-align: center;
  padding: var(--spacing-md);
}

.task-item {
  background: var(--bg-tertiary);
  border-radius: var(--radius-sm);
  padding: var(--spacing-sm);
  margin-bottom: var(--spacing-sm);
}

.task-item.running {
  border-left: 3px solid var(--accent-info);
}

.task-item.completed {
  border-left: 3px solid var(--accent-success);
}

.task-item.failed {
  border-left: 3px solid var(--accent-error);
}

.task-header {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
}

.task-status {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 18px;
  height: 18px;
  border-radius: 50%;
  flex-shrink: 0;
}

.task-item.running .task-status {
  background: rgba(59, 130, 246, 0.2);
  color: var(--accent-info);
}

.task-item.completed .task-status {
  background: rgba(16, 185, 129, 0.2);
  color: var(--accent-success);
}

.task-item.failed .task-status {
  background: rgba(239, 68, 68, 0.2);
  color: var(--accent-error);
}

.spinner-tiny {
  width: 12px;
  height: 12px;
  border: 2px solid transparent;
  border-top-color: currentColor;
  border-radius: 50%;
}

.task-name {
  flex: 1;
  font-size: 0.8rem;
  font-weight: 500;
}

.task-priority {
  font-size: 0.65rem;
  padding: 1px 4px;
  background: var(--bg-hover);
  border-radius: var(--radius-sm);
  color: var(--text-muted);
}

.task-description {
  font-size: 0.75rem;
  color: var(--text-secondary);
  margin-top: var(--spacing-xs);
}

.task-result {
  margin-top: var(--spacing-sm);
  padding-top: var(--spacing-sm);
  border-top: 1px solid var(--border-color);
}

.result-success {
  font-size: 0.75rem;
  color: var(--accent-success);
}

.result-error {
  font-size: 0.75rem;
  color: var(--accent-error);
}

.result-artifacts {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  margin-top: var(--spacing-xs);
}

.artifact {
  font-size: 0.65rem;
  padding: 2px 6px;
  background: var(--bg-hover);
  border-radius: var(--radius-sm);
  font-family: 'JetBrains Mono', monospace;
}

.task-meta {
  display: flex;
  gap: var(--spacing-md);
  margin-top: var(--spacing-sm);
  font-size: 0.65rem;
  color: var(--text-muted);
}
</style>

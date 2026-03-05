<template>
  <div
    class="project-item"
    :class="{ active }"
    @click="$emit('select')"
  >
    <div class="project-icon">
      <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <polyline points="16 18 22 12 16 6"></polyline>
        <polyline points="8 6 2 12 8 18"></polyline>
      </svg>
    </div>

    <div class="project-info">
      <div class="project-name">{{ project.name }}</div>
      <div class="project-meta">
        <span class="project-status" :class="`status-${project.status}`">
          {{ formatStatus(project.status) }}
        </span>
        <span class="project-time">{{ formatTime(project.updated_at) }}</span>
      </div>
    </div>

    <button class="btn btn-icon btn-ghost delete-btn" @click.stop="$emit('delete')">
      <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <polyline points="3 6 5 6 21 6"></polyline>
        <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
      </svg>
    </button>
  </div>
</template>

<script setup lang="ts">
import type { Project } from '@/types'

defineProps<{
  project: Project
  active: boolean
}>()

defineEmits<{
  (e: 'select'): void
  (e: 'delete'): void
}>()

function formatStatus(status: string): string {
  const statusMap: Record<string, string> = {
    idle: 'Idle',
    running: 'Running',
    paused: 'Paused',
    completed: 'Done',
    error: 'Error',
  }
  return statusMap[status] || status
}

function formatTime(dateStr: string): string {
  const date = new Date(dateStr)
  const now = new Date()
  const diff = now.getTime() - date.getTime()

  const minutes = Math.floor(diff / 60000)
  const hours = Math.floor(diff / 3600000)
  const days = Math.floor(diff / 86400000)

  if (minutes < 1) return 'Just now'
  if (minutes < 60) return `${minutes}m ago`
  if (hours < 24) return `${hours}h ago`
  if (days < 7) return `${days}d ago`

  return date.toLocaleDateString()
}
</script>

<style scoped>
.project-item {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  padding: var(--spacing-sm) var(--spacing-md);
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: all var(--transition-fast);
}

.project-item:hover {
  background: var(--bg-hover);
}

.project-item.active {
  background: var(--bg-active);
}

.project-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border-radius: var(--radius-md);
  background: var(--bg-tertiary);
  color: var(--accent-primary);
}

.project-item.active .project-icon {
  background: var(--accent-primary);
  color: var(--bg-primary);
}

.project-info {
  flex: 1;
  min-width: 0;
}

.project-name {
  font-weight: 500;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.project-meta {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  font-size: 0.75rem;
  color: var(--text-muted);
}

.project-status {
  padding: 1px 6px;
  border-radius: 999px;
  font-size: 0.65rem;
  text-transform: uppercase;
  font-weight: 600;
}

.status-idle {
  background: var(--bg-tertiary);
  color: var(--text-muted);
}

.status-running {
  background: rgba(59, 130, 246, 0.2);
  color: var(--accent-info);
}

.status-paused {
  background: rgba(245, 158, 11, 0.2);
  color: var(--accent-warning);
}

.status-completed {
  background: rgba(16, 185, 129, 0.2);
  color: var(--accent-success);
}

.status-error {
  background: rgba(239, 68, 68, 0.2);
  color: var(--accent-error);
}

.delete-btn {
  opacity: 0;
  transition: opacity var(--transition-fast);
}

.project-item:hover .delete-btn {
  opacity: 1;
}

.delete-btn:hover {
  color: var(--accent-error);
}
</style>

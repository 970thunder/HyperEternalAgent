<template>
  <div class="message-item" :class="[`role-${message.role}`, `type-${message.type}`]">
    <div class="message-avatar">
      <template v-if="message.role === 'user'">
        <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path>
          <circle cx="12" cy="7" r="4"></circle>
        </svg>
      </template>
      <template v-else-if="message.role === 'assistant'">
        <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M12 2a2 2 0 0 1 2 2c0 .74-.4 1.39-1 1.73V7h1a7 7 0 0 1 7 7h1a1 1 0 0 1 1 1v3a1 1 0 0 1-1 1h-1v1a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-1H2a1 1 0 0 1-1-1v-3a1 1 0 0 1 1-1h1a7 7 0 0 1 7-7h1V5.73c-.6-.34-1-.99-1-1.73a2 2 0 0 1 2-2z"></path>
          <circle cx="7.5" cy="14.5" r="1.5"></circle>
          <circle cx="16.5" cy="14.5" r="1.5"></circle>
        </svg>
      </template>
      <template v-else-if="message.role === 'agent'">
        <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <rect x="3" y="11" width="18" height="11" rx="2" ry="2"></rect>
          <path d="M7 11V7a5 5 0 0 1 10 0v4"></path>
        </svg>
      </template>
      <template v-else>
        <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <circle cx="12" cy="12" r="10"></circle>
          <line x1="12" y1="16" x2="12" y2="12"></line>
          <line x1="12" y1="8" x2="12.01" y2="8"></line>
        </svg>
      </template>
    </div>

    <div class="message-content">
      <div class="message-header">
        <span class="message-role">
          {{ getRoleLabel() }}
          <template v-if="message.metadata?.agent_name">
            ({{ message.metadata.agent_name }})
          </template>
        </span>
        <span v-if="uiStore.showTimestamps" class="message-time">
          {{ formatTime(message.created_at) }}
        </span>
      </div>

      <div class="message-body">
        <!-- Status message -->
        <div v-if="message.type === 'status'" class="status-content">
          <div class="status-icon" :class="getStatusClass()">
            <svg v-if="message.content.includes('success') || message.content.includes('complete')" xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <polyline points="20 6 9 17 4 12"></polyline>
            </svg>
            <svg v-else-if="message.content.includes('error') || message.content.includes('fail')" xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <circle cx="12" cy="12" r="10"></circle>
              <line x1="15" y1="9" x2="9" y2="15"></line>
              <line x1="9" y1="9" x2="15" y2="15"></line>
            </svg>
            <div v-else class="spinner-tiny animate-spin"></div>
          </div>
          <span>{{ message.content }}</span>
        </div>

        <!-- Code message -->
        <div v-else-if="message.type === 'code'" class="code-content">
          <pre><code>{{ message.content }}</code></pre>
          <button class="btn btn-ghost btn-sm copy-btn" @click="copyCode">
            <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
              <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
            </svg>
            Copy
          </button>
        </div>

        <!-- Command message -->
        <div v-else-if="message.type === 'command'" class="command-content">
          <div class="command-header">
            <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <polyline points="4 17 10 11 4 5"></polyline>
              <line x1="12" y1="19" x2="20" y2="19"></line>
            </svg>
            <code>{{ message.metadata?.command || message.content }}</code>
          </div>
          <div v-if="message.metadata?.exit_code !== undefined" class="command-result">
            Exit code: {{ message.metadata.exit_code }}
            <span v-if="message.metadata.duration">({{ message.metadata.duration }}ms)</span>
          </div>
        </div>

        <!-- File message -->
        <div v-else-if="message.type === 'file'" class="file-content">
          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M13 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z"></path>
            <polyline points="13 2 13 9 20 9"></polyline>
          </svg>
          <span>{{ message.metadata?.file_path || message.content }}</span>
        </div>

        <!-- Error message -->
        <div v-else-if="message.type === 'error'" class="error-content">
          {{ message.content }}
        </div>

        <!-- Action message -->
        <div v-else-if="message.type === 'action'" class="action-content">
          <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <circle cx="12" cy="12" r="10"></circle>
            <polyline points="12 6 12 12 16 14"></polyline>
          </svg>
          {{ message.content }}
        </div>

        <!-- Text message (default) -->
        <div v-else class="text-content" v-html="renderMarkdown(message.content)"></div>
      </div>

      <!-- Progress bar -->
      <div v-if="message.metadata?.progress !== undefined" class="progress-bar">
        <div class="progress-fill" :style="{ width: `${message.metadata.progress}%` }"></div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useUIStore } from '@/stores/ui'
import type { Message } from '@/types'
import { marked } from 'marked'

const props = defineProps<{
  message: Message
}>()

const uiStore = useUIStore()

function getRoleLabel(): string {
  const roleMap: Record<string, string> = {
    user: 'You',
    assistant: 'AI Assistant',
    agent: 'Agent',
    system: 'System',
  }
  return roleMap[props.message.role] || props.message.role
}

function formatTime(dateStr: string): string {
  const date = new Date(dateStr)
  return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
}

function getStatusClass(): string {
  const content = props.message.content.toLowerCase()
  if (content.includes('success') || content.includes('complete')) return 'success'
  if (content.includes('error') || content.includes('fail')) return 'error'
  return 'loading'
}

function renderMarkdown(content: string): string {
  try {
    return marked(content) as string
  } catch {
    return content
  }
}

async function copyCode() {
  await navigator.clipboard.writeText(props.message.content)
}
</script>

<style scoped>
.message-item {
  display: flex;
  gap: var(--spacing-md);
  padding: var(--spacing-md);
  border-radius: var(--radius-lg);
  animation: fadeIn 0.3s ease-out;
}

.role-user {
  background: var(--message-user-bg);
}

.role-assistant,
.role-agent {
  background: var(--message-assistant-bg);
}

.role-system {
  background: var(--message-system-bg);
}

.type-error {
  background: var(--message-error-bg);
}

.type-action {
  background: var(--message-action-bg);
}

.message-avatar {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  border-radius: var(--radius-md);
  background: var(--bg-tertiary);
  color: var(--text-secondary);
  flex-shrink: 0;
}

.role-user .message-avatar {
  background: var(--accent-primary);
  color: var(--bg-primary);
}

.message-content {
  flex: 1;
  min-width: 0;
}

.message-header {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  margin-bottom: var(--spacing-xs);
}

.message-role {
  font-weight: 600;
  font-size: 0.875rem;
}

.message-time {
  font-size: 0.75rem;
  color: var(--text-muted);
}

.message-body {
  font-size: 0.9rem;
  line-height: 1.6;
}

.text-content {
  white-space: pre-wrap;
  word-break: break-word;
}

.text-content :deep(p) {
  margin-bottom: var(--spacing-sm);
}

.text-content :deep(p:last-child) {
  margin-bottom: 0;
}

.text-content :deep(ul),
.text-content :deep(ol) {
  padding-left: var(--spacing-lg);
  margin-bottom: var(--spacing-sm);
}

.text-content :deep(code) {
  background: var(--bg-tertiary);
  padding: 2px 6px;
  border-radius: var(--radius-sm);
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.85em;
}

.text-content :deep(pre) {
  background: var(--code-bg);
  border: 1px solid var(--code-border);
  border-radius: var(--radius-md);
  padding: var(--spacing-md);
  overflow-x: auto;
  margin: var(--spacing-sm) 0;
}

.text-content :deep(pre code) {
  background: none;
  padding: 0;
}

.status-content {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
}

.status-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  border-radius: 50%;
}

.status-icon.loading {
  background: rgba(59, 130, 246, 0.2);
  color: var(--accent-info);
}

.status-icon.success {
  background: rgba(16, 185, 129, 0.2);
  color: var(--accent-success);
}

.status-icon.error {
  background: rgba(239, 68, 68, 0.2);
  color: var(--accent-error);
}

.spinner-tiny {
  width: 14px;
  height: 14px;
  border: 2px solid transparent;
  border-top-color: currentColor;
  border-radius: 50%;
}

.code-content {
  position: relative;
}

.code-content pre {
  margin: 0;
}

.copy-btn {
  position: absolute;
  top: var(--spacing-sm);
  right: var(--spacing-sm);
  padding: var(--spacing-xs) var(--spacing-sm);
  font-size: 0.75rem;
}

.command-content {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.85rem;
}

.command-header {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  padding: var(--spacing-sm);
  background: var(--code-bg);
  border-radius: var(--radius-sm);
}

.command-header code {
  background: none;
  padding: 0;
}

.command-result {
  margin-top: var(--spacing-xs);
  font-size: 0.75rem;
  color: var(--text-muted);
}

.file-content {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  padding: var(--spacing-sm);
  background: var(--bg-tertiary);
  border-radius: var(--radius-sm);
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.85rem;
}

.error-content {
  color: var(--accent-error);
  font-weight: 500;
}

.action-content {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  color: var(--accent-success);
}

.progress-bar {
  height: 3px;
  background: var(--bg-tertiary);
  border-radius: 2px;
  margin-top: var(--spacing-sm);
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: var(--accent-primary);
  transition: width var(--transition-normal);
}
</style>

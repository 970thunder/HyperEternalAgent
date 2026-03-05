<template>
  <div class="center-panel-content">
    <!-- Header -->
    <header class="panel-header" v-if="projectStore.currentProject">
      <div class="header-info">
        <h1 class="project-title">{{ projectStore.currentProject.name }}</h1>
        <span class="project-status" :class="`status-${projectStore.currentProject.status}`">
          {{ formatStatus(projectStore.currentProject.status) }}
        </span>
      </div>
      <div class="header-actions">
        <button
          v-if="projectStore.currentProject.status === 'idle'"
          class="btn btn-primary"
          @click="projectStore.startProject"
        >
          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <polygon points="5 3 19 12 5 21 5 3"></polygon>
          </svg>
          Start
        </button>
        <button
          v-if="projectStore.currentProject.status === 'running'"
          class="btn btn-secondary"
          @click="projectStore.pauseProject"
        >
          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <rect x="6" y="4" width="4" height="16"></rect>
            <rect x="14" y="4" width="4" height="16"></rect>
          </svg>
          Pause
        </button>
        <button
          v-if="projectStore.currentProject.status === 'paused'"
          class="btn btn-primary"
          @click="projectStore.startProject"
        >
          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <polygon points="5 3 19 12 5 21 5 3"></polygon>
          </svg>
          Resume
        </button>
        <button
          v-if="['running', 'paused'].includes(projectStore.currentProject.status)"
          class="btn btn-ghost"
          @click="projectStore.stopProject"
        >
          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect>
          </svg>
          Stop
        </button>
        <button class="btn btn-icon btn-ghost" @click="uiStore.openSettingsModal">
          <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <circle cx="12" cy="12" r="3"></circle>
            <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"></path>
          </svg>
        </button>
      </div>
    </header>

    <!-- Empty State -->
    <div v-if="!projectStore.currentProject" class="empty-state">
      <div class="empty-content">
        <svg xmlns="http://www.w3.org/2000/svg" width="80" height="80" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1" stroke-linecap="round" stroke-linejoin="round">
          <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
        </svg>
        <h2>Welcome to HyperEternal Agent</h2>
        <p>Your AI-powered autonomous coding assistant</p>
        <button class="btn btn-primary btn-lg" @click="uiStore.openNewProjectModal">
          <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <line x1="12" y1="5" x2="12" y2="19"></line>
            <line x1="5" y1="12" x2="19" y2="12"></line>
          </svg>
          Start New Project
        </button>
      </div>
    </div>

    <!-- Chat Area -->
    <template v-else>
      <div class="messages-container" ref="messagesContainer">
        <div class="messages">
          <MessageItem
            v-for="message in projectStore.messages"
            :key="message.id"
            :message="message"
          />
          <div v-if="isProcessing" class="typing-indicator">
            <span></span>
            <span></span>
            <span></span>
          </div>
        </div>
      </div>

      <!-- Input Area -->
      <div class="input-area">
        <div class="input-wrapper">
          <textarea
            v-model="inputMessage"
            class="message-input"
            placeholder="Describe what you want to build..."
            @keydown="handleKeydown"
            :disabled="isSending"
            rows="1"
            ref="inputRef"
          ></textarea>
          <button
            class="btn btn-primary send-btn"
            @click="sendMessage"
            :disabled="!inputMessage.trim() || isSending"
          >
            <svg v-if="!isSending" xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <line x1="22" y1="2" x2="11" y2="13"></line>
              <polygon points="22 2 15 22 11 13 2 9 22 2"></polygon>
            </svg>
            <div v-else class="spinner-small animate-spin"></div>
          </button>
        </div>
        <div class="input-hints">
          <span>Press Enter to send, Shift+Enter for new line</span>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, nextTick, watch } from 'vue'
import { useProjectStore } from '@/stores/project'
import { useUIStore } from '@/stores/ui'
import MessageItem from './MessageItem.vue'

const projectStore = useProjectStore()
const uiStore = useUIStore()

const inputMessage = ref('')
const isSending = ref(false)
const isProcessing = ref(false)
const messagesContainer = ref<HTMLElement | null>(null)
const inputRef = ref<HTMLTextAreaElement | null>(null)

function formatStatus(status: string): string {
  const statusMap: Record<string, string> = {
    idle: 'Ready',
    running: 'Running',
    paused: 'Paused',
    completed: 'Completed',
    error: 'Error',
  }
  return statusMap[status] || status
}

async function sendMessage() {
  if (!inputMessage.value.trim() || isSending.value) return

  const content = inputMessage.value.trim()
  inputMessage.value = ''
  isSending.value = true

  try {
    await projectStore.sendMessage(content)
    isProcessing.value = true
    scrollToBottom()
  } catch (e) {
    console.error('Failed to send message:', e)
  } finally {
    isSending.value = false
  }
}

function handleKeydown(e: KeyboardEvent) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    sendMessage()
  }
}

function scrollToBottom() {
  nextTick(() => {
    if (messagesContainer.value && uiStore.autoScroll) {
      messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
    }
  })
}

// Auto-scroll when new messages arrive
watch(
  () => projectStore.messages.length,
  () => {
    scrollToBottom()
  }
)

// Auto-resize textarea
watch(inputMessage, () => {
  if (inputRef.value) {
    inputRef.value.style.height = 'auto'
    inputRef.value.style.height = Math.min(inputRef.value.scrollHeight, 150) + 'px'
  }
})
</script>

<style scoped>
.center-panel-content {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--spacing-md) var(--spacing-lg);
  background: var(--bg-secondary);
  border-bottom: 1px solid var(--border-color);
}

.header-info {
  display: flex;
  align-items: center;
  gap: var(--spacing-md);
}

.project-title {
  font-size: 1.1rem;
  font-weight: 600;
}

.project-status {
  padding: 2px 10px;
  border-radius: 999px;
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
}

.status-idle { background: var(--bg-tertiary); color: var(--text-muted); }
.status-running { background: rgba(59, 130, 246, 0.2); color: var(--accent-info); }
.status-paused { background: rgba(245, 158, 11, 0.2); color: var(--accent-warning); }
.status-completed { background: rgba(16, 185, 129, 0.2); color: var(--accent-success); }
.status-error { background: rgba(239, 68, 68, 0.2); color: var(--accent-error); }

.header-actions {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
}

.empty-state {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: var(--spacing-xl);
}

.empty-content {
  text-align: center;
  max-width: 400px;
}

.empty-content svg {
  color: var(--text-muted);
  opacity: 0.3;
  margin-bottom: var(--spacing-lg);
}

.empty-content h2 {
  font-size: 1.5rem;
  margin-bottom: var(--spacing-sm);
}

.empty-content p {
  color: var(--text-secondary);
  margin-bottom: var(--spacing-lg);
}

.btn-lg {
  padding: var(--spacing-md) var(--spacing-xl);
  font-size: 1rem;
}

.messages-container {
  flex: 1;
  overflow-y: auto;
  padding: var(--spacing-md);
}

.messages {
  max-width: 900px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  gap: var(--spacing-md);
}

.typing-indicator {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: var(--spacing-md);
}

.typing-indicator span {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--accent-primary);
  animation: bounce 1.4s ease-in-out infinite;
}

.typing-indicator span:nth-child(1) { animation-delay: 0s; }
.typing-indicator span:nth-child(2) { animation-delay: 0.2s; }
.typing-indicator span:nth-child(3) { animation-delay: 0.4s; }

@keyframes bounce {
  0%, 80%, 100% { transform: scale(0.8); opacity: 0.5; }
  40% { transform: scale(1); opacity: 1; }
}

.input-area {
  padding: var(--spacing-md) var(--spacing-lg);
  background: var(--bg-secondary);
  border-top: 1px solid var(--border-color);
}

.input-wrapper {
  display: flex;
  align-items: flex-end;
  gap: var(--spacing-sm);
  max-width: 900px;
  margin: 0 auto;
}

.message-input {
  flex: 1;
  padding: var(--spacing-md);
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  color: var(--text-primary);
  font-size: 0.9rem;
  line-height: 1.5;
  resize: none;
  max-height: 150px;
  transition: border-color var(--transition-fast);
}

.message-input:focus {
  outline: none;
  border-color: var(--accent-primary);
}

.message-input::placeholder {
  color: var(--text-muted);
}

.send-btn {
  width: 44px;
  height: 44px;
  padding: 0;
  border-radius: var(--radius-md);
}

.spinner-small {
  width: 18px;
  height: 18px;
  border: 2px solid transparent;
  border-top-color: currentColor;
  border-radius: 50%;
}

.input-hints {
  max-width: 900px;
  margin: var(--spacing-sm) auto 0;
  font-size: 0.75rem;
  color: var(--text-muted);
}
</style>

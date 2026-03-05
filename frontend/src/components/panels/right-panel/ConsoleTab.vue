<template>
  <div class="console-tab">
    <div v-if="!projectStore.currentProject" class="empty-state">
      <p>Select a project to view console</p>
    </div>

    <template v-else>
      <div class="console-header">
        <span class="console-title">Terminal</span>
        <div class="console-actions">
          <button class="btn btn-ghost btn-sm" @click="clearConsole">
            <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <polyline points="3 6 5 6 21 6"></polyline>
              <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
            </svg>
          </button>
        </div>
      </div>

      <!-- Command list -->
      <div class="commands-list" ref="commandsContainer">
        <div v-if="commands.length === 0" class="no-commands">
          No commands executed yet
        </div>

        <div v-for="cmd in commands" :key="cmd.id" class="command-item">
          <div class="command-header" @click="toggleCommand(cmd.id)">
            <div class="command-info">
              <span class="command-status" :class="cmd.status">
                <template v-if="cmd.status === 'running'">
                  <div class="spinner-tiny animate-spin"></div>
                </template>
                <template v-else-if="cmd.status === 'completed'">
                  <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <polyline points="20 6 9 17 4 12"></polyline>
                  </svg>
                </template>
                <template v-else-if="cmd.status === 'failed'">
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
              <code class="command-text">{{ cmd.command }}</code>
            </div>
            <svg class="expand-icon" :class="{ expanded: expandedCommands.has(cmd.id) }" xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <polyline points="6 9 12 15 18 9"></polyline>
            </svg>
          </div>

          <div v-if="expandedCommands.has(cmd.id)" class="command-output">
            <div v-if="cmd.output.length === 0" class="no-output">
              No output
            </div>
            <div v-else class="output-lines">
              <div
                v-for="(line, index) in cmd.output"
                :key="index"
                class="output-line"
                :class="line.type"
              >
                {{ line.content }}
              </div>
            </div>
            <div v-if="cmd.exit_code !== undefined" class="exit-code">
              Exit code: {{ cmd.exit_code }}
            </div>
          </div>
        </div>
      </div>

      <!-- Command input -->
      <div class="command-input">
        <div class="input-wrapper">
          <span class="prompt">$</span>
          <input
            v-model="commandInput"
            type="text"
            class="input"
            placeholder="Enter command..."
            @keydown.enter="executeCommand"
            :disabled="isExecuting"
          />
        </div>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useProjectStore } from '@/stores/project'

const projectStore = useProjectStore()

const commandInput = ref('')
const isExecuting = ref(false)
const expandedCommands = ref(new Set<string>())

const commands = computed(() => projectStore.commands)

function toggleCommand(id: string) {
  if (expandedCommands.value.has(id)) {
    expandedCommands.value.delete(id)
  } else {
    expandedCommands.value.add(id)
  }
}

function clearConsole() {
  // Keep only running commands
  projectStore.commands = projectStore.commands.filter(c => c.status === 'running')
}

async function executeCommand() {
  if (!commandInput.value.trim() || isExecuting.value) return

  const command = commandInput.value.trim()
  commandInput.value = ''
  isExecuting.value = true

  try {
    const cmd = await projectStore.executeCommand(command)
    expandedCommands.value.add(cmd.id)
  } catch (e) {
    console.error('Failed to execute command:', e)
  } finally {
    isExecuting.value = false
  }
}
</script>

<style scoped>
.console-tab {
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

.console-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--spacing-sm);
  border-bottom: 1px solid var(--border-color);
}

.console-title {
  font-size: 0.75rem;
  font-weight: 600;
  color: var(--text-secondary);
}

.commands-list {
  flex: 1;
  overflow-y: auto;
  padding: var(--spacing-sm);
}

.no-commands {
  color: var(--text-muted);
  font-size: 0.8rem;
  text-align: center;
  padding: var(--spacing-md);
}

.command-item {
  margin-bottom: var(--spacing-sm);
  border-radius: var(--radius-sm);
  background: var(--bg-tertiary);
  overflow: hidden;
}

.command-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--spacing-sm);
  cursor: pointer;
}

.command-header:hover {
  background: var(--bg-hover);
}

.command-info {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  flex: 1;
  min-width: 0;
}

.command-status {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 18px;
  height: 18px;
  border-radius: 50%;
  flex-shrink: 0;
}

.command-status.running {
  background: rgba(59, 130, 246, 0.2);
  color: var(--accent-info);
}

.command-status.completed {
  background: rgba(16, 185, 129, 0.2);
  color: var(--accent-success);
}

.command-status.failed, .command-status.killed {
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

.command-text {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.75rem;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.expand-icon {
  color: var(--text-muted);
  transition: transform var(--transition-fast);
}

.expand-icon.expanded {
  transform: rotate(180deg);
}

.command-output {
  border-top: 1px solid var(--border-color);
  background: var(--code-bg);
}

.no-output {
  padding: var(--spacing-sm);
  font-size: 0.75rem;
  color: var(--text-muted);
}

.output-lines {
  max-height: 200px;
  overflow-y: auto;
  padding: var(--spacing-sm);
}

.output-line {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.7rem;
  line-height: 1.5;
  white-space: pre-wrap;
  word-break: break-all;
}

.output-line.stderr {
  color: var(--accent-error);
}

.exit-code {
  padding: var(--spacing-xs) var(--spacing-sm);
  font-size: 0.7rem;
  color: var(--text-muted);
  border-top: 1px solid var(--border-color);
}

.command-input {
  padding: var(--spacing-sm);
  border-top: 1px solid var(--border-color);
  background: var(--bg-secondary);
}

.input-wrapper {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  padding: 0 var(--spacing-sm);
}

.prompt {
  color: var(--accent-success);
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.8rem;
}

.input-wrapper .input {
  border: none;
  background: transparent;
  padding: var(--spacing-sm) 0;
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.8rem;
}

.input-wrapper .input:focus {
  outline: none;
}
</style>

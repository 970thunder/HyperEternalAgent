<template>
  <div class="modal-overlay" @click.self="close">
    <div class="modal-content">
      <div class="modal-header">
        <h3>Create New Project</h3>
        <button class="btn btn-icon btn-ghost" @click="close">
          <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <line x1="18" y1="6" x2="6" y2="18"></line>
            <line x1="6" y1="6" x2="18" y2="18"></line>
          </svg>
        </button>
      </div>

      <form @submit.prevent="handleSubmit" class="modal-body">
        <div class="form-group">
          <label for="name">Project Name</label>
          <input
            id="name"
            v-model="form.name"
            type="text"
            class="input"
            placeholder="My Awesome Project"
            required
            ref="nameInput"
          />
        </div>

        <div class="form-group">
          <label for="description">Description (optional)</label>
          <textarea
            id="description"
            v-model="form.description"
            class="input"
            placeholder="Describe what you want to build..."
            rows="3"
          ></textarea>
        </div>

        <div class="form-group">
          <label>Project Type</label>
          <div class="project-types">
            <button
              type="button"
              v-for="type in projectTypes"
              :key="type.id"
              class="type-btn"
              :class="{ active: form.type === type.id }"
              @click="form.type = type.id"
            >
              <span class="type-icon">{{ type.icon }}</span>
              <span class="type-name">{{ type.name }}</span>
            </button>
          </div>
        </div>
      </form>

      <div class="modal-footer">
        <button type="button" class="btn btn-secondary" @click="close">
          Cancel
        </button>
        <button
          type="button"
          class="btn btn-primary"
          @click="handleSubmit"
          :disabled="!form.name.trim() || isCreating"
        >
          <div v-if="isCreating" class="spinner-tiny animate-spin"></div>
          <span v-else>Create Project</span>
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { useProjectStore } from '@/stores/project'
import { useUIStore } from '@/stores/ui'

const projectStore = useProjectStore()
const uiStore = useUIStore()

const nameInput = ref<HTMLInputElement | null>(null)
const isCreating = ref(false)

const form = reactive({
  name: '',
  description: '',
  type: 'web-app',
})

const projectTypes = [
  { id: 'web-app', name: 'Web App', icon: '🌐' },
  { id: 'api', name: 'API', icon: '🔌' },
  { id: 'cli', name: 'CLI Tool', icon: '💻' },
  { id: 'library', name: 'Library', icon: '📦' },
  { id: 'script', name: 'Script', icon: '📜' },
  { id: 'other', name: 'Other', icon: '🚀' },
]

onMounted(() => {
  nameInput.value?.focus()
})

async function handleSubmit() {
  if (!form.name.trim() || isCreating.value) return

  isCreating.value = true
  try {
    const project = await projectStore.createProject(
      form.name.trim(),
      form.description.trim() || undefined
    )
    await projectStore.selectProject(project.id)
    close()
  } catch (e) {
    console.error('Failed to create project:', e)
  } finally {
    isCreating.value = false
  }
}

function close() {
  uiStore.closeNewProjectModal()
  form.name = ''
  form.description = ''
  form.type = 'web-app'
}
</script>

<style scoped>
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.6);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  animation: fadeIn 0.2s ease-out;
}

.modal-content {
  background: var(--bg-secondary);
  border-radius: var(--radius-lg);
  width: 100%;
  max-width: 480px;
  box-shadow: var(--shadow-lg);
  animation: slideUp 0.3s ease-out;
}

@keyframes slideUp {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--spacing-md) var(--spacing-lg);
  border-bottom: 1px solid var(--border-color);
}

.modal-header h3 {
  font-size: 1.1rem;
}

.modal-body {
  padding: var(--spacing-lg);
}

.form-group {
  margin-bottom: var(--spacing-md);
}

.form-group:last-child {
  margin-bottom: 0;
}

.form-group label {
  display: block;
  font-size: 0.875rem;
  font-weight: 500;
  margin-bottom: var(--spacing-sm);
  color: var(--text-secondary);
}

.form-group textarea.input {
  resize: vertical;
  min-height: 80px;
}

.project-types {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: var(--spacing-sm);
}

.type-btn {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--spacing-xs);
  padding: var(--spacing-md);
  background: var(--bg-tertiary);
  border: 2px solid transparent;
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: all var(--transition-fast);
}

.type-btn:hover {
  background: var(--bg-hover);
  border-color: var(--border-light);
}

.type-btn.active {
  background: var(--bg-active);
  border-color: var(--accent-primary);
}

.type-icon {
  font-size: 1.5rem;
}

.type-name {
  font-size: 0.75rem;
  color: var(--text-secondary);
}

.type-btn.active .type-name {
  color: var(--text-primary);
}

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: var(--spacing-sm);
  padding: var(--spacing-md) var(--spacing-lg);
  border-top: 1px solid var(--border-color);
}

.spinner-tiny {
  width: 16px;
  height: 16px;
  border: 2px solid transparent;
  border-top-color: currentColor;
  border-radius: 50%;
}
</style>

<template>
  <div class="files-tab">
    <div v-if="!projectStore.currentProject" class="empty-state">
      <p>Select a project to view files</p>
    </div>

    <template v-else>
      <div class="files-header">
        <span class="files-count">{{ files.length }} files</span>
        <button class="btn btn-ghost btn-sm" @click="refreshFiles">
          <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <polyline points="23 4 23 10 17 10"></polyline>
            <polyline points="1 20 1 14 7 14"></polyline>
            <path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"></path>
          </svg>
        </button>
      </div>

      <div class="files-tree">
        <FileTreeNodeComponent
          v-for="node in projectStore.projectFilesTree"
          :key="node.id"
          :node="node"
          :depth="0"
          @select="selectFile"
        />
      </div>

      <!-- File preview -->
      <div v-if="selectedFile" class="file-preview">
        <div class="preview-header">
          <span class="file-name">{{ selectedFile.name }}</span>
          <button class="btn btn-ghost btn-sm" @click="selectedFile = null">
            <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <line x1="18" y1="6" x2="6" y2="18"></line>
              <line x1="6" y1="6" x2="18" y2="18"></line>
            </svg>
          </button>
        </div>
        <pre class="preview-content"><code>{{ selectedFile.content || '(binary or empty file)' }}</code></pre>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useProjectStore } from '@/stores/project'
import type { ProjectFile } from '@/types'
import FileTreeNodeComponent from './FileTreeNode.vue'

const projectStore = useProjectStore()

const selectedFile = ref<ProjectFile | null>(null)

const files = computed(() => projectStore.files)

async function refreshFiles() {
  await projectStore.fetchFiles()
}

function selectFile(file: ProjectFile) {
  selectedFile.value = file
}
</script>

<style scoped>
.files-tab {
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

.files-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--spacing-sm);
  border-bottom: 1px solid var(--border-color);
}

.files-count {
  font-size: 0.75rem;
  color: var(--text-muted);
}

.files-tree {
  flex: 1;
  overflow-y: auto;
  padding: var(--spacing-sm);
}

.file-preview {
  border-top: 1px solid var(--border-color);
  max-height: 200px;
  display: flex;
  flex-direction: column;
}

.preview-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--spacing-sm);
  background: var(--bg-tertiary);
}

.file-name {
  font-size: 0.75rem;
  font-weight: 500;
  font-family: 'JetBrains Mono', monospace;
}

.preview-content {
  flex: 1;
  overflow: auto;
  margin: 0;
  padding: var(--spacing-sm);
  font-size: 0.7rem;
  background: var(--code-bg);
  border: none;
  border-radius: 0;
}
</style>

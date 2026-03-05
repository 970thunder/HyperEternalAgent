<template>
  <div class="file-tree-node">
    <div
      class="node-content"
      :style="{ paddingLeft: `${depth * 12 + 8}px` }"
      @click="handleClick"
    >
      <!-- Folder toggle -->
      <span v-if="node.type === 'directory'" class="toggle-icon" @click.stop="toggleExpanded">
        <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <polyline :points="expanded ? '6 9 12 15 18 9' : '9 18 15 12 9 6'"></polyline>
        </svg>
      </span>
      <span v-else class="toggle-icon placeholder"></span>

      <!-- Icon -->
      <span class="node-icon" :class="node.type">
        <template v-if="node.type === 'directory'">
          <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"></path>
          </svg>
        </template>
        <template v-else>
          <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M13 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z"></path>
            <polyline points="13 2 13 9 20 9"></polyline>
          </svg>
        </template>
      </span>

      <!-- Name -->
      <span class="node-name">{{ node.name }}</span>
    </div>

    <!-- Children -->
    <div v-if="node.type === 'directory' && expanded && node.children" class="node-children">
      <FileTreeNode
        v-for="child in node.children"
        :key="child.id"
        :node="child"
        :depth="depth + 1"
        @select="$emit('select', $event)"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import type { FileTreeNode as IFileTreeNode } from '@/stores/project'
import type { ProjectFile } from '@/types'

const props = defineProps<{
  node: IFileTreeNode
  depth: number
}>()

const emit = defineEmits<{
  (e: 'select', file: ProjectFile): void
}>()

const expanded = ref(false)

function toggleExpanded() {
  expanded.value = !expanded.value
}

function handleClick() {
  if (props.node.type === 'directory') {
    toggleExpanded()
  } else if (props.node.file) {
    emit('select', props.node.file)
  }
}
</script>

<style scoped>
.file-tree-node {
  user-select: none;
}

.node-content {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 4px 8px;
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: background var(--transition-fast);
}

.node-content:hover {
  background: var(--bg-hover);
}

.toggle-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 16px;
  height: 16px;
  color: var(--text-muted);
}

.toggle-icon.placeholder {
  visibility: hidden;
}

.node-icon {
  display: flex;
  align-items: center;
  color: var(--text-muted);
}

.node-icon.directory {
  color: var(--accent-warning);
}

.node-name {
  font-size: 0.8rem;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.node-children {
  /* Children inherit styling */
}
</style>

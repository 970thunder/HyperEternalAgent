<template>
  <div class="left-panel-content">
    <!-- Header -->
    <div class="panel-header">
      <template v-if="!uiStore.leftPanelCollapsed">
        <h2 class="panel-title">Projects</h2>
        <button class="btn btn-icon btn-ghost" @click="uiStore.openNewProjectModal">
          <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <line x1="12" y1="5" x2="12" y2="19"></line>
            <line x1="5" y1="12" x2="19" y2="12"></line>
          </svg>
        </button>
      </template>
      <button class="btn btn-icon btn-ghost collapse-btn" @click="uiStore.toggleLeftPanel">
        <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <template v-if="uiStore.leftPanelCollapsed">
            <polyline points="9 18 15 12 9 6"></polyline>
          </template>
          <template v-else>
            <polyline points="15 18 9 12 15 6"></polyline>
          </template>
        </svg>
      </button>
    </div>

    <!-- Project List -->
    <div v-if="!uiStore.leftPanelCollapsed" class="project-list">
      <div v-if="projectStore.isLoading" class="loading-state">
        <div class="spinner animate-spin"></div>
      </div>

      <div v-else-if="projectStore.projects.length === 0" class="empty-state">
        <svg xmlns="http://www.w3.org/2000/svg" width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
          <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"></path>
        </svg>
        <p>No projects yet</p>
        <button class="btn btn-primary" @click="uiStore.openNewProjectModal">
          Create Project
        </button>
      </div>

      <div v-else class="projects">
        <ProjectItem
          v-for="project in projectStore.sortedProjects"
          :key="project.id"
          :project="project"
          :active="projectStore.currentProject?.id === project.id"
          @select="selectProject(project.id)"
          @delete="deleteProject(project.id)"
        />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useProjectStore } from '@/stores/project'
import { useUIStore } from '@/stores/ui'
import ProjectItem from './ProjectItem.vue'

const projectStore = useProjectStore()
const uiStore = useUIStore()

async function selectProject(projectId: string) {
  await projectStore.selectProject(projectId)
}

async function deleteProject(projectId: string) {
  if (confirm('Are you sure you want to delete this project?')) {
    await projectStore.deleteProject(projectId)
  }
}
</script>

<style scoped>
.left-panel-content {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--spacing-md);
  border-bottom: 1px solid var(--border-color);
  min-height: 56px;
}

.panel-title {
  font-size: 1rem;
  font-weight: 600;
}

.collapse-btn {
  margin-left: auto;
}

.project-list {
  flex: 1;
  overflow-y: auto;
  padding: var(--spacing-sm);
}

.loading-state {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: var(--spacing-xl);
}

.spinner {
  width: 24px;
  height: 24px;
  border: 2px solid var(--border-color);
  border-top-color: var(--accent-primary);
  border-radius: 50%;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: var(--spacing-xl);
  text-align: center;
  color: var(--text-muted);
}

.empty-state svg {
  margin-bottom: var(--spacing-md);
  opacity: 0.5;
}

.empty-state p {
  margin-bottom: var(--spacing-md);
}

.projects {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-xs);
}
</style>

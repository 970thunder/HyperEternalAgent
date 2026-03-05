import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { Project, Message, ProjectFile, Task, LogEntry, CommandExecution } from '@/types'
import api from '@/services/api'
import wsService from '@/services/websocket'

export const useProjectStore = defineStore('project', () => {
  // State
  const projects = ref<Project[]>([])
  const currentProject = ref<Project | null>(null)
  const messages = ref<Message[]>([])
  const files = ref<ProjectFile[]>([])
  const tasks = ref<Task[]>([])
  const logs = ref<LogEntry[]>([])
  const commands = ref<CommandExecution[]>([])
  const isLoading = ref(false)
  const error = ref<string | null>(null)

  // Computed
  const sortedProjects = computed(() =>
    [...projects.value].sort(
      (a, b) => new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime()
    )
  )

  const projectFilesTree = computed(() => {
    return buildFileTree(files.value)
  })

  const runningCommands = computed(() =>
    commands.value.filter((c) => c.status === 'running')
  )

  // Actions
  async function fetchProjects() {
    isLoading.value = true
    error.value = null
    try {
      projects.value = await api.getProjects()
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to fetch projects'
    } finally {
      isLoading.value = false
    }
  }

  async function selectProject(projectId: string) {
    isLoading.value = true
    error.value = null
    try {
      currentProject.value = await api.getProject(projectId)
      messages.value = currentProject.value.messages || []
      files.value = currentProject.value.files || []
      tasks.value = currentProject.value.tasks || []

      // Fetch additional data
      const [logsData, commandsData] = await Promise.all([
        api.getLogs(projectId, { limit: 100 }),
        api.getCommands(projectId),
      ])
      logs.value = logsData
      commands.value = commandsData

      // Connect WebSocket for this project
      await wsService.connect(projectId)
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to load project'
    } finally {
      isLoading.value = false
    }
  }

  async function createProject(name: string, description?: string) {
    isLoading.value = true
    error.value = null
    try {
      const project = await api.createProject({ name, description })
      projects.value.push(project)
      return project
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to create project'
      throw e
    } finally {
      isLoading.value = false
    }
  }

  async function deleteProject(projectId: string) {
    try {
      await api.deleteProject(projectId)
      projects.value = projects.value.filter((p) => p.id !== projectId)
      if (currentProject.value?.id === projectId) {
        currentProject.value = null
        messages.value = []
        files.value = []
        tasks.value = []
        logs.value = []
        commands.value = []
      }
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to delete project'
      throw e
    }
  }

  async function sendMessage(content: string) {
    if (!currentProject.value) return

    try {
      const message = await api.sendMessage(currentProject.value.id, content)
      messages.value.push(message)
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to send message'
      throw e
    }
  }

  async function fetchFiles() {
    if (!currentProject.value) return

    try {
      files.value = await api.getFiles(currentProject.value.id)
    } catch (e) {
      console.error('Failed to fetch files:', e)
    }
  }

  async function fetchLogs() {
    if (!currentProject.value) return

    try {
      logs.value = await api.getLogs(currentProject.value.id, { limit: 100 })
    } catch (e) {
      console.error('Failed to fetch logs:', e)
    }
  }

  async function fetchCommands() {
    if (!currentProject.value) return

    try {
      commands.value = await api.getCommands(currentProject.value.id)
    } catch (e) {
      console.error('Failed to fetch commands:', e)
    }
  }

  async function startProject() {
    if (!currentProject.value) return
    await api.startProject(currentProject.value.id)
    currentProject.value.status = 'running'
  }

  async function pauseProject() {
    if (!currentProject.value) return
    await api.pauseProject(currentProject.value.id)
    currentProject.value.status = 'paused'
  }

  async function stopProject() {
    if (!currentProject.value) return
    await api.stopProject(currentProject.value.id)
    currentProject.value.status = 'idle'
  }

  async function executeCommand(command: string) {
    if (!currentProject.value) throw new Error('No project selected')
    return await api.executeCommand(currentProject.value.id, command)
  }

  // WebSocket event handlers
  function setupWebSocketHandlers() {
    wsService.subscribe('message_created', (data: Message) => {
      if (currentProject.value?.id === data.project_id) {
        messages.value.push(data)
      }
    })

    wsService.subscribe('message_stream', (data: { id: string; content: string }) => {
      const msg = messages.value.find((m) => m.id === data.id)
      if (msg) {
        msg.content += data.content
      }
    })

    wsService.subscribe('file_created', (data: ProjectFile) => {
      if (currentProject.value?.id === data.project_id) {
        files.value.push(data)
      }
    })

    wsService.subscribe('file_updated', (data: ProjectFile) => {
      const index = files.value.findIndex((f) => f.id === data.id)
      if (index !== -1) {
        files.value[index] = data
      }
    })

    wsService.subscribe('file_deleted', (data: { id: string }) => {
      files.value = files.value.filter((f) => f.id !== data.id)
    })

    wsService.subscribe('log_created', (data: LogEntry) => {
      if (currentProject.value?.id === data.project_id) {
        logs.value.push(data)
        // Keep only last 500 logs
        if (logs.value.length > 500) {
          logs.value = logs.value.slice(-500)
        }
      }
    })

    wsService.subscribe('command_started', (data: CommandExecution) => {
      if (currentProject.value?.id === data.project_id) {
        commands.value.push(data)
      }
    })

    wsService.subscribe('command_output', (data: { id: string; output: { content: string; type: string; timestamp: string } }) => {
      const cmd = commands.value.find((c) => c.id === data.id)
      if (cmd) {
        cmd.output.push(data.output as CommandExecution['output'][0])
      }
    })

    wsService.subscribe('command_completed', (data: CommandExecution) => {
      const index = commands.value.findIndex((c) => c.id === data.id)
      if (index !== -1) {
        commands.value[index] = data
      }
    })

    wsService.subscribe('task_updated', (data: Task) => {
      const index = tasks.value.findIndex((t) => t.id === data.id)
      if (index !== -1) {
        tasks.value[index] = data
      } else {
        tasks.value.push(data)
      }
    })

    wsService.subscribe('project_updated', (data: Project) => {
      const index = projects.value.findIndex((p) => p.id === data.id)
      if (index !== -1) {
        projects.value[index] = data
      }
      if (currentProject.value?.id === data.id) {
        currentProject.value = data
      }
    })
  }

  return {
    // State
    projects,
    currentProject,
    messages,
    files,
    tasks,
    logs,
    commands,
    isLoading,
    error,
    // Computed
    sortedProjects,
    projectFilesTree,
    runningCommands,
    // Actions
    fetchProjects,
    selectProject,
    createProject,
    deleteProject,
    sendMessage,
    fetchFiles,
    fetchLogs,
    fetchCommands,
    startProject,
    pauseProject,
    stopProject,
    executeCommand,
    setupWebSocketHandlers,
  }
})

// Helper function to build file tree
function buildFileTree(files: ProjectFile[]): FileTreeNode[] {
  const root: FileTreeNode[] = []
  const map = new Map<string, FileTreeNode>()

  // Sort files by path
  const sortedFiles = [...files].sort((a, b) => a.path.localeCompare(b.path))

  for (const file of sortedFiles) {
    const parts = file.path.split('/').filter(Boolean)
    let current = root
    let currentPath = ''

    for (let i = 0; i < parts.length; i++) {
      const part = parts[i] as string
      currentPath += '/' + part
      const isFile = i === parts.length - 1 && file.type === 'file'

      let node = map.get(currentPath)
      if (!node) {
        const newNode: FileTreeNode = {
          id: file.id,
          name: part,
          path: currentPath,
          type: isFile ? 'file' : 'directory',
          children: isFile ? undefined : [],
          file: isFile ? file : undefined,
        }
        node = newNode
        map.set(currentPath, node)
        current.push(node)
      }

      if (!isFile && node.children) {
        current = node.children
      }
    }
  }

  return root
}

export interface FileTreeNode {
  id: string
  name: string
  path: string
  type: 'file' | 'directory'
  children?: FileTreeNode[]
  file?: ProjectFile
}

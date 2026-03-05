import axios, { type AxiosInstance } from 'axios'
import type {
  Project,
  Message,
  ProjectFile,
  Task,
  LogEntry,
  CommandExecution,
  ApiResponse,
  PaginatedResponse,
} from '@/types'

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api'

class ApiService {
  private client: AxiosInstance

  constructor() {
    this.client = axios.create({
      baseURL: API_BASE_URL,
      headers: {
        'Content-Type': 'application/json',
      },
    })

    // Request interceptor
    this.client.interceptors.request.use(
      (config) => {
        // Add auth token if available
        const token = localStorage.getItem('token')
        if (token) {
          config.headers.Authorization = `Bearer ${token}`
        }
        return config
      },
      (error) => Promise.reject(error)
    )

    // Response interceptor
    this.client.interceptors.response.use(
      (response) => response,
      (error) => {
        console.error('API Error:', error.response?.data || error.message)
        return Promise.reject(error)
      }
    )
  }

  // Project endpoints
  async getProjects(): Promise<Project[]> {
    const response = await this.client.get<ApiResponse<Project[]>>('/projects')
    return response.data.data || []
  }

  async getProject(id: string): Promise<Project> {
    const response = await this.client.get<ApiResponse<Project>>(`/projects/${id}`)
    if (!response.data.data) throw new Error('Project not found')
    return response.data.data
  }

  async createProject(data: { name: string; description?: string }): Promise<Project> {
    const response = await this.client.post<ApiResponse<Project>>('/projects', data)
    if (!response.data.data) throw new Error('Failed to create project')
    return response.data.data
  }

  async updateProject(id: string, data: Partial<Project>): Promise<Project> {
    const response = await this.client.put<ApiResponse<Project>>(`/projects/${id}`, data)
    if (!response.data.data) throw new Error('Failed to update project')
    return response.data.data
  }

  async deleteProject(id: string): Promise<void> {
    await this.client.delete(`/projects/${id}`)
  }

  // Message endpoints
  async getMessages(
    projectId: string,
    page = 1,
    pageSize = 50
  ): Promise<PaginatedResponse<Message>> {
    const response = await this.client.get<PaginatedResponse<Message>>(
      `/projects/${projectId}/messages`,
      { params: { page, page_size: pageSize } }
    )
    return response.data
  }

  async sendMessage(projectId: string, content: string): Promise<Message> {
    const response = await this.client.post<ApiResponse<Message>>(
      `/projects/${projectId}/messages`,
      { content, role: 'user' }
    )
    if (!response.data.data) throw new Error('Failed to send message')
    return response.data.data
  }

  // File endpoints
  async getFiles(projectId: string): Promise<ProjectFile[]> {
    const response = await this.client.get<ApiResponse<ProjectFile[]>>(
      `/projects/${projectId}/files`
    )
    return response.data.data || []
  }

  async getFile(projectId: string, fileId: string): Promise<ProjectFile> {
    const response = await this.client.get<ApiResponse<ProjectFile>>(
      `/projects/${projectId}/files/${fileId}`
    )
    if (!response.data.data) throw new Error('File not found')
    return response.data.data
  }

  async createFile(
    projectId: string,
    data: { path: string; content?: string }
  ): Promise<ProjectFile> {
    const response = await this.client.post<ApiResponse<ProjectFile>>(
      `/projects/${projectId}/files`,
      data
    )
    if (!response.data.data) throw new Error('Failed to create file')
    return response.data.data
  }

  async updateFile(
    projectId: string,
    fileId: string,
    data: { content: string }
  ): Promise<ProjectFile> {
    const response = await this.client.put<ApiResponse<ProjectFile>>(
      `/projects/${projectId}/files/${fileId}`,
      data
    )
    if (!response.data.data) throw new Error('Failed to update file')
    return response.data.data
  }

  async deleteFile(projectId: string, fileId: string): Promise<void> {
    await this.client.delete(`/projects/${projectId}/files/${fileId}`)
  }

  // Task endpoints
  async getTasks(projectId: string): Promise<Task[]> {
    const response = await this.client.get<ApiResponse<Task[]>>(
      `/projects/${projectId}/tasks`
    )
    return response.data.data || []
  }

  async getTask(projectId: string, taskId: string): Promise<Task> {
    const response = await this.client.get<ApiResponse<Task>>(
      `/projects/${projectId}/tasks/${taskId}`
    )
    if (!response.data.data) throw new Error('Task not found')
    return response.data.data
  }

  // Log endpoints
  async getLogs(
    projectId: string,
    params?: { level?: string; limit?: number }
  ): Promise<LogEntry[]> {
    const response = await this.client.get<ApiResponse<LogEntry[]>>(
      `/projects/${projectId}/logs`,
      { params }
    )
    return response.data.data || []
  }

  // Command endpoints
  async getCommands(projectId: string): Promise<CommandExecution[]> {
    const response = await this.client.get<ApiResponse<CommandExecution[]>>(
      `/projects/${projectId}/commands`
    )
    return response.data.data || []
  }

  async executeCommand(projectId: string, command: string): Promise<CommandExecution> {
    const response = await this.client.post<ApiResponse<CommandExecution>>(
      `/projects/${projectId}/commands`,
      { command }
    )
    if (!response.data.data) throw new Error('Failed to execute command')
    return response.data.data
  }

  async killCommand(projectId: string, commandId: string): Promise<void> {
    await this.client.post(`/projects/${projectId}/commands/${commandId}/kill`)
  }

  // Control endpoints
  async startProject(projectId: string): Promise<void> {
    await this.client.post(`/projects/${projectId}/start`)
  }

  async pauseProject(projectId: string): Promise<void> {
    await this.client.post(`/projects/${projectId}/pause`)
  }

  async resumeProject(projectId: string): Promise<void> {
    await this.client.post(`/projects/${projectId}/resume`)
  }

  async stopProject(projectId: string): Promise<void> {
    await this.client.post(`/projects/${projectId}/stop`)
  }
}

export const api = new ApiService()
export default api

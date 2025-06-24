const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:3000'
fetch(`${API_BASE_URL}/api/v1/meetings/summaries`)
export interface MeetingSummary {
  id: string
  title: string
  summary: string
  tasks: Array<{
    id: string
    text: string
    completed: boolean
  }>
  createdAt: string
}

export interface AuthResponse {
  status: string
  message: string
  needs_reauthentication?: boolean
  missing_scopes?: string[]
  reauthentication_url?: string
}

class ApiService {
  private baseUrl: string

  constructor() {
    this.baseUrl = API_BASE_URL
  }

  private async request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
    const url = `${this.baseUrl}${endpoint}`
    
    const config: RequestInit = {
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
      ...options,
    }

    try {
      const response = await fetch(url, config)
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }
      
      return await response.json()
    } catch (error) {
      console.error('API request failed:', error)
      throw error
    }
  }

  // Get all meeting summaries
  async getSummaries(): Promise<MeetingSummary[]> {
    return this.request<MeetingSummary[]>('/api/v1/meetings/summaries')
  }

  // Get a specific meeting summary
  async getSummary(id: string): Promise<MeetingSummary> {
    return this.request<MeetingSummary>(`/api/v1/meetings/summaries/${id}`)
  }

  // Check user authentication status
  async checkAuth(): Promise<AuthResponse> {
    return this.request<AuthResponse>('/api/v1/auth/check-permissions')
  }

  // Get OAuth URL for Google authentication
  getGoogleAuthUrl(): string {
    return `${this.baseUrl}/api/v1/auth/google`
  }

  // Get OAuth restart URL
  getGoogleAuthRestartUrl(): string {
    return `${this.baseUrl}/api/v1/auth/restart`
  }

  // Check if user is authenticated (simple check)
  async isAuthenticated(): Promise<boolean> {
    try {
      const response = await this.checkAuth()
      return response.status === 'ok'
    } catch (error) {
      return false
    }
  }
}

export const apiService = new ApiService() 
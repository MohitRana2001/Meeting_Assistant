const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

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

export interface CalendarEvent {
  id: string
  title: string
  start: string
  end: string
  attendees?: number
  meetingType?: string
  hasRecording?: boolean
}

class ApiService {
  private baseUrl: string

  constructor() {
    this.baseUrl = API_BASE_URL
  }

  private getAuthHeaders(): Record<string, string> {
    const token = localStorage.getItem('auth_token');
    return token ? { 'Authorization': `Bearer ${token}` } : {};
  }

  private async request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
    const url = `${this.baseUrl}${endpoint}`
    
    const config: RequestInit = {
      headers: {
        'Content-Type': 'application/json',
        ...this.getAuthHeaders(),
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

  // Update task completion status
  async updateTaskStatus(summaryId: string, taskId: string, completed: boolean): Promise<{ success: boolean; message?: string }> {
    try {
      const response = await this.request<{ success: boolean; message?: string }>(
        `/api/v1/meetings/summaries/${summaryId}/tasks/${taskId}`,
        {
          method: 'PATCH',
          body: JSON.stringify({ task_id: taskId, completed })
        }
      );
      return response;
    } catch (error) {
      console.error('Failed to update task status:', error);
      return { success: false, message: 'Failed to update task status' };
    }
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
      const token = localStorage.getItem('auth_token');
      if (!token) return false;
      
      const response = await this.checkAuth()
      return response.status === 'ok'
    } catch (error) {
      return false
    }
  }

  // Google Tasks Integration
  async syncTasksToGoogle(summaryId: string): Promise<{ success: boolean; taskListUrl?: string }> {
    try {
      const response = await this.request<{ success: boolean; taskListUrl?: string }>(
        `/api/v1/tasks/sync/${summaryId}`, 
        { method: 'POST' }
      );
      return response;
    } catch (error) {
      console.error('Failed to sync tasks to Google:', error);
      return { success: false };
    }
  }

  // Google Calendar Integration
  async getCalendarEvents(): Promise<CalendarEvent[]> {
    try {
      return await this.request<CalendarEvent[]>('/api/v1/calendar/events');
    } catch (error) {
      console.error('Failed to get calendar events:', error);
      return [];
    }
  }

  async createCalendarEvent(eventData: Partial<CalendarEvent>): Promise<{ success: boolean; eventId?: string }> {
    try {
      const response = await this.request<{ success: boolean; eventId?: string }>(
        '/api/v1/calendar/events',
        {
          method: 'POST',
          body: JSON.stringify(eventData)
        }
      );
      return response;
    } catch (error) {
      console.error('Failed to create calendar event:', error);
      return { success: false };
    }
  }

  // Settings and Account Management
  async refreshAuthToken(): Promise<{ success: boolean; message?: string }> {
    try {
      const response = await this.request<{ success: boolean; message?: string }>(
        '/api/v1/auth/refresh',
        { method: 'POST' }
      );
      return response;
    } catch (error) {
      console.error('Failed to refresh auth token:', error);
      return { success: false, message: 'Failed to refresh token' };
    }
  }

  async deleteAccount(): Promise<{ success: boolean; message?: string }> {
    try {
      const response = await this.request<{ success: boolean; message?: string }>(
        '/api/v1/auth/delete-account',
        { method: 'DELETE' }
      );
      return response;
    } catch (error) {
      console.error('Failed to delete account:', error);
      return { success: false, message: 'Failed to delete account' };
    }
  }

  async exportUserData(): Promise<Blob> {
    try {
      const response = await fetch(`${this.baseUrl}/api/v1/data/export`, {
        headers: this.getAuthHeaders(),
      });
      
      if (!response.ok) {
        throw new Error('Failed to export data');
      }
      
      return await response.blob();
    } catch (error) {
      console.error('Failed to export user data:', error);
      throw error;
    }
  }

  // Clear stored auth token
  logout(): void {
    localStorage.removeItem('auth_token');
  }

  // Manually refresh and sync meeting summaries from Google Drive
  async refreshSummaries(): Promise<{ success: boolean; message?: string; summaries_created?: number }> {
    try {
      const response = await this.request<{ success: boolean; message?: string; summaries_created?: number }>(
        '/api/v1/meetings/refresh',
        { method: 'POST' }
      );
      return response;
    } catch (error) {
      console.error('Failed to refresh summaries:', error);
      return { success: false, message: 'Failed to refresh summaries' };
    }
  }
}

export const apiService = new ApiService() 
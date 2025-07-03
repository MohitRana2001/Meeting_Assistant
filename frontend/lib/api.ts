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
  source: 'drive' | 'gmail'
  sender?: string
  email_id?: string
  attachments?: Array<{
    filename: string
    attachment_id: string
    mime_type: string
    size: number
  }>
}

export interface AuthResponse {
  status: string
  message: string
  needs_reauthentication?: boolean
  missing_scopes?: string[]
  reauthentication_url?: string
}

export interface UserProfile {
  id: number
  email: string
  full_name: string | null
  picture: string | null
  created_at: string
}

export interface CalendarEvent {
  id: string
  title: string
  start: string
  end: string
  attendees?: number
  meetingType?: string
  hasRecording?: boolean
  meetingLink?: string
}

export interface Notification {
  id: string
  type: string
  title: string
  message: string
  timestamp: string
  read: boolean
  metadata?: {
    summaryId?: string
    summaryTitle?: string
    taskCount?: number
  }
}

export interface GoogleTask {
  id: string
  title: string
  notes: string
  status: string
  due?: string
  updated: string
  tasklist_id: string
  tasklist_title: string
}

export interface TaskSyncResult {
  success: boolean
  message: string
  tasks_synced: number
  calendar_events_created: number
  task_list_title?: string
  task_list_url?: string
  errors?: string[]
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

  // Get all meeting summaries (Drive only for backward compatibility)
  async getSummaries(): Promise<MeetingSummary[]> {
    return this.request<MeetingSummary[]>('/api/v1/meetings/summaries')
  }

  // Get combined summaries from both Drive and Gmail
  async getCombinedSummaries(includeGmail: boolean = true, gmailDaysBack: number = 7): Promise<{
    success: boolean;
    total_summaries: number;
    drive_summaries: number;
    gmail_summaries: number;
    summaries: MeetingSummary[];
  }> {
    try {
      const params = new URLSearchParams({
        include_gmail: includeGmail.toString(),
        gmail_days_back: gmailDaysBack.toString()
      });
      
      return await this.request<{
        success: boolean;
        total_summaries: number;
        drive_summaries: number;
        gmail_summaries: number;
        summaries: MeetingSummary[];
      }>(`/api/v1/meetings/combined-summaries?${params}`);
    } catch (error) {
      console.error('Failed to get combined summaries:', error);
      return {
        success: false,
        total_summaries: 0,
        drive_summaries: 0,
        gmail_summaries: 0,
        summaries: []
      };
    }
  }

  // Scan Gmail for meeting summaries
  async scanGmail(daysBack: number = 7): Promise<{
    success: boolean;
    message: string;
    summaries_found: number;
    summaries: MeetingSummary[];
  }> {
    try {
      return await this.request<{
        success: boolean;
        message: string;
        summaries_found: number;
        summaries: MeetingSummary[];
      }>(`/api/v1/meetings/scan-gmail?days_back=${daysBack}`, {
        method: 'POST'
      });
    } catch (error) {
      console.error('Failed to scan Gmail:', error);
      return {
        success: false,
        message: 'Failed to scan Gmail for meeting summaries',
        summaries_found: 0,
        summaries: []
      };
    }
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

  // Update task completion status with Google Tasks sync
  async updateTaskStatusWithGoogleSync(summaryId: string, taskId: string, completed: boolean): Promise<{ 
    success: boolean; 
    message?: string; 
    google_task_updated?: boolean;
  }> {
    try {
      const response = await this.request<{ 
        success: boolean; 
        message?: string; 
        google_task_updated?: boolean;
      }>(
        `/api/v1/tasks/update-google-task-status/${summaryId}/${taskId}?completed=${completed}`,
        {
          method: 'PATCH'
        }
      );
      return response;
    } catch (error) {
      console.error('Failed to update task status with Google sync:', error);
      return { success: false, message: 'Failed to update task status' };
    }
  }

  // Check user authentication status
  async checkAuth(): Promise<AuthResponse> {
    return this.request<AuthResponse>('/api/v1/auth/check-permissions')
  }

  // Get current user profile
  async getUserProfile(): Promise<UserProfile> {
    return this.request<UserProfile>('/api/v1/auth/user')
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

  // Google Tasks Integration - Enhanced
  async syncTasksToGoogle(summaryId: string): Promise<TaskSyncResult> {
    try {
      const response = await this.request<TaskSyncResult>(
        `/api/v1/tasks/sync/${summaryId}`, 
        { method: 'POST' }
      );
      return response;
    } catch (error) {
      console.error('Failed to sync tasks to Google:', error);
      return { 
        success: false, 
        message: 'Failed to sync tasks to Google Tasks',
        tasks_synced: 0,
        calendar_events_created: 0
      };
    }
  }

  // Sync all recent meeting tasks to Google Tasks
  async syncAllTasksToGoogle(limit: number = 10): Promise<TaskSyncResult & { summaries_processed: number; total_tasks_synced: number }> {
    try {
      const response = await this.request<TaskSyncResult & { summaries_processed: number; total_tasks_synced: number }>(
        `/api/v1/tasks/sync-all?limit=${limit}`,
        { method: 'POST' }
      );
      return response;
    } catch (error) {
      console.error('Failed to sync all tasks to Google:', error);
      return {
        success: false,
        message: 'Failed to sync all tasks to Google Tasks',
        tasks_synced: 0,
        calendar_events_created: 0,
        summaries_processed: 0,
        total_tasks_synced: 0
      };
    }
  }

  // Get all user tasks from meeting summaries
  async getUserTasks(): Promise<Array<{
    id: string;
    text: string;
    completed: boolean;
    summary_id: string;
    summary_title: string;
    created_at: string;
  }>> {
    try {
      return await this.request<Array<{
        id: string;
        text: string;
        completed: boolean;
        summary_id: string;
        summary_title: string;
        created_at: string;
      }>>('/api/v1/tasks/');
    } catch (error) {
      console.error('Failed to get user tasks:', error);
      return [];
    }
  }

  // Get tasks directly from Google Tasks
  async getGoogleTasks(): Promise<GoogleTask[]> {
    try {
      return await this.request<GoogleTask[]>('/api/v1/tasks/google-tasks');
    } catch (error) {
      console.error('Failed to get Google Tasks:', error);
      return [];
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

  // Notifications
  async getNotifications(limit?: number): Promise<Notification[]> {
    try {
      const endpoint = limit ? `/api/v1/notifications/?limit=${limit}` : '/api/v1/notifications/';
      return await this.request<Notification[]>(endpoint);
    } catch (error) {
      console.error('Failed to get notifications:', error);
      return [];
    }
  }

  async getUnreadNotificationCount(): Promise<{ unreadCount: number }> {
    try {
      return await this.request<{ unreadCount: number }>('/api/v1/notifications/unread-count');
    } catch (error) {
      console.error('Failed to get unread notification count:', error);
      return { unreadCount: 0 };
    }
  }

  async markNotificationRead(notificationId: string): Promise<{ success: boolean; message?: string }> {
    try {
      return await this.request<{ success: boolean; message?: string }>(
        `/api/v1/notifications/${notificationId}/mark-read`,
        { method: 'POST' }
      );
    } catch (error) {
      console.error('Failed to mark notification as read:', error);
      return { success: false, message: 'Failed to mark notification as read' };
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

export { ApiService };
export const apiService = new ApiService() 
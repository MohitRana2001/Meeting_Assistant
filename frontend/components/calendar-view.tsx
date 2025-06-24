"use client";

import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  Calendar,
  Clock,
  Users,
  ExternalLink,
  RefreshCw,
  CheckCircle2,
  Circle,
} from "lucide-react";
import { apiService, MeetingSummary } from "@/lib/api";

interface CalendarEvent {
  id: string;
  title: string;
  start: string;
  end: string;
  attendees?: number;
  meetingType?: string;
  hasRecording?: boolean;
}

interface TaskWithSummary {
  id: string;
  text: string;
  completed: boolean;
  summaryTitle: string;
  summaryId: string;
  summaryDate: string;
}

export function CalendarView() {
  const [events, setEvents] = useState<CalendarEvent[]>([]);
  const [tasks, setTasks] = useState<TaskWithSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<"events" | "tasks">("events");

  useEffect(() => {
    loadCalendarData();
  }, []);

  const loadCalendarData = async () => {
    try {
      setLoading(true);
      setError(null);

      // Load real meeting summaries and extract tasks
      try {
        const summaries = await apiService.getSummaries();
        const allTasks: TaskWithSummary[] = [];

        summaries.forEach((summary: MeetingSummary) => {
          if (summary.tasks && summary.tasks.length > 0) {
            summary.tasks.forEach((task) => {
              allTasks.push({
                id: `${summary.id}-${task.id}`,
                text: task.text,
                completed: task.completed,
                summaryTitle: summary.title,
                summaryId: summary.id,
                summaryDate: summary.createdAt,
              });
            });
          }
        });

        setTasks(allTasks);
        console.log(
          `Loaded ${allTasks.length} tasks from ${summaries.length} meeting summaries`
        );
      } catch (apiError) {
        console.log("Failed to load real tasks, using calendar API fallback");
      }

      // Try to fetch real calendar events from API (fallback to mock)
      try {
        const realEvents = await apiService.getCalendarEvents();
        if (realEvents && realEvents.length > 0) {
          setEvents(realEvents);
          return;
        }
      } catch (apiError) {
        console.log("API not available, using mock data");
      }

      // Fallback to mock data if API is not available
      const mockEvents: CalendarEvent[] = [
        {
          id: "1",
          title: "Product Planning Meeting",
          start: "2024-01-15T10:00:00Z",
          end: "2024-01-15T11:00:00Z",
          attendees: 5,
          meetingType: "Google Meet",
          hasRecording: true,
        },
        {
          id: "2",
          title: "Sprint Retrospective",
          start: "2024-01-15T14:00:00Z",
          end: "2024-01-15T15:00:00Z",
          attendees: 8,
          meetingType: "Google Meet",
          hasRecording: false,
        },
        {
          id: "3",
          title: "Client Check-in",
          start: "2024-01-16T09:00:00Z",
          end: "2024-01-16T09:30:00Z",
          attendees: 3,
          meetingType: "Google Meet",
          hasRecording: true,
        },
      ];

      setEvents(mockEvents);
    } catch (err) {
      console.error("Failed to load calendar data:", err);
      setError("Failed to load calendar data");
    } finally {
      setLoading(false);
    }
  };

  const handleToggleTask = async (taskWithSummary: TaskWithSummary) => {
    const [summaryId, taskId] = taskWithSummary.id.split("-");
    const newCompleted = !taskWithSummary.completed;

    // Optimistic update
    setTasks((prev) =>
      prev.map((task) =>
        task.id === taskWithSummary.id
          ? { ...task, completed: newCompleted }
          : task
      )
    );

    try {
      const result = await apiService.updateTaskStatus(
        summaryId,
        taskId,
        newCompleted
      );
      if (!result.success) {
        // Revert on failure
        setTasks((prev) =>
          prev.map((task) =>
            task.id === taskWithSummary.id
              ? { ...task, completed: !newCompleted }
              : task
          )
        );
      }
    } catch (error) {
      console.error("Failed to update task:", error);
      // Revert on failure
      setTasks((prev) =>
        prev.map((task) =>
          task.id === taskWithSummary.id
            ? { ...task, completed: !newCompleted }
            : task
        )
      );
    }
  };

  const handleOpenInGoogleCalendar = () => {
    window.open("https://calendar.google.com", "_blank");
  };

  const formatEventTime = (start: string, end: string) => {
    const startDate = new Date(start);
    const endDate = new Date(end);
    const startTime = startDate.toLocaleTimeString([], {
      hour: "2-digit",
      minute: "2-digit",
    });
    const endTime = endDate.toLocaleTimeString([], {
      hour: "2-digit",
      minute: "2-digit",
    });
    return `${startTime} - ${endTime}`;
  };

  const formatEventDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleDateString([], {
      weekday: "short",
      month: "short",
      day: "numeric",
    });
  };

  const formatTaskDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleDateString();
  };

  const completedTasksCount = tasks.filter((task) => task.completed).length;
  const totalTasksCount = tasks.length;

  if (loading) {
    return (
      <div className="h-full p-6 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Loading calendar data...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="h-full p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Calendar & Tasks</h1>
          <p className="text-gray-600">Your meetings and action items</p>
        </div>
        <div className="flex items-center gap-3">
          <Button
            variant="outline"
            onClick={loadCalendarData}
            disabled={loading}
          >
            <RefreshCw className="h-4 w-4 mr-2" />
            Refresh
          </Button>
          <Button onClick={handleOpenInGoogleCalendar}>
            <ExternalLink className="h-4 w-4 mr-2" />
            Open Google Calendar
          </Button>
        </div>
      </div>

      {error && (
        <div className="p-4 bg-red-50 border border-red-200 rounded-lg">
          <p className="text-red-800">{error}</p>
          <button
            onClick={loadCalendarData}
            className="mt-2 text-red-600 hover:text-red-800 underline"
          >
            Try again
          </button>
        </div>
      )}

      {/* Tab Navigation */}
      <div className="flex space-x-1 bg-gray-100 p-1 rounded-lg w-fit">
        <button
          onClick={() => setActiveTab("events")}
          className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
            activeTab === "events"
              ? "bg-white text-gray-900 shadow-sm"
              : "text-gray-600 hover:text-gray-900"
          }`}
        >
          Calendar Events ({events.length})
        </button>
        <button
          onClick={() => setActiveTab("tasks")}
          className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
            activeTab === "tasks"
              ? "bg-white text-gray-900 shadow-sm"
              : "text-gray-600 hover:text-gray-900"
          }`}
        >
          Meeting Tasks ({completedTasksCount}/{totalTasksCount})
        </button>
      </div>

      {/* Content */}
      <div className="space-y-4">
        {activeTab === "events" ? (
          // Events List
          events.length === 0 ? (
            <Card>
              <CardContent className="p-8 text-center">
                <Calendar className="h-12 w-12 text-gray-400 mx-auto mb-4" />
                <h3 className="text-lg font-medium text-gray-900 mb-2">
                  No events found
                </h3>
                <p className="text-gray-600">
                  Your upcoming calendar events will appear here
                </p>
              </CardContent>
            </Card>
          ) : (
            events.map((event) => (
              <Card
                key={event.id}
                className="hover:shadow-md transition-shadow"
              >
                <CardContent className="p-6">
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center gap-3 mb-2">
                        <h3 className="text-lg font-semibold text-gray-900">
                          {event.title}
                        </h3>
                        {event.hasRecording && (
                          <Badge
                            variant="outline"
                            className="bg-green-50 text-green-700 border-green-200"
                          >
                            Recording Available
                          </Badge>
                        )}
                      </div>

                      <div className="flex items-center gap-4 text-sm text-gray-600">
                        <div className="flex items-center gap-1">
                          <Calendar className="h-4 w-4" />
                          {formatEventDate(event.start)}
                        </div>
                        <div className="flex items-center gap-1">
                          <Clock className="h-4 w-4" />
                          {formatEventTime(event.start, event.end)}
                        </div>
                        {event.attendees && (
                          <div className="flex items-center gap-1">
                            <Users className="h-4 w-4" />
                            {event.attendees} attendees
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))
          )
        ) : // Tasks List
        tasks.length === 0 ? (
          <Card>
            <CardContent className="p-8 text-center">
              <CheckCircle2 className="h-12 w-12 text-gray-400 mx-auto mb-4" />
              <h3 className="text-lg font-medium text-gray-900 mb-2">
                No tasks found
              </h3>
              <p className="text-gray-600">
                Tasks from meeting summaries will appear here
              </p>
            </CardContent>
          </Card>
        ) : (
          tasks.map((task) => (
            <Card key={task.id} className="hover:shadow-md transition-shadow">
              <CardContent className="p-4">
                <div className="flex items-start gap-3">
                  <button
                    onClick={() => handleToggleTask(task)}
                    className="flex-shrink-0 mt-1"
                  >
                    {task.completed ? (
                      <CheckCircle2 className="h-5 w-5 text-green-600" />
                    ) : (
                      <Circle className="h-5 w-5 text-gray-400 hover:text-gray-600" />
                    )}
                  </button>

                  <div className="flex-1 min-w-0">
                    <p
                      className={`text-sm ${
                        task.completed
                          ? "line-through text-gray-500"
                          : "text-gray-900"
                      }`}
                    >
                      {task.text}
                    </p>
                    <div className="flex items-center gap-2 mt-2 text-xs text-gray-500">
                      <span>From: {task.summaryTitle}</span>
                      <span>•</span>
                      <span>{formatTaskDate(task.summaryDate)}</span>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))
        )}
      </div>
    </div>
  );
}

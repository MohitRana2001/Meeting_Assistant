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
  Bot,
  Lightbulb,
  TrendingUp,
  Target,
  AlertCircle,
  CheckCircle,
  Zap,
} from "lucide-react";
import { apiService } from "@/lib/api";

interface CalendarEvent {
  id: string;
  title: string;
  start: string;
  end: string;
  attendees?: number;
  meetingType?: string;
  hasRecording?: boolean;
}

interface AIInsight {
  id: string;
  type: "preparation" | "optimization" | "follow-up" | "analytics" | "conflict";
  title: string;
  description: string;
  priority: "high" | "medium" | "low";
  actionable: boolean;
  relatedMeetingId?: string;
}

export function CalendarView() {
  const [events, setEvents] = useState<CalendarEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<"events" | "agents">("events");
  const [aiInsights, setAiInsights] = useState<AIInsight[]>([]);

  useEffect(() => {
    loadCalendarData();
  }, []);

  const loadCalendarData = async () => {
    try {
      setLoading(true);
      setError(null);

      // Fetch real calendar events from Google Calendar API
      try {
        const realEvents = await apiService.getCalendarEvents();
        setEvents(realEvents);
        console.log(
          `Loaded ${realEvents.length} calendar events from Google Calendar`
        );

        // Generate AI insights based on events
        generateAIInsights(realEvents);
      } catch (apiError) {
        console.error("Failed to load calendar events:", apiError);
        setError(
          "Failed to load calendar events. Please check your Google Calendar permissions and try again."
        );
        setEvents([]);
      }
    } catch (err) {
      console.error("Failed to load calendar data:", err);
      setError("Failed to load calendar data. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  const generateAIInsights = (events: CalendarEvent[]) => {
    const insights: AIInsight[] = [];
    const now = new Date();
    const upcomingEvents = events.filter(
      (event) => new Date(event.start) > now
    );
    const todayEvents = events.filter((event) => {
      const eventDate = new Date(event.start);
      return eventDate.toDateString() === now.toDateString();
    });

    // Meeting Preparation Insights
    if (upcomingEvents.length > 0) {
      const nextMeeting = upcomingEvents[0];
      insights.push({
        id: "prep-1",
        type: "preparation",
        title: `Prepare for "${nextMeeting.title}"`,
        description: `Your next meeting is in ${Math.round(
          (new Date(nextMeeting.start).getTime() - now.getTime()) /
            (1000 * 60 * 60)
        )} hours. ${
          nextMeeting.attendees
            ? `With ${nextMeeting.attendees} attendees.`
            : ""
        } Consider preparing an agenda and reviewing previous meeting notes.`,
        priority: "high",
        actionable: true,
        relatedMeetingId: nextMeeting.id,
      });
    }

    // Schedule Optimization
    if (todayEvents.length > 5) {
      insights.push({
        id: "opt-1",
        type: "optimization",
        title: "Heavy Meeting Day Detected",
        description: `You have ${todayEvents.length} meetings today. Consider rescheduling non-critical meetings or blocking focus time for tomorrow.`,
        priority: "medium",
        actionable: true,
      });
    }

    // Analytics Insights
    const avgMeetingDuration =
      events.reduce((acc, event) => {
        const duration =
          (new Date(event.end).getTime() - new Date(event.start).getTime()) /
          (1000 * 60);
        return acc + duration;
      }, 0) / events.length;

    if (avgMeetingDuration > 60) {
      insights.push({
        id: "analytics-1",
        type: "analytics",
        title: "Long Meeting Pattern Detected",
        description: `Your average meeting duration is ${Math.round(
          avgMeetingDuration
        )} minutes. Consider shorter, more focused meetings to increase productivity.`,
        priority: "medium",
        actionable: true,
      });
    }

    // Follow-up Insights
    if (events.length > 0) {
      insights.push({
        id: "follow-1",
        type: "follow-up",
        title: "Follow-up Recommendations",
        description: `Based on your recent meetings, consider following up on action items from your last 3 meetings. Check if any attendees need additional information.`,
        priority: "low",
        actionable: true,
      });
    }

    // Conflict Detection
    const conflicts = events.filter((event, index) => {
      return events.some((otherEvent, otherIndex) => {
        if (index === otherIndex) return false;
        const eventStart = new Date(event.start);
        const eventEnd = new Date(event.end);
        const otherStart = new Date(otherEvent.start);
        const otherEnd = new Date(otherEvent.end);

        return eventStart < otherEnd && eventEnd > otherStart;
      });
    });

    if (conflicts.length > 0) {
      insights.push({
        id: "conflict-1",
        type: "conflict",
        title: "Scheduling Conflicts Detected",
        description: `Found ${conflicts.length} potential scheduling conflicts. Review your calendar to resolve overlapping meetings.`,
        priority: "high",
        actionable: true,
      });
    }

    setAiInsights(insights);
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

  const getInsightIcon = (type: string) => {
    switch (type) {
      case "preparation":
        return <Lightbulb className="h-5 w-5 text-yellow-600" />;
      case "optimization":
        return <TrendingUp className="h-5 w-5 text-blue-600" />;
      case "follow-up":
        return <CheckCircle className="h-5 w-5 text-green-600" />;
      case "analytics":
        return <Target className="h-5 w-5 text-purple-600" />;
      case "conflict":
        return <AlertCircle className="h-5 w-5 text-red-600" />;
      default:
        return <Bot className="h-5 w-5 text-gray-600" />;
    }
  };

  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case "high":
        return "bg-red-50 border-red-200 text-red-800";
      case "medium":
        return "bg-yellow-50 border-yellow-200 text-yellow-800";
      case "low":
        return "bg-green-50 border-green-200 text-green-800";
      default:
        return "bg-gray-50 border-gray-200 text-gray-800";
    }
  };

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
          <h1 className="text-2xl font-bold text-gray-900">Smart Calendar</h1>
          <p className="text-gray-600">
            Your meetings with AI-powered insights
          </p>
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
          className={`px-4 py-2 rounded-md text-sm font-medium transition-colors flex items-center gap-2 ${
            activeTab === "events"
              ? "bg-white text-gray-900 shadow-sm"
              : "text-gray-600 hover:text-gray-900"
          }`}
        >
          <Calendar className="h-4 w-4" />
          Calendar Events ({events.length})
        </button>
        <button
          onClick={() => setActiveTab("agents")}
          className={`px-4 py-2 rounded-md text-sm font-medium transition-colors flex items-center gap-2 ${
            activeTab === "agents"
              ? "bg-white text-gray-900 shadow-sm"
              : "text-gray-600 hover:text-gray-900"
          }`}
        >
          <Bot className="h-4 w-4" />
          AI Insights ({aiInsights.length})
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
        ) : (
          // AI Insights
          <div className="space-y-4">
            {aiInsights.length === 0 ? (
              <Card>
                <CardContent className="p-8 text-center">
                  <Bot className="h-12 w-12 text-gray-400 mx-auto mb-4" />
                  <h3 className="text-lg font-medium text-gray-900 mb-2">
                    No insights available
                  </h3>
                  <p className="text-gray-600">
                    AI insights will appear here based on your calendar patterns
                  </p>
                </CardContent>
              </Card>
            ) : (
              <>
                <div className="mb-4 p-4 bg-gradient-to-r from-indigo-50 to-purple-50 border border-indigo-200 rounded-lg">
                  <div className="flex items-center gap-2 mb-2">
                    <Zap className="h-5 w-5 text-indigo-600" />
                    <h3 className="font-semibold text-indigo-900">
                      AI-Powered Calendar Intelligence
                    </h3>
                  </div>
                  <p className="text-sm text-indigo-700">
                    Your personal AI assistant analyzes your calendar patterns
                    and provides actionable insights to optimize your schedule
                    and productivity.
                  </p>
                </div>

                {aiInsights.map((insight) => (
                  <Card
                    key={insight.id}
                    className="hover:shadow-md transition-shadow"
                  >
                    <CardContent className="p-6">
                      <div className="flex items-start gap-4">
                        <div className="flex-shrink-0">
                          {getInsightIcon(insight.type)}
                        </div>
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2 mb-2">
                            <h3 className="text-lg font-semibold text-gray-900">
                              {insight.title}
                            </h3>
                            <Badge
                              className={`text-xs ${getPriorityColor(
                                insight.priority
                              )}`}
                            >
                              {insight.priority} priority
                            </Badge>
                          </div>
                          <p className="text-gray-600 mb-3">
                            {insight.description}
                          </p>
                          {insight.actionable && (
                            <Button variant="outline" size="sm">
                              Take Action
                            </Button>
                          )}
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

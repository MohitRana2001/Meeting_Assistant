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

export function CalendarView() {
  const [events, setEvents] = useState<CalendarEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

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
          <h1 className="text-2xl font-bold text-gray-900">Calendar</h1>
          <p className="text-gray-600">
            Your upcoming meetings from Google Calendar
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

      {/* Content */}
      <div className="space-y-4">
        {
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
        }
      </div>
    </div>
  );
}

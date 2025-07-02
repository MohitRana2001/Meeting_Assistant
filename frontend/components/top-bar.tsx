"use client";

import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from "@/components/ui/sheet";
import { Bell, Search, RefreshCw } from "lucide-react";
import { apiService, Notification } from "@/lib/api";

interface TopBarProps {
  pageTitle: string;
  actions?: React.ReactNode;
}

export function TopBar({ pageTitle, actions }: TopBarProps) {
  const [searchQuery, setSearchQuery] = useState("");
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [loading, setLoading] = useState(false);
  const [isSheetOpen, setIsSheetOpen] = useState(false);

  // Load notifications when component mounts or sheet opens
  useEffect(() => {
    loadNotifications();
    loadUnreadCount();

    // Set up polling for real-time updates
    const interval = setInterval(() => {
      loadUnreadCount();
    }, 30000); // Check every 30 seconds

    return () => clearInterval(interval);
  }, []);

  // Load notifications when sheet opens
  useEffect(() => {
    if (isSheetOpen) {
      loadNotifications();
    }
  }, [isSheetOpen]);

  const loadNotifications = async () => {
    try {
      setLoading(true);
      const data = await apiService.getNotifications(20);
      setNotifications(data);
    } catch (error) {
      console.error("Failed to load notifications:", error);
    } finally {
      setLoading(false);
    }
  };

  const loadUnreadCount = async () => {
    try {
      const data = await apiService.getUnreadNotificationCount();
      setUnreadCount(data.unreadCount);
    } catch (error) {
      console.error("Failed to load unread count:", error);
    }
  };

  const handleNotificationClick = async (notification: Notification) => {
    // Mark as read if it's unread
    if (!notification.read) {
      try {
        await apiService.markNotificationRead(notification.id);
        // Update local state
        setNotifications((prev) =>
          prev.map((n) => (n.id === notification.id ? { ...n, read: true } : n))
        );
        // Update unread count
        setUnreadCount((prev) => Math.max(0, prev - 1));
      } catch (error) {
        console.error("Failed to mark notification as read:", error);
      }
    }
  };

  const formatNotificationTime = (timestamp: string) => {
    const date = new Date(timestamp);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMinutes = Math.floor(diffMs / (1000 * 60));
    const diffHours = Math.floor(diffMinutes / 60);
    const diffDays = Math.floor(diffHours / 24);

    if (diffMinutes < 1) {
      return "Just now";
    } else if (diffMinutes < 60) {
      return `${diffMinutes}m ago`;
    } else if (diffHours < 24) {
      return `${diffHours}h ago`;
    } else if (diffDays < 7) {
      return `${diffDays}d ago`;
    } else {
      return date.toLocaleDateString();
    }
  };

  const getNotificationIcon = (type: string) => {
    switch (type) {
      case "meeting_summary":
        return "📝";
      case "tasks_sync":
        return "✅";
      case "calendar_sync":
        return "📅";
      default:
        return "🔔";
    }
  };

  return (
    <div className="flex items-center justify-between px-6 py-4 bg-white border-b border-gray-200">
      <div>
        <h1 className="text-2xl font-semibold text-gray-900">{pageTitle}</h1>
      </div>

      <div className="flex items-center gap-4">
        {/* Search */}
        <div className="relative">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
          <Input
            placeholder="Search meeting titles or tasks..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-10 w-80 bg-gray-50 border-gray-200 focus:bg-white focus:border-indigo-300 focus:ring-indigo-200"
          />
        </div>

        {/* Custom Actions */}
        {actions && <div className="flex items-center gap-2">{actions}</div>}

        {/* Notifications */}
        <Sheet open={isSheetOpen} onOpenChange={setIsSheetOpen}>
          <SheetTrigger asChild>
            <Button
              variant="ghost"
              size="sm"
              className="relative p-2 hover:bg-gray-100"
            >
              <Bell className="h-5 w-5 text-gray-600" />
              {unreadCount > 0 && (
                <Badge className="absolute -top-1 -right-1 h-5 w-5 p-0 flex items-center justify-center bg-red-500 text-white text-xs">
                  {unreadCount > 9 ? "9+" : unreadCount}
                </Badge>
              )}
            </Button>
          </SheetTrigger>
          <SheetContent className="w-96">
            <SheetHeader>
              <div className="flex items-center justify-between">
                <SheetTitle>Notifications</SheetTitle>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={loadNotifications}
                  disabled={loading}
                  className="h-8 w-8 p-0"
                >
                  <RefreshCw
                    className={`h-4 w-4 ${loading ? "animate-spin" : ""}`}
                  />
                </Button>
              </div>
            </SheetHeader>

            <div className="mt-6 space-y-3">
              {loading && notifications.length === 0 ? (
                <div className="text-center py-8 text-gray-500">
                  <RefreshCw className="h-8 w-8 animate-spin mx-auto mb-2" />
                  Loading notifications...
                </div>
              ) : notifications.length === 0 ? (
                <div className="text-center py-8 text-gray-500">
                  <Bell className="h-8 w-8 mx-auto mb-2 opacity-50" />
                  No notifications yet
                </div>
              ) : (
                notifications.map((notification) => (
                  <div
                    key={notification.id}
                    onClick={() => handleNotificationClick(notification)}
                    className={`p-3 rounded-lg border transition-all cursor-pointer hover:shadow-md ${
                      notification.read
                        ? "bg-gray-50 border-gray-200"
                        : "bg-blue-50 border-blue-200 shadow-sm"
                    }`}
                  >
                    <div className="flex items-start gap-3">
                      <span className="text-lg flex-shrink-0 mt-0.5">
                        {getNotificationIcon(notification.type)}
                      </span>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-start justify-between gap-2">
                          <h4 className="text-sm font-medium text-gray-900 leading-tight">
                            {notification.title}
                          </h4>
                          {!notification.read && (
                            <div className="w-2 h-2 bg-blue-500 rounded-full flex-shrink-0 mt-1"></div>
                          )}
                        </div>
                        <p className="text-sm text-gray-600 mt-1 leading-relaxed">
                          {notification.message}
                        </p>
                        <p className="text-xs text-gray-500 mt-2">
                          {formatNotificationTime(notification.timestamp)}
                        </p>
                      </div>
                    </div>
                  </div>
                ))
              )}
            </div>

            {notifications.length > 0 && (
              <div className="mt-6 pt-4 border-t">
                <p className="text-xs text-gray-500 text-center">
                  Showing {notifications.length} recent notifications
                </p>
              </div>
            )}
          </SheetContent>
        </Sheet>
      </div>
    </div>
  );
}

"use client";

import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import {
  LayoutDashboard,
  Calendar,
  Settings,
  ChevronLeft,
  ChevronRight,
  Bot,
} from "lucide-react";
import { cn } from "@/lib/utils";
import Link from "next/link";
import { apiService, UserProfile } from "@/lib/api";

interface SidebarProps {
  collapsed: boolean;
  onToggle: () => void;
  activeItem?: string;
  onItemSelect?: (item: string) => void;
}

export function Sidebar({
  collapsed,
  onToggle,
  activeItem = "dashboard",
  onItemSelect,
}: SidebarProps) {
  const [userProfile, setUserProfile] = useState<UserProfile | null>(null);
  const [authStatus, setAuthStatus] = useState<"loading" | "ok" | "error">(
    "loading"
  );

  const navItems = [
    { id: "dashboard", label: "Dashboard", icon: LayoutDashboard },
    { id: "calendar", label: "Calendar", icon: Calendar },
    { id: "settings", label: "Settings", icon: Settings },
  ];

  // Load user profile on component mount
  useEffect(() => {
    loadUserProfile();
  }, []);

  const loadUserProfile = async () => {
    try {
      const token = localStorage.getItem("auth_token");
      if (!token) {
        setAuthStatus("error");
        return;
      }

      const [profile, authCheck] = await Promise.all([
        apiService.getUserProfile(),
        apiService.checkAuth(),
      ]);

      setUserProfile(profile);
      setAuthStatus(authCheck.status === "ok" ? "ok" : "error");
    } catch (error) {
      console.error("Failed to load user profile:", error);
      setAuthStatus("error");
    }
  };

  const handleItemClick = (itemId: string) => {
    if (onItemSelect) {
      onItemSelect(itemId);
    }
  };

  const getInitials = (name: string | null, email: string) => {
    if (name) {
      return name
        .split(" ")
        .map((n) => n[0])
        .join("")
        .toUpperCase()
        .slice(0, 2);
    }
    return email.slice(0, 2).toUpperCase();
  };

  const getDisplayName = (profile: UserProfile) => {
    return profile.full_name || profile.email.split("@")[0];
  };

  return (
    <div
      className={cn(
        "flex flex-col h-full bg-white border-r border-gray-200 transition-all duration-300",
        collapsed ? "w-16" : "w-60"
      )}
    >
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-gray-200">
        {!collapsed && (
          <Link
            href="/"
            className="flex items-center gap-3 hover:opacity-80 transition-opacity"
          >
            <div className="flex items-center justify-center w-8 h-8 bg-indigo-100 rounded-lg">
              <Bot className="w-5 h-5 text-indigo-600" />
            </div>
            <span className="font-semibold text-gray-900 text-lg">
              MeetingMate
            </span>
          </Link>
        )}
        {collapsed && (
          <Link
            href="/"
            className="flex items-center justify-center w-8 h-8 bg-indigo-100 rounded-lg mx-auto hover:opacity-80 transition-opacity"
          >
            <Bot className="w-5 h-5 text-indigo-600" />
          </Link>
        )}
        <Button
          variant="ghost"
          size="sm"
          onClick={onToggle}
          className="p-1 h-6 w-6 hover:bg-gray-100"
        >
          {collapsed ? (
            <ChevronRight className="h-4 w-4" />
          ) : (
            <ChevronLeft className="h-4 w-4" />
          )}
        </Button>
      </div>

      {/* Navigation */}
      <nav className="flex-1 p-4 space-y-2">
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = activeItem === item.id;

          return (
            <Button
              key={item.id}
              variant={isActive ? "default" : "ghost"}
              className={cn(
                "w-full justify-start gap-3 h-10 text-sm font-medium transition-colors",
                collapsed && "justify-center px-0",
                isActive
                  ? "bg-indigo-600 text-white hover:bg-indigo-700"
                  : "text-gray-700 hover:bg-gray-100 hover:text-gray-900"
              )}
              onClick={() => handleItemClick(item.id)}
            >
              <Icon className="h-4 w-4 flex-shrink-0" />
              {!collapsed && <span>{item.label}</span>}
            </Button>
          );
        })}
      </nav>

      {/* User Profile */}
      <div className="p-4 border-t border-gray-200">
        <div
          className={cn(
            "flex items-center gap-3",
            collapsed && "justify-center"
          )}
        >
          <Avatar className="h-8 w-8">
            {userProfile?.picture ? (
              <AvatarImage
                src={userProfile.picture}
                alt={userProfile.full_name || userProfile.email}
              />
            ) : (
              <AvatarFallback className="bg-indigo-100 text-indigo-600 text-sm font-medium">
                {userProfile
                  ? getInitials(userProfile.full_name, userProfile.email)
                  : "?"}
              </AvatarFallback>
            )}
          </Avatar>
          {!collapsed && (
            <div className="flex-1 min-w-0">
              {userProfile ? (
                <>
                  <p className="text-sm font-medium text-gray-900 truncate">
                    {getDisplayName(userProfile)}
                  </p>
                  <div className="flex items-center gap-2 mt-1">
                    {authStatus === "error" ? (
                      <Badge
                        variant="outline"
                        className="text-xs bg-red-50 text-red-700 border-red-200"
                      >
                        Reconnect Google
                      </Badge>
                    ) : authStatus === "ok" ? (
                      <Badge
                        variant="outline"
                        className="text-xs bg-green-50 text-green-700 border-green-200"
                      >
                        Connected
                      </Badge>
                    ) : (
                      <Badge
                        variant="outline"
                        className="text-xs bg-gray-50 text-gray-700 border-gray-200"
                      >
                        Loading...
                      </Badge>
                    )}
                  </div>
                </>
              ) : (
                <>
                  <p className="text-sm font-medium text-gray-500 truncate">
                    Loading profile...
                  </p>
                  <div className="flex items-center gap-2 mt-1">
                    <Badge
                      variant="outline"
                      className="text-xs bg-gray-50 text-gray-700 border-gray-200"
                    >
                      Loading...
                    </Badge>
                  </div>
                </>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

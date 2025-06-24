"use client"

import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar"
import { LayoutDashboard, CheckSquare, Calendar, Settings, ChevronLeft, ChevronRight, Bot } from "lucide-react"
import { cn } from "@/lib/utils"

interface SidebarProps {
  collapsed: boolean
  onToggle: () => void
}

export function Sidebar({ collapsed, onToggle }: SidebarProps) {
  const [activeItem, setActiveItem] = useState("dashboard")

  const navItems = [
    { id: "dashboard", label: "Dashboard", icon: LayoutDashboard },
    { id: "tasks", label: "Tasks", icon: CheckSquare },
    { id: "calendar", label: "Calendar", icon: Calendar },
    { id: "settings", label: "Settings", icon: Settings },
  ]

  return (
    <div
      className={cn(
        "flex flex-col h-full bg-white border-r border-gray-200 transition-all duration-300",
        collapsed ? "w-16" : "w-60",
      )}
    >
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-gray-200">
        {!collapsed && (
          <div className="flex items-center gap-3">
            <div className="flex items-center justify-center w-8 h-8 bg-indigo-100 rounded-lg">
              <Bot className="w-5 h-5 text-indigo-600" />
            </div>
            <span className="font-semibold text-gray-900 text-lg">MeetingMate</span>
          </div>
        )}
        {collapsed && (
          <div className="flex items-center justify-center w-8 h-8 bg-indigo-100 rounded-lg mx-auto">
            <Bot className="w-5 h-5 text-indigo-600" />
          </div>
        )}
        <Button variant="ghost" size="sm" onClick={onToggle} className="p-1 h-6 w-6 hover:bg-gray-100">
          {collapsed ? <ChevronRight className="h-4 w-4" /> : <ChevronLeft className="h-4 w-4" />}
        </Button>
      </div>

      {/* Navigation */}
      <nav className="flex-1 p-4 space-y-2">
        {navItems.map((item) => {
          const Icon = item.icon
          const isActive = activeItem === item.id

          return (
            <Button
              key={item.id}
              variant={isActive ? "default" : "ghost"}
              className={cn(
                "w-full justify-start gap-3 h-10 text-sm font-medium transition-colors",
                collapsed && "justify-center px-0",
                isActive
                  ? "bg-indigo-600 text-white hover:bg-indigo-700"
                  : "text-gray-700 hover:bg-gray-100 hover:text-gray-900",
              )}
              onClick={() => setActiveItem(item.id)}
            >
              <Icon className="h-4 w-4 flex-shrink-0" />
              {!collapsed && <span>{item.label}</span>}
            </Button>
          )
        })}
      </nav>

      {/* User Profile */}
      <div className="p-4 border-t border-gray-200">
        <div className={cn("flex items-center gap-3", collapsed && "justify-center")}>
          <Avatar className="h-8 w-8">
            <AvatarImage src="/placeholder.svg?height=32&width=32" />
            <AvatarFallback className="bg-indigo-100 text-indigo-600 text-sm font-medium">JD</AvatarFallback>
          </Avatar>
          {!collapsed && (
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-gray-900 truncate">John Doe</p>
              <div className="flex items-center gap-2 mt-1">
                <Badge variant="outline" className="text-xs bg-red-50 text-red-700 border-red-200">
                  Reconnect Google
                </Badge>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

"use client"

import { useEffect, useState } from "react"
import { Button } from "@/components/ui/button"
import { X, Zap } from "lucide-react"
import { cn } from "@/lib/utils"

interface ToastNotificationProps {
  message: string
  show: boolean
  onClose: () => void
  duration?: number
}

export function ToastNotification({ message, show, onClose, duration = 5000 }: ToastNotificationProps) {
  const [isVisible, setIsVisible] = useState(false)

  useEffect(() => {
    if (show) {
      setIsVisible(true)
      const timer = setTimeout(() => {
        setIsVisible(false)
        setTimeout(onClose, 300) // Wait for animation to complete
      }, duration)

      return () => clearTimeout(timer)
    }
  }, [show, duration, onClose])

  if (!show && !isVisible) return null

  return (
    <div className="fixed bottom-6 left-6 z-50">
      <div
        className={cn(
          "flex items-center gap-3 bg-white border border-gray-200 rounded-lg shadow-lg p-4 max-w-sm transition-all duration-300",
          isVisible ? "translate-y-0 opacity-100" : "translate-y-2 opacity-0",
        )}
      >
        <div className="flex items-center justify-center w-8 h-8 bg-emerald-100 rounded-full">
          <Zap className="w-4 h-4 text-emerald-600" />
        </div>
        <div className="flex-1">
          <p className="text-sm font-medium text-gray-900">{message}</p>
        </div>
        <Button
          variant="ghost"
          size="sm"
          onClick={() => {
            setIsVisible(false)
            setTimeout(onClose, 300)
          }}
          className="p-1 h-6 w-6 hover:bg-gray-100"
        >
          <X className="h-3 w-3" />
        </Button>
      </div>
    </div>
  )
}

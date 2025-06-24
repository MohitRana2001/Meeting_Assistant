"use client"

import { Button } from "@/components/ui/button"
import { AlertTriangle, X } from "lucide-react"
import { useState } from "react"

interface ReconnectBannerProps {
  onReconnect: () => void
  onDismiss: () => void
}

export function ReconnectBanner({ onReconnect, onDismiss }: ReconnectBannerProps) {
  const [isVisible, setIsVisible] = useState(true)

  if (!isVisible) return null

  return (
    <div className="bg-amber-50 border-l-4 border-amber-400 p-4 mb-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center">
          <AlertTriangle className="h-5 w-5 text-amber-400 mr-3" />
          <div>
            <p className="text-sm font-medium text-amber-800">Google Drive access expires in 24 hours</p>
            <p className="text-sm text-amber-700 mt-1">
              We'll renew automatically. If you revoked permissions, click reconnect.
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={onReconnect}
            className="bg-white hover:bg-amber-50 border-amber-300 text-amber-800"
          >
            Reconnect
          </Button>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => {
              setIsVisible(false)
              onDismiss()
            }}
            className="p-1 h-6 w-6 hover:bg-amber-100"
          >
            <X className="h-3 w-3" />
          </Button>
        </div>
      </div>
    </div>
  )
}

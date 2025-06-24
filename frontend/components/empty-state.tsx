"use client"

import { Button } from "@/components/ui/button"
import { Bot, ArrowRight } from "lucide-react"

interface EmptyStateProps {
  onConnect: () => void
}

export function EmptyState({ onConnect }: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center py-16 px-6">
      <div className="flex items-center justify-center w-24 h-24 bg-indigo-100 rounded-full mb-6">
        <Bot className="w-12 h-12 text-indigo-600" />
      </div>

      <div className="text-center max-w-md">
        <h3 className="text-xl font-semibold text-gray-900 mb-2">No meetings yet</h3>
        <p className="text-gray-600 mb-8 leading-relaxed">
          Connect Google Workspace and we'll start listening for your meetings. We'll automatically generate summaries
          and extract action items for you.
        </p>

        <Button onClick={onConnect} className="bg-indigo-600 hover:bg-indigo-700 text-white font-medium">
          Connect Google Workspace
          <ArrowRight className="ml-2 h-4 w-4" />
        </Button>
      </div>

      <div className="mt-12 text-center">
        <p className="text-xs text-gray-500">
          We'll process your meetings automatically and notify you when summaries are ready
        </p>
      </div>
    </div>
  )
}

"use client";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Badge } from "@/components/ui/badge";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { ExternalLink, CheckCircle2 } from "lucide-react";
import { formatDistanceToNow } from "date-fns";
import { MeetingSummary } from "@/lib/api";

interface DetailsDrawerProps {
  summary: MeetingSummary | null;
  open: boolean;
  onClose: () => void;
  onTaskToggle: (taskId: string) => void;
}

export function DetailsDrawer({
  summary,
  open,
  onClose,
  onTaskToggle,
}: DetailsDrawerProps) {
  if (!summary) return null;

  return (
    <Sheet open={open} onOpenChange={onClose}>
      <SheetContent className="w-[400px] sm:w-[400px] p-0">
        <div className="flex flex-col h-full">
          <SheetHeader className="px-6 py-4 border-b border-gray-200">
            <div className="flex items-start justify-between">
              <div className="flex-1 min-w-0">
                <SheetTitle className="text-lg font-semibold text-gray-900 pr-8">
                  {summary.title}
                </SheetTitle>
                <div className="flex items-center gap-3 mt-2">
                  <span className="text-sm text-gray-500">
                    {formatDistanceToNow(new Date(summary.createdAt), {
                      addSuffix: true,
                    })}
                  </span>
                </div>
              </div>
            </div>
          </SheetHeader>

          <div className="flex-1 overflow-y-auto">
            <div className="px-6 py-6 space-y-6">
              {/* Summary Section */}
              <div>
                <h3 className="text-sm font-semibold text-gray-900 mb-3">
                  Summary
                </h3>
                <div className="prose prose-sm max-w-none">
                  <p className="text-gray-700 leading-relaxed">
                    {summary.summary}
                  </p>
                </div>
              </div>

              {/* Action Items Section */}
              <div>
                <div className="flex items-center justify-between mb-4">
                  <h3 className="text-sm font-semibold text-gray-900">
                    Action Items ({summary.tasks.length})
                  </h3>
                  <div className="flex items-center gap-1 text-xs text-gray-500">
                    <CheckCircle2 className="h-3 w-3" />
                    {summary.tasks.filter((t) => t.completed).length} completed
                  </div>
                </div>

                <div className="space-y-3">
                  {summary.tasks.map((task) => (
                    <div
                      key={task.id}
                      className="flex items-start gap-3 p-3 rounded-lg border border-gray-200 hover:border-gray-300 transition-colors"
                    >
                      <Checkbox
                        checked={task.completed}
                        onCheckedChange={() => onTaskToggle(task.id)}
                        className="mt-0.5"
                      />
                      <span
                        className={`text-sm flex-1 ${
                          task.completed
                            ? "line-through text-gray-500"
                            : "text-gray-900"
                        }`}
                      >
                        {task.text}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>

          {/* Footer Actions */}
          <div className="px-6 py-4 border-t border-gray-200 bg-gray-50">
            <Button
              variant="outline"
              className="w-full bg-white hover:bg-gray-50"
            >
              <ExternalLink className="mr-2 h-4 w-4" />
              View in Google Tasks
            </Button>
          </div>
        </div>
      </SheetContent>
    </Sheet>
  );
}

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
import {
  ExternalLink,
  CheckCircle2,
  Circle,
  Clock,
  FileText,
  RefreshCw,
  CheckCheck,
} from "lucide-react";
import { formatDistanceToNow } from "date-fns";
import { MeetingSummary, apiService } from "@/lib/api";
import { useState } from "react";

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
  const [syncing, setSyncing] = useState(false);
  const [syncResult, setSyncResult] = useState<{
    success: boolean;
    message: string;
    tasks_synced?: number;
    task_list_url?: string;
  } | null>(null);

  const handleSyncToGoogleTasks = async () => {
    if (!summary) return;

    setSyncing(true);
    setSyncResult(null);

    try {
      const result = await apiService.syncTasksToGoogle(summary.id);
      setSyncResult(result);

      if (result.success) {
        // Auto-dismiss success message after 3 seconds
        setTimeout(() => setSyncResult(null), 3000);
      }
    } catch (error) {
      console.error("Failed to sync tasks to Google Tasks:", error);
      setSyncResult({
        success: false,
        message: "Failed to sync tasks to Google Tasks",
      });
    } finally {
      setSyncing(false);
    }
  };

  const handleOpenInGoogleTasks = () => {
    // If we have a specific task list URL from sync, use that
    if (syncResult?.success && syncResult.task_list_url) {
      window.open(syncResult.task_list_url, "_blank");
    } else {
      // Fallback to general Google Tasks URL
      window.open("https://tasks.google.com", "_blank");
    }
  };

  if (!summary) return null;

  const completedTasks = summary.tasks.filter((task) => task.completed).length;
  const totalTasks = summary.tasks.length;

  return (
    <Sheet open={open} onOpenChange={onClose}>
      <SheetContent className="w-full sm:w-[600px] sm:max-w-none">
        <div className="flex flex-col h-full">
          <SheetHeader className="flex-shrink-0 pb-6">
            <div className="flex items-start justify-between">
              <div className="flex-1">
                <SheetTitle className="text-xl font-semibold text-gray-900 mb-2 pr-4">
                  {summary.title}
                </SheetTitle>
                <div className="flex items-center gap-4 text-sm text-gray-500">
                  <div className="flex items-center gap-1">
                    <Clock className="h-4 w-4" />
                    {new Date(summary.createdAt).toLocaleDateString()}
                  </div>
                  <div className="flex items-center gap-1">
                    <FileText className="h-4 w-4" />
                    {summary.tasks.length} tasks
                  </div>
                </div>
              </div>
            </div>
          </SheetHeader>

          <div className="flex-1 overflow-y-auto space-y-6">
            {/* Summary Section */}
            <div>
              <h3 className="text-lg font-medium text-gray-900 mb-3">
                Meeting Summary
              </h3>
              <div className="bg-gray-50 rounded-lg p-4">
                <p className="text-gray-700 leading-relaxed">
                  {summary.summary}
                </p>
              </div>
            </div>

            {/* Tasks Section */}
            {summary.tasks.length > 0 && (
              <div>
                <div className="flex items-center justify-between mb-4">
                  <h3 className="text-lg font-medium text-gray-900">
                    Action Items
                  </h3>
                  <Badge
                    variant="outline"
                    className="bg-blue-50 text-blue-700 border-blue-200"
                  >
                    {completedTasks}/{totalTasks} completed
                  </Badge>
                </div>

                {/* Google Tasks Sync Section */}
                <div className="mb-6 p-4 bg-blue-50 border border-blue-200 rounded-lg">
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <CheckCheck className="h-5 w-5 text-blue-600" />
                      <span className="font-medium text-blue-900">
                        Sync to Google Tasks
                      </span>
                    </div>
                  </div>

                  {syncResult && (
                    <div
                      className={`mb-3 p-3 rounded-md ${
                        syncResult.success
                          ? "bg-green-50 border border-green-200"
                          : "bg-red-50 border border-red-200"
                      }`}
                    >
                      <p
                        className={`text-sm ${
                          syncResult.success ? "text-green-800" : "text-red-800"
                        }`}
                      >
                        {syncResult.success ? "✅ " : "❌ "}
                        {syncResult.message}
                        {syncResult.tasks_synced &&
                          syncResult.tasks_synced > 0 &&
                          ` (${syncResult.tasks_synced} tasks synced)`}
                      </p>
                    </div>
                  )}

                  <div className="flex gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={handleSyncToGoogleTasks}
                      disabled={syncing || totalTasks === 0}
                      className="flex-1 bg-white hover:bg-blue-50"
                    >
                      {syncing ? (
                        <>
                          <RefreshCw className="mr-2 h-4 w-4 animate-spin" />
                          Syncing...
                        </>
                      ) : (
                        <>
                          <CheckCheck className="mr-2 h-4 w-4" />
                          Sync to Google Tasks
                        </>
                      )}
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={handleOpenInGoogleTasks}
                      className="bg-white hover:bg-blue-50"
                    >
                      <ExternalLink className="h-4 w-4" />
                    </Button>
                  </div>

                  <p className="text-xs text-blue-600 mt-2">
                    Create tasks in your Google Tasks app for easy mobile access
                  </p>
                </div>

                {/* Tasks List */}
                <div className="space-y-3">
                  {summary.tasks.map((task) => (
                    <div
                      key={task.id}
                      className="flex items-start gap-3 p-3 bg-white border border-gray-200 rounded-lg hover:border-gray-300 transition-colors"
                    >
                      <button
                        onClick={() => onTaskToggle(task.id)}
                        className="flex-shrink-0 mt-0.5"
                      >
                        {task.completed ? (
                          <CheckCircle2 className="h-5 w-5 text-green-600" />
                        ) : (
                          <Circle className="h-5 w-5 text-gray-400 hover:text-gray-600" />
                        )}
                      </button>
                      <span
                        className={`text-sm leading-relaxed ${
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
            )}
          </div>
        </div>
      </SheetContent>
    </Sheet>
  );
}

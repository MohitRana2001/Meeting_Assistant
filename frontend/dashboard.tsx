"use client";

import { useState, useEffect } from "react";
import { Sidebar } from "./components/sidebar";
import { TopBar } from "./components/top-bar";
import { MeetingSummaryTable } from "./components/meeting-summary-table";
import { DetailsDrawer } from "./components/details-drawer";
import { ToastNotification } from "./components/toast-notification";
import { EmptyState } from "./components/empty-state";
import { ReconnectBanner } from "./components/reconnect-banner";
import { CalendarView } from "@/components/calendar-view";
import { SettingsView } from "@/components/settings-view";
import { apiService, MeetingSummary } from "./lib/api";
import { useRouter, useSearchParams } from "next/navigation";
import { RefreshCw, CheckCheck, Mail } from "lucide-react";
import { Button } from "@/components/ui/button";

export default function Dashboard() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [activeView, setActiveView] = useState("dashboard");
  const [selectedSummary, setSelectedSummary] = useState<MeetingSummary | null>(
    null
  );
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [showToast, setShowToast] = useState(false);
  const [toastMessage, setToastMessage] = useState("");
  const [showReconnectBanner, setShowReconnectBanner] = useState(false);
  const [summaries, setSummaries] = useState<MeetingSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [syncingTasks, setSyncingTasks] = useState(false);
  const [scanningGmail, setScanningGmail] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [gmailSummariesCount, setGmailSummariesCount] = useState(0);
  const [driveSummariesCount, setDriveSummariesCount] = useState(0);

  // Handle OAuth token from URL
  useEffect(() => {
    const token = searchParams.get("token");
    if (token) {
      // Store the token in localStorage
      localStorage.setItem("auth_token", token);
      // Clean up the URL by removing the token parameter
      const url = new URL(window.location.href);
      url.searchParams.delete("token");
      window.history.replaceState({}, "", url.toString());
      console.log("Auth token stored successfully");
    }
  }, [searchParams]);

  // Load summaries from API
  useEffect(() => {
    if (activeView === "dashboard") {
      loadSummaries();
    }
  }, [activeView]);

  const loadSummaries = async () => {
    try {
      setLoading(true);
      setError(null);

      // First check if user is authenticated
      const isAuth = await apiService.isAuthenticated();
      if (!isAuth) {
        setShowReconnectBanner(true);
        setLoading(false);
        return;
      }

      // Load combined summaries (Drive + Gmail)
      const data = await apiService.getCombinedSummaries(true, 7);
      if (data.success) {
        setSummaries(data.summaries);
        setDriveSummariesCount(data.drive_summaries);
        setGmailSummariesCount(data.gmail_summaries);
      } else {
        // Fallback to Drive-only summaries
        const driveData = await apiService.getSummaries();
        setSummaries(driveData);
        setDriveSummariesCount(driveData.length);
        setGmailSummariesCount(0);
      }
    } catch (err) {
      console.error("Failed to load summaries:", err);
      setError("Failed to load meeting summaries");
      setShowReconnectBanner(true);
    } finally {
      setLoading(false);
    }
  };

  const handleRefreshSummaries = async () => {
    try {
      setRefreshing(true);
      setError(null);

      const result = await apiService.refreshSummaries();

      if (result.success) {
        // Reload summaries to show any new ones
        await loadSummaries();

        if (result.summaries_created && result.summaries_created > 0) {
          setToastMessage(
            `✅ Found and processed ${result.summaries_created} new meeting${
              result.summaries_created > 1 ? "s" : ""
            } from Drive!`
          );
        } else {
          setToastMessage("✅ Drive sync complete - no new meetings found");
        }
        setShowToast(true);
      } else {
        setError(result.message || "Failed to refresh summaries");
      }
    } catch (err) {
      console.error("Failed to refresh summaries:", err);
      setError("Failed to refresh summaries");
    } finally {
      setRefreshing(false);
    }
  };

  const handleScanGmail = async () => {
    try {
      setScanningGmail(true);
      setError(null);

      const result = await apiService.scanGmail(7);

      if (result.success) {
        // Reload summaries to show Gmail + Drive summaries together
        await loadSummaries();

        if (result.summaries_found > 0) {
          setToastMessage(
            `📧 Found ${result.summaries_found} meeting summaries in Gmail!`
          );
        } else {
          setToastMessage(
            "📧 Gmail scan complete - no meeting summaries found"
          );
        }
        setShowToast(true);
      } else {
        setError(result.message || "Failed to scan Gmail");
      }
    } catch (err) {
      console.error("Failed to scan Gmail:", err);
      setError("Failed to scan Gmail for meeting summaries");
    } finally {
      setScanningGmail(false);
    }
  };

  const handleSyncAllTasks = async () => {
    try {
      setSyncingTasks(true);
      setError(null);

      const result = await apiService.syncAllTasksToGoogle(10);

      if (result.success) {
        if (result.total_tasks_synced > 0) {
          setToastMessage(
            `🎉 Synced ${result.total_tasks_synced} tasks from ${result.summaries_processed} meetings to Google Tasks!`
          );
        } else {
          setToastMessage("✅ All tasks are already up to date");
        }
        setShowToast(true);
      } else {
        setError(result.message || "Failed to sync tasks");
      }
    } catch (err) {
      console.error("Failed to sync all tasks:", err);
      setError("Failed to sync tasks to Google Tasks");
    } finally {
      setSyncingTasks(false);
    }
  };

  const handleRowSelect = (summary: MeetingSummary) => {
    setSelectedSummary(summary);
    setDrawerOpen(true);
  };

  const handleTaskToggle = async (taskId: string) => {
    if (!selectedSummary) return;

    // Only allow task toggling for Drive summaries (not Gmail ones)
    if (selectedSummary.source === "gmail") {
      setToastMessage(
        "⚠️ Cannot edit tasks from Gmail summaries. Sync to Google Tasks instead!"
      );
      setShowToast(true);
      return;
    }

    // Find the current task to get its completion status
    const currentTask = selectedSummary.tasks.find(
      (task) => task.id === taskId
    );
    if (!currentTask) return;

    const newCompletedStatus = !currentTask.completed;

    // Optimistic UI update
    const updatedSummary = {
      ...selectedSummary,
      tasks: selectedSummary.tasks.map((task) =>
        task.id === taskId ? { ...task, completed: newCompletedStatus } : task
      ),
    };

    setSelectedSummary(updatedSummary);
    setSummaries((prev) =>
      prev.map((s) => (s.id === selectedSummary.id ? updatedSummary : s))
    );

    // Call the enhanced API to update both local and Google Tasks
    try {
      const result = await apiService.updateTaskStatusWithGoogleSync(
        selectedSummary.id,
        taskId,
        newCompletedStatus
      );

      if (result.success) {
        // Show different messages based on Google Tasks sync status
        if (result.google_task_updated) {
          setToastMessage(
            `✅ Task ${
              newCompletedStatus ? "completed" : "reopened"
            } in both local and Google Tasks!`
          );
        } else {
          setToastMessage(
            `✅ Task ${
              newCompletedStatus ? "completed" : "reopened"
            } locally. ${
              result.message || "Google Tasks sync may have failed."
            }`
          );
        }
        setShowToast(true);
      } else {
        console.error("Failed to update task status:", result.message);
        // Revert the optimistic update if API call failed
        setSelectedSummary(selectedSummary);
        setSummaries((prev) =>
          prev.map((s) => (s.id === selectedSummary.id ? selectedSummary : s))
        );
      }
    } catch (error) {
      console.error("Error updating task status:", error);
      // Revert the optimistic update if API call failed
      setSelectedSummary(selectedSummary);
      setSummaries((prev) =>
        prev.map((s) => (s.id === selectedSummary.id ? selectedSummary : s))
      );
    }
  };

  const handleConnect = () => {
    // Redirect to Google OAuth
    window.location.href = apiService.getGoogleAuthUrl();
  };

  const handleReconnect = () => {
    // Redirect to Google OAuth restart
    window.location.href = apiService.getGoogleAuthRestartUrl();
  };

  const handleDismissReconnect = () => {
    setShowReconnectBanner(false);
  };

  const handleViewChange = (view: string) => {
    setActiveView(view);
    setDrawerOpen(false); // Close drawer when switching views
  };

  const getPageTitle = () => {
    switch (activeView) {
      case "calendar":
        return "Calendar";
      case "settings":
        return "Settings";
      default:
        return "Summaries";
    }
  };

  const getTopBarActions = () => {
    if (activeView === "dashboard") {
      const totalTasks = summaries.reduce(
        (count, summary) => count + (summary.tasks?.length || 0),
        0
      );

      return (
        <div className="flex items-center gap-2">
          {totalTasks > 0 && (
            <Button
              variant="outline"
              size="sm"
              onClick={handleSyncAllTasks}
              disabled={syncingTasks || loading}
              className="flex items-center gap-2"
            >
              {syncingTasks ? (
                <>
                  <RefreshCw className="h-4 w-4 animate-spin" />
                  Syncing...
                </>
              ) : (
                <>
                  <CheckCheck className="h-4 w-4" />
                  Sync All Tasks
                </>
              )}
            </Button>
          )}
          <Button
            variant="outline"
            size="sm"
            onClick={handleScanGmail}
            disabled={scanningGmail || loading}
            className="flex items-center gap-2"
          >
            {scanningGmail ? (
              <>
                <RefreshCw className="h-4 w-4 animate-spin" />
                Scanning...
              </>
            ) : (
              <>
                <Mail className="h-4 w-4" />
                Scan Gmail
              </>
            )}
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={handleRefreshSummaries}
            disabled={refreshing || loading}
            className="flex items-center gap-2"
          >
            <RefreshCw
              className={`h-4 w-4 ${refreshing ? "animate-spin" : ""}`}
            />
            {refreshing ? "Syncing..." : "Sync Drive"}
          </Button>
        </div>
      );
    }
    return null;
  };

  // Simulate real-time updates
  useEffect(() => {
    // Removed simulated notifications - now using real API notifications
    // const interval = setInterval(() => {
    //   // Randomly show toast notification
    //   if (
    //     Math.random() > 0.7 &&
    //     summaries.length > 0 &&
    //     activeView === "dashboard"
    //   ) {
    //     setShowToast(true);
    //   }
    // }, 30000); // Every 30 seconds
    // return () => clearInterval(interval);
  }, [summaries, activeView]);

  const isEmpty =
    summaries.length === 0 && !loading && activeView === "dashboard";

  const renderMainContent = () => {
    if (activeView === "calendar") {
      return <CalendarView />;
    }

    if (activeView === "settings") {
      return <SettingsView onReconnect={handleReconnect} />;
    }

    // Dashboard view
    if (loading) {
      return (
        <div className="h-full p-6 flex items-center justify-center">
          <div className="text-center">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600 mx-auto mb-4"></div>
            <p className="text-gray-600">Loading meeting summaries...</p>
          </div>
        </div>
      );
    }

    return (
      <div className="h-full p-6">
        {showReconnectBanner && (
          <ReconnectBanner
            onReconnect={handleReconnect}
            onDismiss={handleDismissReconnect}
          />
        )}

        {/* Summary Stats */}
        {summaries.length > 0 && (
          <div className="mb-4 p-4 bg-blue-50 border border-blue-200 rounded-lg">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-4">
                <span className="text-sm font-medium text-blue-900">
                  📁 Drive: {driveSummariesCount} summaries
                </span>
                <span className="text-sm font-medium text-blue-900">
                  📧 Gmail: {gmailSummariesCount} summaries
                </span>
                <span className="text-sm font-medium text-blue-900">
                  🔄 Total: {summaries.length} summaries
                </span>
              </div>
              <div className="text-xs text-blue-600">
                Gmail scans last 7 days for shared meeting summaries
              </div>
            </div>
          </div>
        )}

        {error && (
          <div className="mb-4 p-4 bg-red-50 border border-red-200 rounded-lg">
            <p className="text-red-800">{error}</p>
            <button
              onClick={loadSummaries}
              className="mt-2 text-red-600 hover:text-red-800 underline"
            >
              Try again
            </button>
          </div>
        )}

        {isEmpty ? (
          <EmptyState onConnect={handleConnect} />
        ) : (
          <MeetingSummaryTable
            summaries={summaries}
            onRowSelect={handleRowSelect}
            selectedSummary={selectedSummary || undefined}
          />
        )}
      </div>
    );
  };

  return (
    <div className="flex h-screen bg-gray-50">
      <Sidebar
        collapsed={sidebarCollapsed}
        onToggle={() => setSidebarCollapsed(!sidebarCollapsed)}
        activeItem={activeView}
        onItemSelect={handleViewChange}
      />

      <div className="flex-1 flex flex-col min-w-0">
        <TopBar pageTitle={getPageTitle()} actions={getTopBarActions()} />
        <main className="flex-1 overflow-hidden">{renderMainContent()}</main>
      </div>

      <DetailsDrawer
        summary={selectedSummary}
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        onTaskToggle={handleTaskToggle}
      />

      <ToastNotification
        message={toastMessage}
        show={showToast}
        onClose={() => setShowToast(false)}
      />
    </div>
  );
}

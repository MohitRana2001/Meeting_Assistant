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
import { RefreshCw } from "lucide-react";
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
  const [error, setError] = useState<string | null>(null);

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

      const data = await apiService.getSummaries();
      setSummaries(data);
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
            }!`
          );
        } else {
          setToastMessage("✅ Sync complete - no new meetings found");
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

  const handleRowSelect = (summary: MeetingSummary) => {
    setSelectedSummary(summary);
    setDrawerOpen(true);
  };

  const handleTaskToggle = async (taskId: string) => {
    if (!selectedSummary) return;

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

    // Call the API to persist the change
    try {
      const result = await apiService.updateTaskStatus(
        selectedSummary.id,
        taskId,
        newCompletedStatus
      );

      if (!result.success) {
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
      return (
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

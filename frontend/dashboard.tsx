"use client";

import { useState, useEffect } from "react";
import { Sidebar } from "./components/sidebar";
import { TopBar } from "./components/top-bar";
import { MeetingSummaryTable } from "./components/meeting-summary-table";
import { DetailsDrawer } from "./components/details-drawer";
import { ToastNotification } from "./components/toast-notification";
import { EmptyState } from "./components/empty-state";
import { ReconnectBanner } from "./components/reconnect-banner";
import { apiService, MeetingSummary } from "./lib/api";
import { useRouter } from "next/navigation";

export default function Dashboard() {
  const router = useRouter();
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [selectedSummary, setSelectedSummary] = useState<MeetingSummary | null>(
    null
  );
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [showToast, setShowToast] = useState(false);
  const [showReconnectBanner, setShowReconnectBanner] = useState(false);
  const [summaries, setSummaries] = useState<MeetingSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Load summaries from API
  useEffect(() => {
    loadSummaries();
  }, []);

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

  const handleRowSelect = (summary: MeetingSummary) => {
    setSelectedSummary(summary);
    setDrawerOpen(true);
  };

  const handleTaskToggle = async (taskId: string) => {
    if (!selectedSummary) return;

    // Optimistic UI update
    const updatedSummary = {
      ...selectedSummary,
      tasks: selectedSummary.tasks.map((task) =>
        task.id === taskId ? { ...task, completed: !task.completed } : task
      ),
    };

    setSelectedSummary(updatedSummary);
    setSummaries((prev) =>
      prev.map((s) => (s.id === selectedSummary.id ? updatedSummary : s))
    );

    // TODO: In a real app, this would sync via API
    console.log(`Task ${taskId} toggled`);
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

  // Simulate real-time updates
  useEffect(() => {
    const interval = setInterval(() => {
      // Randomly show toast notification
      if (Math.random() > 0.7 && summaries.length > 0) {
        setShowToast(true);
      }
    }, 30000); // Every 30 seconds

    return () => clearInterval(interval);
  }, [summaries]);

  const isEmpty = summaries.length === 0 && !loading;

  if (loading) {
    return (
      <div className="flex h-screen bg-gray-50">
        <Sidebar
          collapsed={sidebarCollapsed}
          onToggle={() => setSidebarCollapsed(!sidebarCollapsed)}
        />
        <div className="flex-1 flex flex-col min-w-0">
          <TopBar pageTitle="Summaries" />
          <main className="flex-1 overflow-hidden">
            <div className="h-full p-6 flex items-center justify-center">
              <div className="text-center">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600 mx-auto mb-4"></div>
                <p className="text-gray-600">Loading meeting summaries...</p>
              </div>
            </div>
          </main>
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-screen bg-gray-50">
      <Sidebar
        collapsed={sidebarCollapsed}
        onToggle={() => setSidebarCollapsed(!sidebarCollapsed)}
      />

      <div className="flex-1 flex flex-col min-w-0">
        <TopBar pageTitle="Summaries" />

        <main className="flex-1 overflow-hidden">
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
                selectedSummary={selectedSummary}
              />
            )}
          </div>
        </main>
      </div>

      <DetailsDrawer
        summary={selectedSummary}
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        onTaskToggle={handleTaskToggle}
      />

      <ToastNotification
        message="New meeting processed ⚡ Ready to review."
        show={showToast}
        onClose={() => setShowToast(false)}
      />
    </div>
  );
}

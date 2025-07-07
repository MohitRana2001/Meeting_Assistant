"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import {
  Bot,
  Zap,
  Calendar,
  BarChart,
} from "lucide-react";
import { apiService } from "@/lib/api";

export default function LandingPage() {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const checkAuthStatus = async () => {
      try {
        // apiService checks for token in localStorage and validates it
        const authStatus = await apiService.isAuthenticated();
        setIsAuthenticated(authStatus);
      } catch (error) {
        console.error("Auth check failed:", error);
        setIsAuthenticated(false);
      } finally {
        setIsLoading(false);
      }
    };

    checkAuthStatus();
  }, []);

  return (
    <div className="flex flex-col min-h-screen bg-white">
      {/* Header */}
      <header className="px-4 lg:px-6 h-16 flex items-center border-b bg-white sticky top-0 z-50">
        <Link href="#" className="flex items-center gap-3">
          <div className="flex items-center justify-center w-8 h-8 bg-indigo-100 rounded-lg">
            <Bot className="w-5 h-5 text-indigo-600" />
          </div>
          <span className="font-semibold text-gray-900 text-lg">
            MeetingMate
          </span>
        </Link>
        <nav className="ml-auto flex gap-4 sm:gap-6">
          {isLoading ? (
            <Button disabled variant="ghost" size="sm">Loading...</Button>
          ) : isAuthenticated ? (
            <Button asChild size="sm" className="bg-indigo-600 text-white hover:bg-indigo-700">
              <Link href="/dashboard">Go to Dashboard</Link>
            </Button>
          ) : (
            <>
              <Button asChild variant="ghost" size="sm">
                <Link href="/dashboard">Login</Link>
              </Button>
              <Button asChild size="sm" className="bg-indigo-600 text-white hover:bg-indigo-700">
                <Link href="/dashboard">Get Started</Link>
              </Button>
            </>
          )}
        </nav>
      </header>

      <main className="flex-1">
        {/* Hero Section */}
        <section className="w-full py-20 md:py-32 lg:py-40 bg-gray-50">
          <div className="container px-4 md:px-6">
            <div className="grid gap-6 lg:grid-cols-[1fr_400px] lg:gap-12 xl:grid-cols-[1fr_600px]">
              <div className="flex flex-col justify-center space-y-4">
                <div className="space-y-2">
                  <h1 className="text-3xl font-bold tracking-tighter text-gray-900 sm:text-5xl xl:text-6xl/none">
                    Turn Conversations into Actions
                  </h1>
                  <p className="max-w-[600px] text-gray-600 md:text-xl">
                    MeetingMate automatically transcribes your meetings,
                    extracts key tasks, and syncs them with your favorite
                    tools. Stop taking notes and start getting things done.
                  </p>
                </div>
                <div className="flex flex-col gap-2 min-[400px]:flex-row">
                  {isAuthenticated ? (
                    <Button asChild size="lg" className="bg-indigo-600 text-white hover:bg-indigo-700">
                      <Link href="/dashboard">Go to Dashboard</Link>
                    </Button>
                  ) : (
                    <Button asChild size="lg" className="bg-indigo-600 text-white hover:bg-indigo-700">
                      <Link href="/dashboard">Get Started for Free</Link>
                    </Button>
                  )}
                </div>
              </div>
              <img
                src="https://images.unsplash.com/photo-1556761175-5973dc0f32e7?q=80&w=2832&auto=format&fit=crop"
                width="550"
                height="550"
                alt="Collaboration"
                className="mx-auto aspect-video overflow-hidden rounded-xl object-cover sm:w-full lg:order-last lg:aspect-square"
              />
            </div>
          </div>
        </section>

        {/* Features Section */}
        <section id="features" className="w-full py-12 md:py-24 lg:py-32">
          <div className="container px-4 md:px-6">
            <div className="flex flex-col items-center justify-center space-y-4 text-center">
              <div className="space-y-2">
                <div className="inline-block rounded-lg bg-indigo-50 px-3 py-1 text-sm text-indigo-600">
                  Key Features
                </div>
                <h2 className="text-3xl font-bold tracking-tighter text-gray-900 sm:text-5xl">
                  Everything You Need, Automated
                </h2>
                <p className="max-w-[900px] text-gray-600 md:text-xl/relaxed lg:text-base/relaxed xl:text-xl/relaxed">
                  Focus on the conversation, not on the note-taking. Our AI
                  handles the heavy lifting.
                </p>
              </div>
            </div>
            <div className="mx-auto grid max-w-5xl items-start gap-8 py-12 sm:grid-cols-2 md:gap-12 lg:grid-cols-3">
              <div className="grid gap-1 text-center">
                <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-indigo-100">
                  <Zap className="h-6 w-6 text-indigo-600" />
                </div>
                <h3 className="text-lg font-bold text-gray-900">
                  Automatic Task Extraction
                </h3>
                <p className="text-sm text-gray-600">
                  Never miss an action item. Our AI identifies tasks,
                  assignees, and deadlines from your meeting transcripts.
                </p>
              </div>
              <div className="grid gap-1 text-center">
                <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-indigo-100">
                  <Calendar className="h-6 w-6 text-indigo-600" />
                </div>
                <h3 className="text-lg font-bold text-gray-900">
                  Seamless Google Integration
                </h3>
                <p className="text-sm text-gray-600">
                  Syncs directly with Google Tasks and Google Calendar,
                  putting your action items where you need them.
                </p>
              </div>
              <div className="grid gap-1 text-center">
                <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-indigo-100">
                  <BarChart className="h-6 w-6 text-indigo-600" />
                </div>
                <h3 className="text-lg font-bold text-gray-900">
                  Intelligent Summaries
                </h3>
                <p className="text-sm text-gray-600">
                  Get concise, AI-generated summaries of your meetings,
                  perfect for quick reviews and sharing with stakeholders.
                </p>
              </div>
            </div>
          </div>
        </section>
      </main>

      {/* Footer */}
      <footer className="flex flex-col gap-2 sm:flex-row py-6 w-full shrink-0 items-center px-4 md:px-6 border-t">
        <p className="text-xs text-gray-500">
          &copy; 2024 MeetingMate. All rights reserved.
        </p>
        <nav className="sm:ml-auto flex gap-4 sm:gap-6">
          <Link
            href="#"
            className="text-xs hover:underline underline-offset-4 text-gray-600"
          >
            Terms of Service
          </Link>
          <Link
            href="#"
            className="text-xs hover:underline underline-offset-4 text-gray-600"
          >
            Privacy
          </Link>
        </nav>
      </footer>
    </div>
  );
}

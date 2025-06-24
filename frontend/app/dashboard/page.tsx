"use client";

import { Suspense } from "react";
import Dashboard from "../../dashboard";

function DashboardContent() {
  return <Dashboard />;
}

export default function DashboardPage() {
  return (
    <Suspense fallback={<div>Loading...</div>}>
      <DashboardContent />
    </Suspense>
  );
}

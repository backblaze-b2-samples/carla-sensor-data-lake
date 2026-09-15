import Link from "next/link";
import { Plus } from "lucide-react";

import { Button } from "@/components/ui/button";
import { LakeStatsCards } from "@/components/dashboard/lake-stats-cards";
import { IngestChart } from "@/components/dashboard/ingest-chart";
import { RecentEpisodes } from "@/components/dashboard/recent-episodes";
import { LakeBreakdown } from "@/components/dashboard/lake-breakdown";

export default function DashboardPage() {
  return (
    <div className="space-y-8">
      <div className="animate-fade-in border-b border-border pb-5 flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="page-title">Dashboard</h1>
          <p className="text-sm text-muted-foreground mt-1.5">
            Your synthetic autonomous-driving data lake on Backblaze B2.
          </p>
        </div>
        <Button asChild size="sm" className="h-8">
          <Link href="/scenarios/new">
            <Plus className="h-3.5 w-3.5" />
            New scenario
          </Link>
        </Button>
      </div>
      <LakeStatsCards />
      <div className="grid gap-6 lg:grid-cols-2">
        <div className="animate-fade-in-up stagger-3">
          <IngestChart />
        </div>
        <div className="animate-fade-in-up stagger-4">
          <RecentEpisodes />
        </div>
      </div>
      <LakeBreakdown />
    </div>
  );
}

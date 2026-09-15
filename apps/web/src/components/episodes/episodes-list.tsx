"use client";

import { Film } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/ui/empty-state";
import { ErrorState } from "@/components/ui/error-state";
import { EpisodesTable } from "./episodes-table";
import { useEpisodes } from "@/lib/queries";

export function EpisodesList() {
  const { data: episodes = [], isLoading, error, refetch } = useEpisodes();

  return (
    <Card>
      <CardHeader className="border-b border-border py-4 px-5">
        <CardTitle className="card-title">Episodes</CardTitle>
      </CardHeader>
      <CardContent className="p-0">
        {isLoading ? (
          <div className="p-4 space-y-3">
            {Array.from({ length: 5 }).map((_, i) => (
              <Skeleton key={i} className="h-10 w-full" />
            ))}
          </div>
        ) : error ? (
          <ErrorState error={error} onRetry={() => refetch()} />
        ) : episodes.length === 0 ? (
          <EmptyState
            icon={Film}
            title="No episodes yet"
            description="Run a scenario to capture an episode, or seed synthetic demo data with scripts/seed_lake.py."
          />
        ) : (
          <EpisodesTable episodes={episodes} />
        )}
      </CardContent>
    </Card>
  );
}

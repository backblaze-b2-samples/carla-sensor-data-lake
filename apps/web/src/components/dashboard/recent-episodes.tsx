"use client";

import Link from "next/link";
import { ArrowRight, Inbox } from "lucide-react";
import {
  Card,
  CardAction,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/ui/empty-state";
import { ErrorState } from "@/components/ui/error-state";
import { EpisodesTable } from "@/components/episodes/episodes-table";
import { useEpisodes } from "@/lib/queries";

export function RecentEpisodes() {
  const { data: episodes = [], isLoading, error, refetch } = useEpisodes();

  return (
    <Card>
      <CardHeader className="border-b border-border py-4 px-5">
        <CardTitle className="card-title">Recent Episodes</CardTitle>
        <CardAction className="self-center">
          <Link
            href="/episodes"
            className="inline-flex items-center gap-1 text-xs font-medium text-muted-foreground hover:text-foreground transition-colors"
          >
            View all
            <ArrowRight className="h-3 w-3" />
          </Link>
        </CardAction>
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
            icon={Inbox}
            title="No episodes yet"
            description="Run a scenario or seed synthetic demo data to populate the lake."
          />
        ) : (
          <EpisodesTable episodes={episodes.slice(0, 5)} />
        )}
      </CardContent>
    </Card>
  );
}

"use client";

import Link from "next/link";
import { Clapperboard, Plus } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/ui/empty-state";
import { ErrorState } from "@/components/ui/error-state";
import { useScenarios } from "@/lib/queries";
import { formatDate } from "@/lib/utils";

export function ScenariosList() {
  const { data: scenarios = [], isLoading, error, refetch } = useScenarios();

  return (
    <Card>
      <CardHeader className="border-b border-border py-4 px-5">
        <CardTitle className="card-title">Scenarios</CardTitle>
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
        ) : scenarios.length === 0 ? (
          <EmptyState
            icon={Clapperboard}
            title="No scenarios yet"
            description="Create a reusable CARLA capture config to get started."
            action={
              <Button asChild size="sm">
                <Link href="/scenarios/new">
                  <Plus aria-hidden="true" className="h-3.5 w-3.5" />
                  New scenario
                </Link>
              </Button>
            }
          />
        ) : (
          <Table>
            <TableHeader>
              <TableRow className="bg-muted/40 hover:bg-muted/40">
                <TableHead className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                  Name
                </TableHead>
                <TableHead className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                  Town / Weather
                </TableHead>
                <TableHead className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                  Traffic
                </TableHead>
                <TableHead className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                  FPS
                </TableHead>
                <TableHead className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                  Frames
                </TableHead>
                <TableHead className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                  Sensors
                </TableHead>
                <TableHead className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                  Updated
                </TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {scenarios.map((s) => (
                <TableRow key={s.id} className="table-row-hover">
                  <TableCell className="font-medium">
                    <Link
                      href={`/scenarios/${s.id}`}
                      className="underline-offset-4 hover:underline"
                    >
                      {s.name}
                    </Link>
                  </TableCell>
                  <TableCell className="text-muted-foreground whitespace-nowrap">
                    {s.town} · {s.weather}
                  </TableCell>
                  <TableCell className="text-muted-foreground capitalize">
                    {s.traffic_density}
                  </TableCell>
                  <TableCell className="font-mono text-xs tabular-nums">
                    {s.fps}
                  </TableCell>
                  <TableCell className="font-mono text-xs tabular-nums">
                    {s.frame_count}
                  </TableCell>
                  <TableCell>
                    <Badge variant="secondary">{s.sensors.length}</Badge>
                  </TableCell>
                  <TableCell className="text-muted-foreground whitespace-nowrap">
                    {formatDate(s.updated_at)}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </CardContent>
    </Card>
  );
}

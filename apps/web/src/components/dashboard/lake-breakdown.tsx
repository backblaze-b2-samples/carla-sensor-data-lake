"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useLakeStats } from "@/lib/queries";
import { SENSOR_LABELS } from "@/lib/scenario-config";

interface Row {
  label: string;
  value: number;
}

function BreakdownCard({
  title,
  rows,
  isLoading,
}: {
  title: string;
  rows: Row[];
  isLoading: boolean;
}) {
  const max = Math.max(1, ...rows.map((r) => r.value));
  return (
    <Card>
      <CardHeader className="border-b border-border py-4 px-5">
        <CardTitle className="card-title">{title}</CardTitle>
      </CardHeader>
      <CardContent className="p-5 space-y-3">
        {isLoading ? (
          Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-5 w-full" />
          ))
        ) : rows.length === 0 ? (
          <p className="text-sm text-muted-foreground">No data yet.</p>
        ) : (
          rows.map((row) => (
            <div key={row.label} className="space-y-1">
              <div className="flex items-center justify-between text-sm">
                <span className="truncate">{row.label}</span>
                <span className="font-mono text-xs tabular-nums text-muted-foreground">
                  {row.value}
                </span>
              </div>
              <div className="h-1.5 w-full overflow-hidden rounded-full bg-muted">
                <div
                  className="h-full rounded-full bg-[var(--chart-1)]"
                  style={{ width: `${(row.value / max) * 100}%` }}
                />
              </div>
            </div>
          ))
        )}
      </CardContent>
    </Card>
  );
}

export function LakeBreakdown() {
  const { data: stats, isLoading } = useLakeStats();

  const sensors: Row[] = (stats?.frames_by_sensor ?? []).map((s) => ({
    label: SENSOR_LABELS[s.sensor] ?? s.sensor,
    value: s.frames,
  }));
  const weather: Row[] = (stats?.episodes_by_weather ?? []).map((g) => ({
    label: g.label,
    value: g.episodes,
  }));
  const towns: Row[] = (stats?.episodes_by_town ?? []).map((g) => ({
    label: g.label,
    value: g.episodes,
  }));

  return (
    <div className="grid gap-6 lg:grid-cols-3">
      <BreakdownCard title="Frames by sensor" rows={sensors} isLoading={isLoading} />
      <BreakdownCard title="Episodes by weather" rows={weather} isLoading={isLoading} />
      <BreakdownCard title="Episodes by town" rows={towns} isLoading={isLoading} />
    </div>
  );
}

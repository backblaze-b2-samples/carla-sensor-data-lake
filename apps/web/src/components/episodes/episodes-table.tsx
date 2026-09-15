"use client";

import Link from "next/link";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { formatDate } from "@/lib/utils";
import type { EpisodeSummary } from "@carla-sensor-data-lake/shared";

function StatusBadge({ status }: { status: string }) {
  const variant =
    status === "completed"
      ? "default"
      : status === "failed"
        ? "destructive"
        : "secondary";
  return <Badge variant={variant}>{status}</Badge>;
}

/** Presentational table of episodes. Callers own loading/empty/error states. */
export function EpisodesTable({ episodes }: { episodes: EpisodeSummary[] }) {
  return (
    <Table>
      <TableHeader>
        <TableRow className="bg-muted/40 hover:bg-muted/40">
          <TableHead className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
            Episode
          </TableHead>
          <TableHead className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
            Scenario
          </TableHead>
          <TableHead className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
            Town / Weather
          </TableHead>
          <TableHead className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
            Frames
          </TableHead>
          <TableHead className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
            Size
          </TableHead>
          <TableHead className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
            Source
          </TableHead>
          <TableHead className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
            Status
          </TableHead>
          <TableHead className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
            Created
          </TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {episodes.map((ep) => (
          <TableRow key={ep.id} className="table-row-hover">
            <TableCell className="font-medium">
              <Link
                href={`/episodes/${ep.id}`}
                className="font-mono text-xs underline-offset-4 hover:underline"
              >
                {ep.id}
              </Link>
            </TableCell>
            <TableCell className="text-muted-foreground">
              {ep.scenario_name ?? "—"}
            </TableCell>
            <TableCell className="text-muted-foreground whitespace-nowrap">
              {ep.town} · {ep.weather}
            </TableCell>
            <TableCell className="font-mono text-xs tabular-nums">
              {ep.captured_frames}
            </TableCell>
            <TableCell className="font-mono text-xs tabular-nums text-muted-foreground whitespace-nowrap">
              {ep.size_human}
            </TableCell>
            <TableCell>
              <Badge variant={ep.capture_source === "carla" ? "outline" : "secondary"}>
                {ep.capture_source === "carla" ? "CARLA" : "seed"}
              </Badge>
            </TableCell>
            <TableCell>
              <StatusBadge status={ep.status} />
            </TableCell>
            <TableCell className="text-muted-foreground whitespace-nowrap">
              {formatDate(ep.created_at)}
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}

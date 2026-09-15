"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { Pencil, Play, Trash2 } from "lucide-react";
import { toast } from "sonner";

import { Button, buttonVariants } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { ErrorState } from "@/components/ui/error-state";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import { EpisodesTable } from "@/components/episodes/episodes-table";
import { ApiError } from "@/lib/api-client";
import {
  useDeleteScenario,
  useEpisodes,
  useRunScenario,
  useScenario,
} from "@/lib/queries";
import { SENSOR_LABELS } from "@/lib/scenario-config";
import { formatDate } from "@/lib/utils";

function ConfigRow({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="flex items-center justify-between border-b border-border py-2 text-sm last:border-0">
      <span className="text-muted-foreground">{label}</span>
      <span className="font-medium">{value}</span>
    </div>
  );
}

export function ScenarioDetail({ scenarioId }: { scenarioId: string }) {
  const router = useRouter();
  const { data: scenario, isLoading, error, refetch } = useScenario(scenarioId);
  const runMutation = useRunScenario();
  const deleteMutation = useDeleteScenario();
  const { data: allEpisodes = [] } = useEpisodes();
  const episodes = allEpisodes.filter((e) => e.scenario_id === scenarioId);

  if (isLoading) {
    return <Skeleton className="h-64 w-full" />;
  }
  if (error) {
    return <ErrorState error={error} onRetry={() => refetch()} />;
  }
  if (!scenario) {
    return <ErrorState title="Scenario not found" onRetry={() => refetch()} />;
  }

  const handleRun = () => {
    const toastId = toast.loading("Requesting a CARLA run...");
    runMutation.mutate(scenarioId, {
      onSuccess: (episode) => {
        toast.success(`Episode ${episode.id} captured`, {
          id: toastId,
          description: `${episode.captured_frames} frames streamed to B2.`,
        });
        router.push(`/episodes/${episode.id}`);
      },
      onError: (err) => {
        const detail =
          err instanceof ApiError ? err.message : "Failed to start the run";
        // A 503 here is the documented "CARLA not on this host" case, not a bug.
        toast.error("Run unavailable", { id: toastId, description: detail });
      },
    });
  };

  const handleDelete = () => {
    deleteMutation.mutate(scenarioId, {
      onSuccess: () => {
        toast.success("Scenario deleted");
        router.push("/scenarios");
      },
      onError: (err) => {
        const detail =
          err instanceof ApiError ? err.message : "Failed to delete scenario";
        toast.error(detail);
      },
    });
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <h1 className="page-title">{scenario.name}</h1>
          {scenario.description && (
            <p className="mt-1.5 max-w-prose text-sm text-muted-foreground">
              {scenario.description}
            </p>
          )}
        </div>
        <div className="flex shrink-0 items-center gap-2">
          <Button onClick={handleRun} disabled={runMutation.isPending} size="sm">
            <Play className="h-3.5 w-3.5" />
            {runMutation.isPending ? "Running..." : "Run"}
          </Button>
          <Button asChild variant="outline" size="sm">
            <Link href={`/scenarios/${scenario.id}/edit`}>
              <Pencil className="h-3.5 w-3.5" />
              Edit
            </Link>
          </Button>
          <AlertDialog>
            <AlertDialogTrigger asChild>
              <Button variant="outline" size="sm" className="text-destructive">
                <Trash2 className="h-3.5 w-3.5" />
                Delete
              </Button>
            </AlertDialogTrigger>
            <AlertDialogContent>
              <AlertDialogHeader>
                <AlertDialogTitle>Delete this scenario?</AlertDialogTitle>
                <AlertDialogDescription>
                  This permanently deletes the scenario config from B2. Episodes
                  already captured from it are not affected.
                </AlertDialogDescription>
              </AlertDialogHeader>
              <AlertDialogFooter>
                <AlertDialogCancel>Cancel</AlertDialogCancel>
                <AlertDialogAction
                  onClick={handleDelete}
                  className={buttonVariants({ variant: "destructive" })}
                >
                  Delete scenario
                </AlertDialogAction>
              </AlertDialogFooter>
            </AlertDialogContent>
          </AlertDialog>
        </div>
      </div>

      <Card>
        <CardHeader className="border-b border-border py-4 px-5">
          <CardTitle className="card-title">Capture config</CardTitle>
        </CardHeader>
        <CardContent className="p-5">
          <ConfigRow label="Town" value={scenario.town} />
          <ConfigRow label="Weather" value={scenario.weather} />
          <ConfigRow
            label="Traffic density"
            value={<span className="capitalize">{scenario.traffic_density}</span>}
          />
          <ConfigRow label="Capture rate" value={`${scenario.fps} fps`} />
          <ConfigRow label="Frame count" value={scenario.frame_count} />
          <ConfigRow
            label="Sensor rig"
            value={
              <span className="flex flex-wrap justify-end gap-1">
                {scenario.sensors.map((s) => (
                  <Badge key={s} variant="secondary">
                    {SENSOR_LABELS[s] ?? s}
                  </Badge>
                ))}
              </span>
            }
          />
          <ConfigRow label="Created" value={formatDate(scenario.created_at)} />
          <ConfigRow label="Updated" value={formatDate(scenario.updated_at)} />
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="border-b border-border py-4 px-5">
          <CardTitle className="card-title">Episodes from this scenario</CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          {episodes.length === 0 ? (
            <p className="p-5 text-sm text-muted-foreground">
              No episodes yet. Click <strong>Run</strong> to capture one on a host
              with a CARLA server, or seed synthetic demo data.
            </p>
          ) : (
            <EpisodesTable episodes={episodes} />
          )}
        </CardContent>
      </Card>
    </div>
  );
}

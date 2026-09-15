"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Check, Copy, Link2, Trash2 } from "lucide-react";
import { toast } from "sonner";

import { Button, buttonVariants } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { ErrorState } from "@/components/ui/error-state";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
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
import { FileBrowser } from "@/components/files/file-browser";
import { ApiError, getPreviewUrl } from "@/lib/api-client";
import { useDeleteEpisode, useEpisode, useFiles } from "@/lib/queries";
import { FILE_LIST_LIMIT } from "@/lib/file-list-limit";
import { SENSOR_LABELS } from "@/lib/scenario-config";
import { formatDate } from "@/lib/utils";

function MetaRow({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="flex items-center justify-between border-b border-border py-2 text-sm last:border-0">
      <span className="text-muted-foreground">{label}</span>
      <span className="font-medium text-right">{value}</span>
    </div>
  );
}

export function EpisodeDetail({ episodeId }: { episodeId: string }) {
  const router = useRouter();
  const { data, isLoading, error, refetch } = useEpisode(episodeId);
  const deleteMutation = useDeleteEpisode();
  const prefix = `episodes/${episodeId}/`;
  const { data: frames = [] } = useFiles(prefix, FILE_LIST_LIMIT);
  const [copied, setCopied] = useState<string | null>(null);

  if (isLoading) return <Skeleton className="h-64 w-full" />;
  if (error) return <ErrorState error={error} onRetry={() => refetch()} />;
  if (!data) return <ErrorState title="Episode not found" onRetry={() => refetch()} />;

  const { metadata: meta } = data;
  const snippet = `python services/api/examples/carla_b2_dataset.py --episode ${episodeId}`;

  const copy = async (text: string, label: string) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(label);
      setTimeout(() => setCopied(null), 1500);
      toast.success(`${label} copied`);
    } catch {
      toast.error("Couldn't copy to the clipboard");
    }
  };

  const copyPresignedUrl = async () => {
    const sample = frames.find((f) => f.key.includes("/rgb/")) ?? frames[0];
    if (!sample) {
      toast.error("No frames to serve yet");
      return;
    }
    try {
      const { url } = await getPreviewUrl(sample.key);
      await copy(url, "Presigned URL");
    } catch (err) {
      const detail =
        err instanceof ApiError ? err.message : "Failed to get a presigned URL";
      toast.error(detail);
    }
  };

  const handleDelete = () => {
    deleteMutation.mutate(episodeId, {
      onSuccess: (result) => {
        toast.success(`Episode deleted (${result.objects} objects)`);
        router.push("/episodes");
      },
      onError: (err) => {
        const detail =
          err instanceof ApiError ? err.message : "Failed to delete episode";
        toast.error(detail);
      },
    });
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <h1 className="page-title font-mono">{episodeId}</h1>
          <div className="mt-2 flex flex-wrap items-center gap-2">
            <Badge variant={meta.status === "completed" ? "default" : "destructive"}>
              {meta.status}
            </Badge>
            <Badge variant={meta.capture_source === "carla" ? "outline" : "secondary"}>
              {meta.capture_source === "carla" ? "CARLA capture" : "synthetic seed"}
            </Badge>
            {meta.scenario_name && (
              <span className="text-sm text-muted-foreground">
                from {meta.scenario_name}
              </span>
            )}
          </div>
        </div>
        <AlertDialog>
          <AlertDialogTrigger asChild>
            <Button variant="outline" size="sm" className="text-destructive shrink-0">
              <Trash2 className="h-3.5 w-3.5" />
              Delete episode
            </Button>
          </AlertDialogTrigger>
          <AlertDialogContent>
            <AlertDialogHeader>
              <AlertDialogTitle>Delete this episode?</AlertDialogTitle>
              <AlertDialogDescription>
                This permanently deletes every object under{" "}
                <code>{prefix}</code> from B2. There is no undo.
              </AlertDialogDescription>
            </AlertDialogHeader>
            <AlertDialogFooter>
              <AlertDialogCancel>Cancel</AlertDialogCancel>
              <AlertDialogAction
                onClick={handleDelete}
                className={buttonVariants({ variant: "destructive" })}
              >
                Delete episode
              </AlertDialogAction>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialog>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader className="border-b border-border py-4 px-5">
            <CardTitle className="card-title">Metadata</CardTitle>
          </CardHeader>
          <CardContent className="p-5">
            <MetaRow label="Town" value={meta.town} />
            <MetaRow label="Weather" value={meta.weather} />
            <MetaRow
              label="Traffic"
              value={<span className="capitalize">{meta.traffic_density}</span>}
            />
            <MetaRow label="Capture rate" value={`${meta.fps} fps`} />
            <MetaRow
              label="Frames"
              value={`${meta.captured_frames} / ${meta.requested_frames}`}
            />
            <MetaRow label="Stored size" value={data.size_human} />
            <MetaRow label="Objects" value={data.total_objects} />
            <MetaRow label="Started" value={formatDate(meta.started_at)} />
            {meta.finished_at && (
              <MetaRow label="Finished" value={formatDate(meta.finished_at)} />
            )}
            {meta.error && <MetaRow label="Error" value={meta.error} />}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="border-b border-border py-4 px-5">
            <CardTitle className="card-title">Frames by sensor</CardTitle>
          </CardHeader>
          <CardContent className="p-5 space-y-2">
            {Object.entries(meta.frames_by_sensor).map(([sensor, count]) => (
              <div
                key={sensor}
                className="flex items-center justify-between text-sm"
              >
                <span>{SENSOR_LABELS[sensor] ?? sensor}</span>
                <span className="font-mono tabular-nums text-muted-foreground">
                  {count}
                </span>
              </div>
            ))}
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader className="border-b border-border py-4 px-5">
          <CardTitle className="card-title">Serve this dataset</CardTitle>
        </CardHeader>
        <CardContent className="p-5 space-y-4">
          <p className="text-sm text-muted-foreground">
            Frames are served straight from B2 via short-lived presigned URLs.
            Stream them into a PyTorch <code>DataLoader</code> with the example
            script, or grab a single presigned URL to inspect a frame.
          </p>
          <div className="flex items-center gap-2 rounded-md border border-border bg-muted/40 p-3">
            <code className="flex-1 overflow-x-auto text-xs">{snippet}</code>
            <Button
              variant="outline"
              size="sm"
              onClick={() => copy(snippet, "PyTorch command")}
            >
              {copied === "PyTorch command" ? (
                <Check className="h-3.5 w-3.5" />
              ) : (
                <Copy className="h-3.5 w-3.5" />
              )}
              Copy
            </Button>
          </div>
          <Button variant="outline" size="sm" onClick={copyPresignedUrl}>
            <Link2 className="h-3.5 w-3.5" />
            Copy a sample frame&apos;s presigned URL
          </Button>
        </CardContent>
      </Card>

      {meta.annotations.length > 0 && (
        <Card>
          <CardHeader className="border-b border-border py-4 px-5">
            <CardTitle className="card-title">Bounding-box annotations</CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            <Table>
              <TableHeader>
                <TableRow className="bg-muted/40 hover:bg-muted/40">
                  <TableHead className="text-xs uppercase tracking-wider text-muted-foreground">
                    Frame
                  </TableHead>
                  <TableHead className="text-xs uppercase tracking-wider text-muted-foreground">
                    Label
                  </TableHead>
                  <TableHead className="text-xs uppercase tracking-wider text-muted-foreground">
                    Box (x, y, w, h)
                  </TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {meta.annotations.map((a, i) => (
                  <TableRow key={i} className="table-row-hover">
                    <TableCell className="font-mono text-xs">{a.frame}</TableCell>
                    <TableCell>{a.label}</TableCell>
                    <TableCell className="font-mono text-xs text-muted-foreground">
                      {a.x}, {a.y}, {a.width}, {a.height}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}

      <div>
        <FileBrowser
          prefix={prefix}
          stripPrefix={prefix}
          title="Sensor frames"
          emptyTitle="No frames captured"
          emptyDescription="This episode has no sensor frames stored in B2."
          showUploadCta={false}
        />
      </div>
    </div>
  );
}

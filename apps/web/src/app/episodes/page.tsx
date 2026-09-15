import { EpisodesList } from "@/components/episodes/episodes-list";

export default function EpisodesPage() {
  return (
    <div className="space-y-8">
      <div className="animate-fade-in border-b border-border pb-5">
        <h1 className="page-title">Episodes</h1>
        <p className="mt-1.5 max-w-prose text-sm text-muted-foreground">
          Captured multi-sensor driving datasets in the lake. Open one to browse
          its sensor frames and serve them into training.
        </p>
      </div>
      <div className="animate-fade-in-up stagger-2">
        <EpisodesList />
      </div>
    </div>
  );
}

import { EpisodeDetail } from "@/components/episodes/episode-detail";

export default async function EpisodePage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  return (
    <div className="animate-fade-in">
      <EpisodeDetail episodeId={id} />
    </div>
  );
}

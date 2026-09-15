import { ScenarioDetail } from "@/components/scenarios/scenario-detail";

export default async function ScenarioPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  return (
    <div className="animate-fade-in">
      <ScenarioDetail scenarioId={id} />
    </div>
  );
}

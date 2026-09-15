import { ScenarioEdit } from "@/components/scenarios/scenario-edit";

export default async function EditScenarioPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  return (
    <div className="space-y-8">
      <div className="animate-fade-in border-b border-border pb-5">
        <h1 className="page-title">Edit scenario</h1>
        <p className="mt-1.5 max-w-prose text-sm text-muted-foreground">
          Update this capture config. Captured episodes are not affected.
        </p>
      </div>
      <div className="animate-fade-in-up stagger-2">
        <ScenarioEdit scenarioId={id} />
      </div>
    </div>
  );
}

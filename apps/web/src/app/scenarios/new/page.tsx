import { ScenarioForm } from "@/components/scenarios/scenario-form";

export default function NewScenarioPage() {
  return (
    <div className="space-y-8">
      <div className="animate-fade-in border-b border-border pb-5">
        <h1 className="page-title">New scenario</h1>
        <p className="mt-1.5 max-w-prose text-sm text-muted-foreground">
          Define a reusable CARLA capture config. Suggested defaults are shown as
          hints under each field.
        </p>
      </div>
      <div className="animate-fade-in-up stagger-2">
        <ScenarioForm />
      </div>
    </div>
  );
}

"use client";

import { Skeleton } from "@/components/ui/skeleton";
import { ErrorState } from "@/components/ui/error-state";
import { ScenarioForm } from "./scenario-form";
import { useScenario } from "@/lib/queries";

export function ScenarioEdit({ scenarioId }: { scenarioId: string }) {
  const { data, isLoading, error, refetch } = useScenario(scenarioId);

  if (isLoading) return <Skeleton className="h-64 w-full" />;
  if (error) return <ErrorState error={error} onRetry={() => refetch()} />;
  if (!data) return <ErrorState title="Scenario not found" onRetry={() => refetch()} />;

  return <ScenarioForm scenario={data} />;
}

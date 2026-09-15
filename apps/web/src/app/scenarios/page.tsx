import Link from "next/link";
import { Plus } from "lucide-react";

import { Button } from "@/components/ui/button";
import { ScenariosList } from "@/components/scenarios/scenarios-list";

export default function ScenariosPage() {
  return (
    <div className="space-y-8">
      <div className="animate-fade-in flex flex-wrap items-start justify-between gap-4 border-b border-border pb-5">
        <div className="min-w-0">
          <h1 className="page-title">Scenarios</h1>
          <p className="mt-1.5 max-w-prose text-sm text-muted-foreground">
            Reusable CARLA capture configs (town, weather, traffic, sensor rig).
            Create one, then run it to capture an episode into the lake.
          </p>
        </div>
        <Button asChild size="sm" className="h-8 shrink-0">
          <Link href="/scenarios/new">
            <Plus aria-hidden="true" className="h-3.5 w-3.5" />
            New scenario
          </Link>
        </Button>
      </div>
      <div className="animate-fade-in-up stagger-2">
        <ScenariosList />
      </div>
    </div>
  );
}

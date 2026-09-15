"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Checkbox } from "@/components/ui/checkbox";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Form,
  FormControl,
  FormDescription,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import { ApiError } from "@/lib/api-client";
import { useCreateScenario, useUpdateScenario } from "@/lib/queries";
import {
  FPS_OPTIONS,
  SCENARIO_DEFAULTS,
  SENSORS,
  TOWNS,
  TRAFFIC_DENSITIES,
  WEATHER_PRESETS,
} from "@/lib/scenario-config";
import type { Scenario } from "@carla-sensor-data-lake/shared";

// Finite fields validate against the shared option sets; fps/frame_count are
// kept as strings in the form (Selects/Inputs emit strings) and coerced on
// submit — the same pattern the settings form uses for its numeric field.
const schema = z.object({
  name: z.string().min(2, "Name must be at least 2 characters").max(80),
  description: z.string().max(500, "500 characters or fewer"),
  town: z
    .string()
    .refine((v) => (TOWNS as readonly string[]).includes(v), "Choose a town"),
  weather: z
    .string()
    .refine(
      (v) => (WEATHER_PRESETS as readonly string[]).includes(v),
      "Choose a weather preset",
    ),
  traffic_density: z
    .string()
    .refine(
      (v) => (TRAFFIC_DENSITIES as readonly string[]).includes(v),
      "Choose a traffic density",
    ),
  fps: z
    .string()
    .refine(
      (v) => (FPS_OPTIONS as readonly number[]).map(String).includes(v),
      "Choose a capture rate",
    ),
  frame_count: z
    .string()
    .regex(/^\d+$/, "Whole number of frames")
    .refine((v) => {
      const n = Number(v);
      return n >= 1 && n <= 10000;
    }, "Between 1 and 10000"),
  sensors: z.array(z.string()).min(1, "Pick at least one sensor"),
});

type FormValues = z.infer<typeof schema>;

function toFormValues(scenario?: Scenario): FormValues {
  if (!scenario) {
    return {
      name: "",
      description: "",
      town: "",
      weather: "",
      traffic_density: "",
      fps: "",
      frame_count: "",
      sensors: [],
    };
  }
  return {
    name: scenario.name,
    description: scenario.description,
    town: scenario.town,
    weather: scenario.weather,
    traffic_density: scenario.traffic_density,
    fps: String(scenario.fps),
    frame_count: String(scenario.frame_count),
    sensors: scenario.sensors,
  };
}

export function ScenarioForm({ scenario }: { scenario?: Scenario }) {
  const router = useRouter();
  const isEdit = !!scenario;
  const [submitting, setSubmitting] = useState(false);
  const createMutation = useCreateScenario();
  const updateMutation = useUpdateScenario(scenario?.id ?? "");

  const form = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: toFormValues(scenario),
  });

  const onSubmit = async (values: FormValues) => {
    setSubmitting(true);
    const payload = {
      name: values.name,
      description: values.description,
      town: values.town,
      weather: values.weather,
      traffic_density: values.traffic_density,
      fps: Number(values.fps),
      frame_count: Number(values.frame_count),
      sensors: values.sensors,
    };
    try {
      const saved = isEdit
        ? await updateMutation.mutateAsync(payload)
        : await createMutation.mutateAsync(payload);
      toast.success(isEdit ? "Scenario updated" : "Scenario created");
      router.push(`/scenarios/${saved.id}`);
    } catch (err) {
      const detail =
        err instanceof ApiError ? err.message : "Failed to save scenario";
      toast.error(detail);
      setSubmitting(false);
    }
  };

  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
        <Card>
          <CardHeader className="border-b border-border py-4 px-5">
            <CardTitle className="card-title">Scenario</CardTitle>
          </CardHeader>
          <CardContent className="p-5 space-y-4">
            <FormField
              control={form.control}
              name="name"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Name</FormLabel>
                  <FormControl>
                    <Input placeholder="Highway rush hour" {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
            <FormField
              control={form.control}
              name="description"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Description</FormLabel>
                  <FormControl>
                    <Textarea
                      placeholder="What this capture is for"
                      className="resize-none"
                      {...field}
                    />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="border-b border-border py-4 px-5">
            <CardTitle className="card-title">Capture config</CardTitle>
          </CardHeader>
          <CardContent className="p-5 space-y-6">
            <div className="grid gap-6 sm:grid-cols-2">
              <FormField
                control={form.control}
                name="town"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Town</FormLabel>
                    <Select onValueChange={field.onChange} value={field.value}>
                      <FormControl>
                        <SelectTrigger>
                          <SelectValue placeholder="Select a town" />
                        </SelectTrigger>
                      </FormControl>
                      <SelectContent>
                        {TOWNS.map((t) => (
                          <SelectItem key={t} value={t}>
                            {t}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    <FormDescription>
                      Suggested: {SCENARIO_DEFAULTS.town}
                    </FormDescription>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <FormField
                control={form.control}
                name="weather"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Weather preset</FormLabel>
                    <Select onValueChange={field.onChange} value={field.value}>
                      <FormControl>
                        <SelectTrigger>
                          <SelectValue placeholder="Select weather" />
                        </SelectTrigger>
                      </FormControl>
                      <SelectContent>
                        {WEATHER_PRESETS.map((w) => (
                          <SelectItem key={w} value={w}>
                            {w}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    <FormDescription>
                      Suggested: {SCENARIO_DEFAULTS.weather}
                    </FormDescription>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <FormField
                control={form.control}
                name="fps"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Capture rate (fps)</FormLabel>
                    <Select onValueChange={field.onChange} value={field.value}>
                      <FormControl>
                        <SelectTrigger>
                          <SelectValue placeholder="Select fps" />
                        </SelectTrigger>
                      </FormControl>
                      <SelectContent>
                        {FPS_OPTIONS.map((f) => (
                          <SelectItem key={f} value={String(f)}>
                            {f} fps
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    <FormDescription>
                      Suggested: {SCENARIO_DEFAULTS.fps} fps
                    </FormDescription>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <FormField
                control={form.control}
                name="frame_count"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Frame count</FormLabel>
                    <FormControl>
                      <Input
                        type="number"
                        min={1}
                        max={10000}
                        placeholder={String(SCENARIO_DEFAULTS.frame_count)}
                        className="font-mono tabular-nums"
                        {...field}
                      />
                    </FormControl>
                    <FormDescription>
                      Suggested: {SCENARIO_DEFAULTS.frame_count} frames
                    </FormDescription>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </div>

            <FormField
              control={form.control}
              name="traffic_density"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Traffic density</FormLabel>
                  <FormControl>
                    <RadioGroup
                      onValueChange={field.onChange}
                      value={field.value}
                      className="flex gap-6"
                    >
                      {TRAFFIC_DENSITIES.map((d) => (
                        <label
                          key={d}
                          className="flex items-center gap-2 text-sm capitalize cursor-pointer"
                        >
                          <RadioGroupItem value={d} />
                          {d}
                        </label>
                      ))}
                    </RadioGroup>
                  </FormControl>
                  <FormDescription>
                    Suggested: {SCENARIO_DEFAULTS.traffic_density}
                  </FormDescription>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="sensors"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Sensor rig</FormLabel>
                  <div className="grid gap-3 sm:grid-cols-2">
                    {SENSORS.map((sensor) => {
                      const checked = field.value.includes(sensor.value);
                      return (
                        <label
                          key={sensor.value}
                          className="flex items-center gap-2 rounded-md border border-border p-3 text-sm cursor-pointer"
                        >
                          <Checkbox
                            checked={checked}
                            onCheckedChange={(next) => {
                              field.onChange(
                                next
                                  ? [...field.value, sensor.value]
                                  : field.value.filter((v) => v !== sensor.value),
                              );
                            }}
                          />
                          {sensor.label}
                        </label>
                      );
                    })}
                  </div>
                  <FormDescription>
                    Suggested rig: RGB + segmentation + depth + LiDAR + vehicle
                    telemetry.
                  </FormDescription>
                  <FormMessage />
                </FormItem>
              )}
            />
          </CardContent>
        </Card>

        <div className="flex items-center justify-end gap-2">
          <Button type="button" variant="outline" onClick={() => router.back()}>
            Cancel
          </Button>
          <Button type="submit" disabled={submitting}>
            {submitting
              ? "Saving..."
              : isEdit
                ? "Save changes"
                : "Create scenario"}
          </Button>
        </div>
      </form>
    </Form>
  );
}

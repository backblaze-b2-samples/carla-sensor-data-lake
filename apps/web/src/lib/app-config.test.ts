import { describe, expect, it } from "vitest";
import { APP_DESCRIPTION, APP_NAME } from "@/lib/app-config";

describe("app identity", () => {
  it("ships the canonical app name and description", () => {
    expect(APP_NAME).toBe("CARLA Sensor Data Lake");
    expect(APP_DESCRIPTION).toBe(
      "Synthetic autonomous-driving sensor data lake powered by Backblaze B2"
    );
  });
});

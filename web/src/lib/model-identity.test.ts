import { describe, expect, it } from "vitest";

import { sameMainProvider } from "./model-identity";

describe("sameMainProvider", () => {
  it("matches identical ids", () => {
    expect(sameMainProvider("openrouter", "openrouter")).toBe(true);
    expect(sameMainProvider("custom:gw", "custom:gw")).toBe(true);
  });

  it("treats bare custom and a named custom slug as one endpoint, either way round", () => {
    expect(sameMainProvider("custom", "custom:gw.example.lan")).toBe(true);
    expect(sameMainProvider("custom:gw.example.lan", "custom")).toBe(true);
  });

  it("keeps two named endpoints and other providers apart", () => {
    expect(sameMainProvider("custom:a", "custom:b")).toBe(false);
    expect(sameMainProvider("custom", "openrouter")).toBe(false);
    expect(sameMainProvider("customer", "custom:x")).toBe(false);
  });
});

import { beforeEach, describe, expect, it, vi } from "vitest";
import { GL_POINT_THRESHOLD, scatterIsSlow, scatterType, supportsWebGL } from "./theme.js";

// The module caches the answer, so each case gets a fresh copy.
async function withWebGL(available) {
  vi.resetModules();
  vi.stubGlobal("document", {
    createElement: () => ({
      getContext: (kind) =>
        available && /webgl/.test(kind) ? {} : null,
    }),
  });
  return import("./theme.js");
}

describe("WebGL fallback", () => {
  beforeEach(() => vi.unstubAllGlobals());

  it("uses SVG for small point counts even where WebGL works", async () => {
    const t = await withWebGL(true);
    expect(t.scatterType(50)).toBe("scatter");
    expect(t.scatterType(t.GL_POINT_THRESHOLD - 1)).toBe("scatter");
  });

  it("uses WebGL for large point counts when it is available", async () => {
    const t = await withWebGL(true);
    expect(t.scatterType(t.GL_POINT_THRESHOLD)).toBe("scattergl");
  });

  it("never asks for WebGL when the browser has none", async () => {
    const t = await withWebGL(false);
    expect(t.scatterType(50)).toBe("scatter");
    expect(t.scatterType(100000)).toBe("scatter");
  });

  it("says when it is drawing many points the slow way", async () => {
    const without = await withWebGL(false);
    expect(without.scatterIsSlow(100000)).toBe(true);
    expect(without.scatterIsSlow(10)).toBe(false);

    const with_ = await withWebGL(true);
    expect(with_.scatterIsSlow(100000)).toBe(false);
  });

  it("survives a browser that throws on getContext", async () => {
    vi.resetModules();
    vi.stubGlobal("document", {
      createElement: () => ({ getContext: () => { throw new Error("blocked"); } }),
    });
    const t = await import("./theme.js");
    expect(t.supportsWebGL()).toBe(false);
    expect(t.scatterType(100000)).toBe("scatter");
  });
});

describe("exports", () => {
  it("keeps a sane threshold", () => {
    expect(GL_POINT_THRESHOLD).toBeGreaterThan(100);
    expect(typeof supportsWebGL).toBe("function");
    expect(typeof scatterIsSlow).toBe("function");
    expect(typeof scatterType).toBe("function");
  });
});

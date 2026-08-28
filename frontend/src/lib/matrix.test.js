import { describe, expect, it } from "vitest";
import { computeOrder, parseMatrix, transform } from "./matrix.js";

// parseMatrix is the most fragile code in the frontend: it has to cope with
// feature-matrix cells that are JSON objects containing commas and quotes, and
// it had no coverage at all.
describe("parseMatrix", () => {
  it("reads a plain numeric matrix", () => {
    const d = parseMatrix("Species,D1,D2\ns1,1,0\ns2,2,3\n");
    expect(d.kind).toBe("numeric");
    expect(d.rows).toEqual(["s1", "s2"]);
    expect(d.cols).toEqual(["D1", "D2"]);
    expect(d.data.value).toEqual([[1, 0], [2, 3]]);
  });

  it("reads a feature matrix whose cells are JSON with embedded commas", () => {
    const cell = (n) => `"{""num_hits"": ${n}, ""mean_bitscore"": ${n * 10}}"`;
    const csv = `Species,D1,D2\ns1,${cell(1)},${cell(2)}\n`;
    const d = parseMatrix(csv);
    expect(d.kind).toBe("feature");
    expect(d.features).toEqual(["num_hits", "mean_bitscore"]);
    expect(d.data.num_hits).toEqual([[1, 2]]);
    expect(d.data.mean_bitscore).toEqual([[10, 20]]);
  });

  it("treats blank and non-numeric cells as zero rather than NaN", () => {
    const d = parseMatrix("Species,D1,D2\ns1,,x\n");
    expect(d.data.value).toEqual([[0, 0]]);
  });

  it("does not produce NaN for ragged rows", () => {
    const d = parseMatrix("Species,D1,D2\ns1,1\n");
    expect(d.data.value[0].every((v) => Number.isFinite(v))).toBe(true);
  });

  it("rejects input with no columns", () => {
    expect(() => parseMatrix("Species\n")).toThrow();
  });
});

describe("computeOrder", () => {
  const rows = ["b", "a"];
  const cols = ["y", "x"];
  const z = [[1, 5], [9, 2]];

  it("sorts alphabetically", () => {
    const { ri, ci } = computeOrder(z, rows, cols, "alpha");
    expect(ri.map((i) => rows[i])).toEqual(["a", "b"]);
    expect(ci.map((j) => cols[j])).toEqual(["x", "y"]);
  });

  it("sorts by descending total", () => {
    const { ri, ci } = computeOrder(z, rows, cols, "total");
    expect(ri).toEqual([1, 0]);        // row totals 6 vs 11
    expect(ci).toEqual([0, 1]);        // col totals 10 vs 7
  });
});

describe("transform", () => {
  const cols = ["a", "b"];

  it("normalises per row", () => {
    expect(transform([[1, 4]], cols, { norm: "row" })).toEqual([[0.25, 1]]);
  });

  it("normalises per column", () => {
    expect(transform([[1, 2], [4, 2]], cols, { norm: "col" })).toEqual([[0.25, 1], [1, 1]]);
  });

  it("never divides by zero on an all-zero row", () => {
    expect(transform([[0, 0]], cols, { norm: "row" })[0].every(Number.isFinite)).toBe(true);
  });

  it("applies log1p only to positive values", () => {
    const [row] = transform([[0, Math.E - 1]], cols, { norm: "none", log: true });
    expect(row[0]).toBe(0);
    expect(row[1]).toBeCloseTo(1);
  });
});

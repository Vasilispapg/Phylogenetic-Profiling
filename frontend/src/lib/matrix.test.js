import { describe, expect, it } from "vitest";
import { computeOrder, transform } from "./matrix.js";

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

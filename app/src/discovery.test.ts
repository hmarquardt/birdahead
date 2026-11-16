import test from "node:test";
import assert from "node:assert/strict";
import { binAtDate, binLabel, discoveryMetrics, filterDiscovery, reportingChange, seriesFor, type DiscoverySpecies } from "./discovery";

const bins = [
  { index: 0, start: "2001-01-01", end: "2001-01-08", month: 1, period: 1 },
  { index: 1, start: "2001-01-08", end: "2001-01-15", month: 1, period: 2 },
  { index: 2, start: "2001-01-15", end: "2001-01-22", month: 1, period: 3 },
  { index: 3, start: "2001-01-22", end: "2001-02-01", month: 1, period: 4 },
];
const row: DiscoverySpecies = {
  code: "a", name: "Alpha", scientific_name: "Alpha alpha", taxon_id: null, teaching: false,
  media: { photos: 0, audio: 0, field_guide: false, photo_practice_ready: false, audio_practice_ready: false },
  practice_ready: false, confusion_pair: null, counties: { US: [0.1, 0.2, null, 0] },
  regional: { frequency: [0.1, 0.2, null, 0], support: [100, 100, 100, 100], counties_used: [1, 1, 1, 1] },
};

test("calendar bins preserve nulls and are not treated as zero", () => {
  assert.equal(binAtDate(bins as any, "2026-01-09"), 1);
  assert.equal(binAtDate(bins as any, "2026-01-31"), 3);
  assert.equal(binLabel(bins[3] as any), "Jan 22–Jan 31");
  const metrics = discoveryMetrics(Array.from({ length: 48 }, (_, i) => i === 1 ? null : i < 4 ? 0.1 : 0));
  assert.equal(metrics.missing_bins, 1);
  assert.equal(metrics.observed_bins, 47);
  assert.equal(reportingChange(row.counties.US, 2), null);
});

test("seasonal classification and filters distinguish year-round, missing support and media coverage", () => {
  assert.equal(discoveryMetrics(Array.from({ length: 48 }, () => 0.2)).classification, "year_round");
  assert.equal(discoveryMetrics(Array.from({ length: 48 }, (_, i) => i < 12 ? 0.4 : 0)).classification, "strongly_seasonal");
  assert.equal(discoveryMetrics(Array(48).fill(null)).classification, "insufficient");
  assert.deepEqual(filterDiscovery([row], "US", 1, "alpha", "all", false, "name").map((item) => item.code), ["a"]);
  assert.deepEqual(filterDiscovery([row], "US", 1, "", "all", true, "name"), []);
  assert.deepEqual(seriesFor(row, "US"), [0.1, 0.2, null, 0]);
});

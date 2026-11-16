import test from "node:test";
import assert from "node:assert/strict";
import { assetGaps, comparativeQuestion, recommendedPairs, seasonalOverlap, type ComparisonCatalog, type ComparisonPair } from "./comparisons";

const pair: ComparisonPair = {
  id: "alpha-beta", priority: 1,
  left: { code: "a", name: "Alpha" }, right: { code: "b", name: "Beta" },
  traits: [{ dimension: "relative_size", left: "small", right: "large", source_ids: ["src"] }],
  gaps: ["No verified label"],
};
const catalog: ComparisonCatalog = {
  schema: "birdahead-comparison-catalog-v1", version: "fixture", review_status: "provisional_curated",
  review_note: "fixture", sources: { src: { publisher: "Fixture", title: "Reference", url: "https://example.test" } }, pairs: [pair],
};
const photo = (id: string, species_code: string) => ({ id, kind: "photo" as const, species_code, media_url: `/media/public/${id}` });

test("comparison recommendations prioritize existing confusion history and local comparative attempts", () => {
  const rows = recommendedPairs(catalog, { confusion: [{ from_code: "a", to_code: "b" }] }, [{ species_code: "b" }]);
  assert.equal(rows[0]?.id, "alpha-beta");
});

test("seasonal overlap counts matching active bins without inventing a frequency", () => {
  const overlap = seasonalOverlap(
    [{ start: "Jan 1", end: "Jan 7", frequency: 0.2 }, { start: "Jan 8", end: "Jan 14", frequency: null }],
    [{ start: "Jan 1", end: "Jan 7", frequency: 0.4 }, { start: "Jan 8", end: "Jan 14", frequency: 0.1 }],
  );
  assert.deepEqual(overlap, { common_bins: 1, total_bins: 2, left_max: 0.2, right_max: 0.4 });
});

test("comparative practice uses a fresh accepted example and keeps a missing-media gap explicit", () => {
  const question = comparativeQuestion(pair, [photo("a1", "a"), photo("a2", "a")], [photo("b1", "b")], "photo", [{ asset_id: "a1" }], () => 0);
  assert.equal(question?.asset.id, "a2");
  assert.deepEqual(question?.choices.map((choice) => choice.code), ["a", "b"]);
  assert.deepEqual(assetGaps(pair, [photo("a1", "a")], []), ["Alpha: no accepted public recording", "Beta: no accepted public photograph", "Beta: no accepted public recording"]);
  assert.equal(comparativeQuestion(pair, [photo("a1", "a")], [photo("b1", "b")], "photo", [{ asset_id: "a1" }, { asset_id: "b1" }]), null);
});

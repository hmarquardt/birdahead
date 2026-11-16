import test from "node:test";
import assert from "node:assert/strict";
import {
  formatBytes, newBytesForPack, offlineQuestions, planOfflinePacks, sha256Bytes, sharedAssetCount,
  type OfflineAttempt, type OfflineCatalog, type NarrationManifest,
} from "./offline";
import { planRoadTrip } from "./roadtrip";

function asset(id: string, kind: "photo" | "audio", species: string, bytes: number) {
  return {
    id, kind, species_code: species, media_url: `/media/public/${id}`, bytes,
    sha256: "a".repeat(64), content_type: kind === "photo" ? "image/jpeg" : "audio/mpeg",
    creator: "Fixture creator", license_code: "cc-by", target_bbox_xyxy: null,
  };
}
function catalog(): OfflineCatalog {
  return {
    release_id: "release-one", county: "fixture", day: "2026-04-10",
    species: [
      { code: "a", name: "Alpha", current_reporting_frequency: 0.8, approaching_window_rise: 0, assets: [asset("a-photo", "photo", "a", 1000), asset("shared-audio", "audio", "a", 2000)] },
      { code: "b", name: "Beta", current_reporting_frequency: 0.1, approaching_window_rise: 0.4, assets: [asset("b-photo", "photo", "b", 3000), asset("shared-audio", "audio", "a", 2000)] },
      { code: "c", name: "Gamma", current_reporting_frequency: 0, approaching_window_rise: 0.2, assets: [asset("c-photo", "photo", "c", 4000)] },
    ],
  };
}

test("offline pack planning deduplicates shared assets and computes actual byte sizes", () => {
  const packs = planOfflinePacks(catalog());
  assert.deepEqual(packs.map((pack) => pack.id), ["county-day", "here-now", "arriving-soon", "photos", "audio", "complete"]);
  const complete = packs.find((pack) => pack.id === "complete")!;
  assert.deepEqual(complete.assetIds, ["a-photo", "shared-audio", "b-photo", "c-photo"]);
  assert.equal(complete.bytes, 10000);
  assert.equal(packs.find((pack) => pack.id === "photos")!.bytes, 8000);
  assert.equal(packs.find((pack) => pack.id === "audio")!.bytes, 2000);
  assert.equal(packs.find((pack) => pack.id === "here-now")!.assetIds.length, 3);
  assert.equal(packs.find((pack) => pack.id === "arriving-soon")!.assetIds.length, 3);
});

test("shared-asset accounting lets the UI show the incremental download size", () => {
  const packs = planOfflinePacks(catalog());
  const complete = packs.find((pack) => pack.id === "complete")!;
  const photos = packs.find((pack) => pack.id === "photos")!;
  assert.equal(sharedAssetCount(complete, [photos]), 3);
  assert.equal(newBytesForPack(complete, [photos]), 2000);
  assert.equal(formatBytes(10_000), "9.8 KB");
  assert.equal(formatBytes(0), "0 B");
});

test("offline questions include only downloaded modality, four distinct choices, and adapt toward misses", () => {
  const packs = planOfflinePacks(catalog());
  const attempts: OfflineAttempt[] = [{
    event_id: "offline:00000000-0000-4000-8000-000000000001", profile_id: null, release_id: "release-one",
    session_id: "offline-one", asset_id: "a-photo", species_code: "a", kind: "photo", mode: "choice",
    choice: "b", outcome: "incorrect", at: new Date().toISOString(),
  }];
  const questions = offlineQuestions(packs, "photo", attempts, 10, () => 0.5);
  assert.equal(questions.length, 3);
  assert.equal(questions[0].asset_id, "a-photo");
  assert.ok(questions.every((question) => question.kind === "photo"));
  assert.ok(questions.every((question) => new Set(question.options.map((option) => option.code)).size === question.options.length));
  assert.ok(questions.every((question) => question.options.some((option) => option.code === question.species_code)));
  assert.equal(offlineQuestions(packs, "audio", [], 10).length, 1);
});

test("road-trip planning builds an automatic audio chain with narration and separate listening metadata", () => {
  const manifest: NarrationManifest = {
    schema: "birdahead-narration-v1", voice: "Fixture",
    files: {
      "instructions/intro.m4a": { bytes: 100, sha256: "b".repeat(64), content_type: "audio/mp4" },
      "instructions/answer.m4a": { bytes: 80, sha256: "b".repeat(64), content_type: "audio/mp4" },
      "instructions/next.m4a": { bytes: 80, sha256: "b".repeat(64), content_type: "audio/mp4" },
      "instructions/another.m4a": { bytes: 80, sha256: "b".repeat(64), content_type: "audio/mp4" },
      "instructions/listen.m4a": { bytes: 80, sha256: "b".repeat(64), content_type: "audio/mp4" },
      "instructions/complete.m4a": { bytes: 80, sha256: "b".repeat(64), content_type: "audio/mp4" },
      "silence/10.m4a": { bytes: 60, sha256: "b".repeat(64), content_type: "audio/mp4", duration_seconds: 10 },
      "names/a.m4a": { bytes: 40, sha256: "b".repeat(64), content_type: "audio/mp4" },
      "names/b.m4a": { bytes: 40, sha256: "b".repeat(64), content_type: "audio/mp4" },
      "names/c.m4a": { bytes: 40, sha256: "b".repeat(64), content_type: "audio/mp4" },
    },
  };
  const base = catalog();
  base.species = base.species.map((row) => ({ ...row, assets: row.assets.map((asset) => ({ ...asset, duration_seconds: 3 })) }));
  const quiz = planRoadTrip(base, manifest, { minutes: 10, county: "fixture", day: "2026-04-10", focus: "mixed", interval_seconds: 10, order: "sequential", mode: "quiz" });
  assert.ok(quiz.roadTrip!.exercises.length >= 1);
  assert.ok(quiz.roadTrip!.segments.some((segment) => segment.kind === "silence"));
  assert.ok(quiz.roadTrip!.segments.some((segment) => segment.kind === "recording"));
  assert.ok(quiz.roadTrip!.segments.some((segment) => segment.kind === "narration" && segment.text === "The answer is"));
  assert.ok(quiz.assets.some((asset) => asset.media_url === "/narration/names/a.m4a"));
  assert.ok(quiz.bytes > 0);
  const listen = planRoadTrip(base, manifest, { minutes: 10, county: "fixture", day: "2026-04-10", focus: "here", interval_seconds: 10, order: "sequential", mode: "listen" });
  const firstRecording = listen.roadTrip!.segments.findIndex((segment) => segment.kind === "recording");
  const firstNarration = listen.roadTrip!.segments.findIndex((segment) => segment.kind === "narration" && segment.text === "The next bird is");
  assert.ok(firstNarration >= 0 && firstNarration < firstRecording);
  assert.ok(!listen.roadTrip!.segments.some((segment) => segment.kind === "silence"));
});

test("integrity helper hashes exact bytes", async () => {
  assert.equal(await sha256Bytes(new TextEncoder().encode("birdahead").buffer), "387185ca096a3f619e2be34b5c9cec64d96adfe20abb463b3f69e54d64fca956");
});

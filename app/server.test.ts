import test from "node:test";
import assert from "node:assert/strict";
import { DatabaseSync } from "node:sqlite";
import { mkdtempSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { createHash, randomUUID } from "node:crypto";
import { createApp, priorities } from "./server";
import type { Release } from "./types";

const origin = "http://127.0.0.1:8788";
function fixture() {
  const dir = mkdtempSync(join(tmpdir(), "birdahead-test-"));
  const data = Buffer.from("synthetic test bytes; not bird media");
  const path = join(dir, "fixture.jpg");
  writeFileSync(path, data);
  const release: Release = {
    schema: "birdahead-local-release-v2",
    id: "fixture-release",
    compatibility_key: "fixture-family",
    data_vintage: { start_year: 2016, end_year: 2025, source_taxonomy_version: null },
    coverage_summary: { species: 2, assets: 4 },
    confusion_pairs: [{ left: "Fixture resident", right: "Fixture migrant" }],
    species: [
      {
        ebird_species_code: "a",
        common_name: "Fixture resident",
        scientific_name: "Fixture a",
        pilot: true,
        priority_rank: 1,
        selection_rationale: ["fixture"],
      },
      {
        ebird_species_code: "b",
        common_name: "Fixture migrant",
        scientific_name: "Fixture b",
        pilot: false,
        priority_rank: 2,
        selection_rationale: ["fixture"],
      },
    ],
    counties: { fixture: "Synthetic location" },
    profiles: {
      fixture: {
        metadata: {
          start_year: 2016,
          end_year: 2025,
          source_sha256: "fixture",
        },
        rows: ["a", "b"].flatMap((code) => [
          {
            species_code: code,
            start: "2001-01-01",
            end: "2001-04-01",
            frequency: code === "b" ? 0 : 0.1,
            sample_size: 100,
          },
          {
            species_code: code,
            start: "2001-04-01",
            end: "2002-01-01",
            frequency: code === "b" ? 0.8 : 0.1,
            sample_size: 100,
          },
        ]),
      },
    },
    assets: ["a", "b"].flatMap((code) =>
      [0, 1].map((n) => ({
        id: code + n,
        kind: "photo" as const,
        species_code: code,
        local_path: path,
        bytes: data.length,
        sha256: createHash("sha256").update(data).digest("hex"),
        creator: "Fixture creator",
        source_url: "https://example.org/source",
        license_url: "https://creativecommons.org/licenses/by/4.0/",
        attribution: "Fixture creator, example source, CC BY 4.0",
        public_delivery: n === 0,
        public_use_basis: n === 0 ? "Fixture public-noncommercial eligibility" : null,
        public_license_notice: n === 0 ? "Fixture public attribution notice" : null,
        vocalization: null,
        target_bbox_xyxy: null,
      })),
    ),
  };
  const db = new DatabaseSync(":memory:");
  const app = createApp(release, db, dir);
  const get = async (path: string) => {
    const res = await app.request(origin + path, {
      headers: { Host: "127.0.0.1:8788" },
    });
    return {
      status: res.status,
      data: res.headers.get("content-type")?.includes("application/json")
        ? ((await res.json()) as any)
        : await res.text(),
    };
  };
  const post = async (
    path: string,
    data: Record<string, any>,
    requestOrigin = origin,
  ) => {
    const res = await app.request(origin + path, {
      method: "POST",
      headers: {
        Host: "127.0.0.1:8788",
        Origin: requestOrigin,
        "Content-Type": "application/json",
      },
      body: JSON.stringify(data),
    });
    return { status: res.status, data: (await res.json()) as any };
  };
  const start = () =>
    post("/api/sessions", {
      profile: "birder-1",
      location: "fixture",
      day: "2026-03-15",
      kind: "photo",
      mode: "choice",
      focus: "weak",
    });
  return {
    app,
    db,
    release,
    dir,
    get,
    post,
    start,
    cleanup: () => {
      db.close();
      rmSync(dir, { recursive: true });
    },
  };
}
test("public branding is consistent and every public page declares the inline SVG favicon", async () => {
  const f = fixture();
  const assertFavicon = (html: string) => {
    const href = html.match(/<link rel="icon" href="(data:image\/svg\+xml,[^"]+)"/)?.[1];
    assert.ok(href, "missing inline SVG favicon");
    assert.equal(href.match(/%3Csvg/g)?.length, 1);
    assert.ok(href.endsWith("%3C/svg%3E"));
    assert.match(html, /Learn the birds you're about to meet\./);
  };
  try {
    assertFavicon(readFileSync(new URL("./index.html", import.meta.url), "utf8"));
    for (const path of ["/sources", "/privacy"]) {
      const page = await f.get(path);
      assert.equal(page.status, 200);
      assertFavicon(page.data);
    }
  } finally { f.cleanup(); }
});

test("offline sync is idempotent and never crosses learner profiles", async () => {
  const f = fixture();
  try {
    const library = await f.get("/api/public/library?location=fixture&day=2026-03-15");
    const card = library.data.species.flatMap((row: any) => row.assets)[0];
    assert.ok(card.bytes > 0);
    assert.match(card.sha256, /^[a-f0-9]{64}$/);
    const event_id = `offline:${randomUUID()}`;
    const attempt = {
      event_id, asset_id: "a0", kind: "photo", mode: "choice", choice: "a",
      at: new Date().toISOString(), release_id: card.release_id ?? "fixture-release",
    };
    const first = await f.post("/api/offline/sync", { profile: "birder-1", attempts: [attempt] });
    assert.equal(first.status, 200);
    assert.deepEqual(first.data.accepted, [event_id]);
    const duplicate = await f.post("/api/offline/sync", { profile: "birder-1", attempts: [attempt] });
    assert.deepEqual(duplicate.data.duplicates, [event_id]);
    const crossed = await f.post("/api/offline/sync", { profile: "birder-2", attempts: [attempt] });
    assert.deepEqual(crossed.data.rejected, [{ event_id, code: "profile_mismatch" }]);
    assert.equal((await f.get("/api/progress?profile=birder-1")).data.attempts, 1);
    assert.equal((await f.get("/api/progress?profile=birder-2")).data.attempts, 0);
    const withdrawn = await f.post("/api/offline/sync", {
      profile: "birder-1",
      attempts: [{ ...attempt, event_id: `offline:${randomUUID()}`, asset_id: "not-in-release" }],
    });
    assert.equal(withdrawn.data.rejected[0].code, "media_withdrawn");
  } finally { f.cleanup(); }
});

test("service worker keeps downloaded pack caches across shell upgrades", () => {
  const sw = readFileSync(new URL("./public/sw.js", import.meta.url), "utf8");
  assert.match(sw, /birdahead-pack-assets-v1/);
  assert.match(sw, /key\.startsWith\('birdahead-shell-'\)/);
  assert.doesNotMatch(sw, /keys\.filter\(\(key\) => key !== CACHE\)/);
  assert.match(sw, /url\.pathname\.startsWith\('\/media\/public\/'\)/);
  assert.match(sw, /url\.pathname\.startsWith\('\/narration\/'\)/);
  assert.match(sw, /url\.pathname\.startsWith\('\/api\/'\)/);
});

test("approaching signal includes absent migrants and validates dates", () => {
  const f = fixture();
  try {
    const ranked = priorities(f.release, "fixture", "2026-03-15");
    assert.equal(ranked[0].species_code, "b");
    assert.equal(ranked[0].current_reporting_frequency, 0);
    assert.equal(ranked[0].approaching_window_rise, 0.8);
    assert.throws(() => priorities(f.release, "fixture", "2026-02-30"));
  } finally {
    f.cleanup();
  }
});
test("public catalog exposes only explicitly eligible assets and public media needs no login", async () => {
  const f = fixture();
  try {
    const boot = await f.get("/api/public/bootstrap");
    assert.equal(boot.status, 200);
    assert.equal(boot.data.public_assets, 2);
    assert.equal(boot.data.counties.fixture, "Synthetic location");
    const library = await f.get("/api/public/library?location=fixture&day=2026-03-15");
    assert.equal(library.status, 200);
    assert.equal(library.data.species.flatMap((row: any) => row.assets).length, 2);
    assert.equal((await f.get("/media/public/a0")).status, 200);
    assert.equal((await f.get("/media/public/a1")).status, 404);
    assert.equal((await f.get("/api/public/practice?location=fixture&day=2026-03-15&kind=photo&mode=choice&focus=weak")).status, 200);
  } finally { f.cleanup(); }
});

test("answers are persistent and idempotent; profiles, modalities and directed confusion stay separate", async () => {
  const f = fixture();
  try {
    const s = (await f.start()).data;
    assert.equal(s.total, 4);
    assert.equal(s.question.correct, undefined);
    const question = JSON.parse(
      f.db.prepare("SELECT questions FROM sessions WHERE id=?").get(s.id)!
        .questions as string,
    )[0];
    const wrong = question.options.find((c: string) => c !== question.correct);
    const answer = {
      session_id: s.id,
      question_id: question.id,
      choice: wrong,
    };
    assert.equal(
      (await f.post("/api/answer", answer)).data.outcome,
      "incorrect",
    );
    assert.equal((await f.post("/api/answer", answer)).status, 200);
    const p = (await f.get("/api/progress?profile=birder-1")).data;
    assert.equal(p.attempts, 1);
    assert.equal(p.confusion[0].species_code, question.correct);
    assert.equal(p.confusion[0].choice, wrong);
    assert.equal(
      (await f.get("/api/progress?profile=birder-2")).data.attempts,
      0,
    );
    assert.equal((await f.get("/api/sessions/" + s.id)).data.answered, 1);
    assert.equal(
      (await f.post("/api/answer", { ...answer, choice: "made-up" })).status,
      400,
    );
  } finally {
    f.cleanup();
  }
});
test("flags suppress media for both learners and exclude affected practice; provenance is retained", async () => {
  const f = fixture();
  try {
    const s = (await f.start()).data,
      q = s.question;
    await f.post("/api/answer", {
      session_id: s.id,
      question_id: q.id,
      choice: "unknown",
    });
    assert.equal(
      (
        await f.post("/api/flag", {
          profile: "birder-1",
          asset_id: q.asset_id,
          session_id: s.id,
          reason: "Synthetic test report",
        })
      ).status,
      200,
    );
    assert.equal(
      (await f.get("/api/progress?profile=birder-1")).data.attempts,
      0,
    );
    assert.equal((await f.get("/media/" + q.asset_id)).status, 404);
    const record = f.db.prepare("SELECT * FROM flags").get()!;
    assert.equal(record.release_id, "fixture-release");
    assert.equal(
      (
        await f.post("/api/flag", {
          profile: "birder-2",
          asset_id: q.asset_id,
          session_id: s.id,
          reason: "Invalid context",
        })
      ).status,
      400,
    );
  } finally {
    f.cleanup();
  }
});
test("cross-origin mutation, expired sessions and unsupported locations are rejected", async () => {
  const f = fixture();
  try {
    assert.equal(
      (await f.post("/api/sessions", {}, "https://invalid.example")).status,
      403,
    );
    const s = (await f.start()).data;
    f.db
      .prepare("UPDATE sessions SET started=? WHERE id=?")
      .run("2000-01-01T00:00:00.000Z", s.id);
    assert.equal((await f.get("/api/sessions/" + s.id)).data.done, true);
    assert.equal(
      (
        await f.post("/api/answer", {
          session_id: s.id,
          question_id: s.question.id,
          choice: "unknown",
        })
      ).status,
      400,
    );
    assert.equal(
      (
        await f.get(
          "/api/curriculum?profile=birder-1&location=unknown&day=2026-01-01",
        )
      ).status,
      400,
    );
  } finally {
    f.cleanup();
  }
});
test("recall reveal records no success before explicit self-assessment", async () => {
  const f = fixture();
  try {
    const s = (
      await f.post("/api/sessions", {
        profile: "birder-1",
        location: "fixture",
        day: "2026-04-01",
        kind: "photo",
        mode: "recall",
        focus: "now",
      })
    ).data;
    assert.equal(
      (
        await f.post("/api/reveal", {
          session_id: s.id,
          question_id: s.question.id,
        })
      ).status,
      200,
    );
    assert.equal(
      (await f.get("/api/progress?profile=birder-1")).data.attempts,
      0,
    );
    await f.post("/api/answer", {
      session_id: s.id,
      question_id: s.question.id,
      choice: "known",
    });
    assert.equal(
      (await f.get("/api/progress?profile=birder-1")).data.attempts,
      1,
    );
  } finally {
    f.cleanup();
  }
});
test("media IDs, byte ranges and content integrity are enforced", async () => {
  const f = fixture();
  try {
    const headers = { Host: "127.0.0.1:8788", Range: "bytes=0-3" };
    const response = await f.app.request(origin + "/media/a0", { headers });
    assert.equal(response.status, 206);
    assert.equal((await response.arrayBuffer()).byteLength, 4);
    assert.equal(
      (
        await f.app.request(origin + "/media/a0", {
          headers: { ...headers, Range: "bytes=99999-" },
        })
      ).status,
      416,
    );
    assert.equal(
      (await f.app.request(origin + "/media/nonexistent", { headers })).status,
      404,
    );
    writeFileSync(f.release.assets[0].local_path, "changed fixture bytes");
    assert.equal((await f.get("/media/a0")).status, 400);
  } finally {
    f.cleanup();
  }
});
test("library and coverage expose accepted assets without private paths", async () => {
  const f = fixture();
  try {
    const library = await f.get("/api/library?location=fixture&day=2026-03-15");
    assert.equal(library.status, 200);
    assert.equal(library.data.species.length, 2);
    const resident = library.data.species.find((s: any) => s.code === "a");
    assert.equal(resident.photos, 2);
    assert.equal(resident.photo_practice_ready, true);
    assert.equal(resident.assets.length, 2);
    assert.equal(resident.assets[0].local_path, undefined);
    assert.equal(resident.assets[0].media_url, "/media/a0");
    const searched = await f.get("/api/library?location=fixture&q=migrant&kind=photo");
    assert.deepEqual(searched.data.species.map((s: any) => s.code), ["b"]);
    const coverage = await f.get("/api/coverage?location=fixture");
    assert.equal(coverage.status, 200);
    assert.ok(coverage.data.decks.winter.deck_size >= 1);
    assert.ok(coverage.data.decks.winter.photo_practice_ready >= 1);
    assert.equal(coverage.data.data_vintage.start_year, 2016);
  } finally {
    f.cleanup();
  }
});
test("sessions continue across compatible releases and progress remains available", async () => {
  const f = fixture();
  try {
    const s = (await f.start()).data;
    const compatible: Release = {
      ...f.release,
      id: "fixture-release-2",
      assets: [
        ...f.release.assets,
        { ...f.release.assets[0], id: "added-photo" },
      ],
    };
    const next = createApp(compatible, f.db, f.dir);
    const continued = await next.request(origin + "/api/sessions/" + s.id, {
      headers: { Host: "127.0.0.1:8788" },
    });
    assert.equal(continued.status, 200);
    assert.equal((await continued.json()).id, s.id);
    assert.equal((await f.get("/api/progress?profile=birder-1")).data.attempts, 0);
    const incompatible: Release = { ...compatible, id: "fixture-release-3", compatibility_key: "other-family" };
    const rejected = await createApp(incompatible, f.db, f.dir).request(origin + "/api/sessions/" + s.id, {
      headers: { Host: "127.0.0.1:8788" },
    });
    assert.equal(rejected.status, 400);
  } finally {
    f.cleanup();
  }
});
test("answer feedback includes coverage, comparison context and a session review list", async () => {
  const f = fixture();
  try {
    const s = (await f.start()).data;
    const stored = JSON.parse(f.db.prepare("SELECT questions FROM sessions WHERE id=?").get(s.id)!.questions as string);
    const question = stored.find((q: any) => q.id === s.question.id);
    const wrong = question.options.find((code: string) => code !== question.correct);
    const result = await f.post("/api/answer", {
      session_id: s.id,
      question_id: s.question.id,
      choice: wrong,
    });
    assert.equal(result.data.outcome, "incorrect");
    assert.ok(result.data.feedback.includes("source identification"));
    assert.equal(result.data.coverage.photos, 2);
    assert.equal(result.data.coverage.photo_target_met, false);
    assert.ok(["Fixture resident", "Fixture migrant"].includes(result.data.comparison_pair.name));
    const after = await f.get("/api/sessions/" + s.id);
    assert.equal(after.data.summary.missed.length, 1);
    assert.ok(after.data.summary.coverage_note.includes("not a mastery claim"));
  } finally {
    f.cleanup();
  }
});

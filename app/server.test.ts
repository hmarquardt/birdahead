import test from "node:test";
import assert from "node:assert/strict";
import { DatabaseSync } from "node:sqlite";
import { mkdtempSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { createHash } from "node:crypto";
import { createApp, priorities } from "./server";
import type { Release } from "./types";

const origin = "http://127.0.0.1:8788";
function fixture() {
  const dir = mkdtempSync(join(tmpdir(), "birdahead-test-"));
  const data = Buffer.from("synthetic test bytes; not bird media");
  const path = join(dir, "fixture.jpg");
  writeFileSync(path, data);
  const release: Release = {
    schema: "birdahead-local-release-v1",
    id: "fixture-release",
    species: [
      {
        ebird_species_code: "a",
        common_name: "Fixture resident",
        scientific_name: "Fixture a",
      },
      {
        ebird_species_code: "b",
        common_name: "Fixture migrant",
        scientific_name: "Fixture b",
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
        sha256: createHash("sha256").update(data).digest("hex"),
        creator: "Fixture creator",
        source_url: "https://example.org/source",
        license_url: "https://creativecommons.org/licenses/by/4.0/",
        attribution: null,
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
    get,
    post,
    start,
    cleanup: () => {
      db.close();
      rmSync(dir, { recursive: true });
    },
  };
}
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

import { Hono } from "hono";
import { serve } from "@hono/node-server";
import { serveStatic } from "@hono/node-server/serve-static";
import { bodyLimit } from "hono/body-limit";
import { DatabaseSync } from "node:sqlite";
import { createHash, randomUUID } from "node:crypto";
import { readFileSync, realpathSync, statSync, mkdirSync } from "node:fs";
import { dirname, extname, resolve, sep } from "node:path";
import { fileURLToPath } from "node:url";
import type { Asset, Kind, Priority, Release } from "./types";

export const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const privateRoot = resolve(root, "experiments/private");
type DbRow = Record<string, any>;
const asRow = (value: unknown) => value as DbRow | undefined;
const asRows = (value: unknown) => value as DbRow[];
const dayMs = 86_400_000;
const isoDay = () => new Date().toISOString().slice(0, 10);

export function priorities(
  release: Release,
  location: string,
  day: string,
): Priority[] {
  const profile = release.profiles[location];
  if (
    !profile ||
    !/^\d{4}-\d{2}-\d{2}$/.test(day) ||
    Number.isNaN(Date.parse(day))
  )
    throw Error("Choose a supported county and date");
  const [year, month, date] = day.split("-").map(Number);
  const actual = new Date(Date.UTC(year, month - 1, date));
  if (actual.toISOString().slice(0, 10) !== day)
    throw Error("Invalid calendar date");
  const template = new Date(
    Date.UTC(2001, month - 1, month === 2 ? Math.min(date, 28) : date),
  );
  return release.species
    .map((s) => {
      const rows = profile.rows.filter(
        (r) => r.species_code === s.ebird_species_code,
      );
      const at = (d: Date) => {
        const stamp = `2001-${d.toISOString().slice(5, 10)}`;
        return rows.find((r) => r.start <= stamp && stamp < r.end);
      };
      const current = at(template);
      const value = current?.frequency ?? null;
      const future = [14, 21, 28]
        .map((n) => at(new Date(template.getTime() + n * dayMs))?.frequency)
        .filter((n): n is number => n !== undefined && n !== null);
      const peak = future.length ? Math.max(...future) : null;
      const rise =
        peak === null || value === null ? null : Math.max(0, peak - value);
      return {
        species_code: s.ebird_species_code,
        current_reporting_frequency: value,
        future_14_28_day_max: peak,
        approaching_window_rise: rise,
        learning_priority:
          value === null || rise === null
            ? null
            : Number((0.6 * value + 0.4 * rise).toFixed(8)),
        sample_size: current?.sample_size ?? null,
        bin_start: current?.start ?? null,
        bin_end: current?.end ?? null,
      };
    })
    .sort(
      (a, b) =>
        (b.learning_priority ?? -1) - (a.learning_priority ?? -1) ||
        a.species_code.localeCompare(b.species_code),
    );
}

export function createApp(
  release: Release,
  db: DatabaseSync,
  mediaRoot = privateRoot,
) {
  if (release.schema !== "birdahead-local-release-v1")
    throw Error("Unsupported private content release");
  db.exec(`PRAGMA journal_mode=WAL;
    CREATE TABLE IF NOT EXISTS profiles(id TEXT PRIMARY KEY,name TEXT NOT NULL);
    INSERT OR IGNORE INTO profiles VALUES('birder-1','Birder 1'),('birder-2','Birder 2');
    CREATE TABLE IF NOT EXISTS sessions(id TEXT PRIMARY KEY,profile_id TEXT NOT NULL,release_id TEXT NOT NULL,location TEXT NOT NULL,outing_day TEXT NOT NULL,kind TEXT NOT NULL,mode TEXT NOT NULL,started TEXT NOT NULL,questions TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS attempts(id TEXT PRIMARY KEY,session_id TEXT NOT NULL,question_id TEXT UNIQUE NOT NULL,profile_id TEXT NOT NULL,asset_id TEXT NOT NULL,species_code TEXT NOT NULL,kind TEXT NOT NULL,mode TEXT NOT NULL,choice TEXT NOT NULL,outcome TEXT NOT NULL,at TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS flags(id TEXT PRIMARY KEY,profile_id TEXT NOT NULL,asset_id TEXT NOT NULL,release_id TEXT NOT NULL,session_id TEXT,reason TEXT NOT NULL,suggested_species TEXT,at TEXT NOT NULL);`);
  const app = new Hono();
  const hidden = () =>
    new Set(
      asRows(db.prepare("SELECT DISTINCT asset_id FROM flags").all()).map(
        (r) => r.asset_id,
      ),
    );
  const assets = () => release.assets.filter((a) => !hidden().has(a.id));
  const knownProfile = (id: string) =>
    !!db.prepare("SELECT id FROM profiles WHERE id=?").get(id);
  const species = (code: string) =>
    release.species.find((s) => s.ebird_species_code === code)!;
  const eligible = (kind: Kind) =>
    release.species.filter(
      (s) =>
        assets().filter(
          (a) => a.kind === kind && a.species_code === s.ebird_species_code,
        ).length >= 2,
    );
  const credit = (a: Asset) => ({
    creator: a.creator,
    attribution: a.attribution,
    source_url: a.source_url,
    license_url: a.license_url,
    validation:
      "Automatically accepted with source and model evidence; no expert verification claimed",
    vocalization: a.vocalization,
  });
  const history = (profile: string) =>
    asRows(
      db
        .prepare(
          `SELECT * FROM attempts WHERE profile_id=? AND asset_id NOT IN (SELECT asset_id FROM flags) ORDER BY at`,
        )
        .all(profile),
    );
  function publicSession(id: string) {
    const session = asRow(
      db.prepare("SELECT * FROM sessions WHERE id=?").get(id),
    );
    if (!session) throw Error("Session not found");
    if (session.release_id !== release.id)
      throw Error("Content release changed; start a new session");
    const questions = JSON.parse(session.questions) as DbRow[];
    const answered = asRows(
      db
        .prepare("SELECT * FROM attempts WHERE session_id=? ORDER BY at")
        .all(id),
    );
    const completed = new Set(answered.map((a) => a.question_id));
    const question = questions.find(
      (q) => !completed.has(q.id) && !hidden().has(q.asset_id),
    );
    const elapsed = Math.max(
      0,
      (Date.now() - Date.parse(session.started)) / 1000,
    );
    return {
      id,
      profile_id: session.profile_id,
      location: session.location,
      outing_day: session.outing_day,
      kind: session.kind,
      mode: session.mode,
      answered: answered.length,
      total: questions.length,
      elapsed_seconds: elapsed,
      done: !question || elapsed >= 300,
      summary: {
        recognized: answered.filter((a) => a.outcome === "correct").length,
        practice: answered.filter((a) => a.outcome === "incorrect").length,
        uncertain: answered.filter((a) => a.outcome === "uncertain").length,
      },
      question:
        question && elapsed < 300
          ? {
              id: question.id,
              asset_id: question.asset_id,
              media_url: `/media/${question.asset_id}`,
              kind: session.kind,
              options: question.options.map((code: string) => ({
                code,
                name: species(code).common_name,
              })),
              credit: credit(
                release.assets.find((a) => a.id === question.asset_id)!,
              ),
              bbox:
                release.assets.find((a) => a.id === question.asset_id)
                  ?.target_bbox_xyxy ?? null,
            }
          : null,
    };
  }
  app.use("*", async (c, next) => {
    const host = c.req.header("host") ?? "";
    if (!/^127\.0\.0\.1:\d+$/.test(host))
      return c.json({ error: "Local access only" }, 403);
    if (!["GET", "HEAD"].includes(c.req.method)) {
      if (
        c.req.header("origin") !== new URL(c.req.url).origin ||
        c.req.header("content-type")?.split(";")[0] !== "application/json"
      )
        return c.json({ error: "Same-origin JSON required" }, 403);
    }
    c.header("X-Content-Type-Options", "nosniff");
    c.header("Referrer-Policy", "no-referrer");
    c.header(
      "Content-Security-Policy",
      "default-src 'self'; img-src 'self' data:; media-src 'self'; style-src 'self' 'unsafe-inline'; object-src 'none'; frame-ancestors 'none'; base-uri 'none'",
    );
    c.header("Cache-Control", "no-store");
    await next();
  });
  app.use(
    "/api/*",
    bodyLimit({
      maxSize: 16_384,
      onError: (c) => c.json({ error: "Request too large" }, 413),
    }),
  );
  app.onError((err, c) =>
    c.json(
      { error: err instanceof Error ? err.message : "Request failed" },
      400,
    ),
  );
  app.get("/api/bootstrap", (c) =>
    c.json({
      release_id: release.id,
      counties: release.counties,
      profiles: db.prepare("SELECT * FROM profiles ORDER BY id").all(),
      species: release.species.map((s) => ({
        code: s.ebird_species_code,
        name: s.common_name,
        scientific_name: s.scientific_name,
        photos: assets().filter(
          (a) => a.kind === "photo" && a.species_code === s.ebird_species_code,
        ).length,
        recordings: assets().filter(
          (a) => a.kind === "audio" && a.species_code === s.ebird_species_code,
        ).length,
      })),
      coverage: {
        photo: eligible("photo").length,
        audio: eligible("audio").length,
      },
      source:
        "eBird 2016–2025, owner-supplied county histogram exports; 48 native bins/year",
      limitations:
        "Reporting frequency reflects submitted complete checklists, not your chance of an encounter. Sparse samples and observer/habitat bias remain.",
    }),
  );
  app.get("/api/curriculum", (c) => {
    const profile = c.req.query("profile") ?? "";
    if (!knownProfile(profile)) throw Error("Choose a learner");
    const past = history(profile);
    return c.json({
      priorities: priorities(
        release,
        c.req.query("location") ?? "",
        c.req.query("day") ?? isoDay(),
      ).map((r) => ({
        ...r,
        name: species(r.species_code).common_name,
        photo:
          assets().filter(
            (a) => a.kind === "photo" && a.species_code === r.species_code,
          ).length >= 2,
        audio:
          assets().filter(
            (a) => a.kind === "audio" && a.species_code === r.species_code,
          ).length >= 2,
        attempts: past.filter((a) => a.species_code === r.species_code).length,
        needs_practice: past.filter(
          (a) => a.species_code === r.species_code && a.outcome === "incorrect",
        ).length,
      })),
    });
  });
  app.get("/api/progress", (c) => {
    const profile = c.req.query("profile") ?? "";
    if (!knownProfile(profile)) throw Error("Choose a learner");
    const past = history(profile);
    const confusion = asRows(
      db
        .prepare(
          `SELECT species_code,choice,kind,COUNT(*) AS count FROM attempts WHERE profile_id=? AND outcome='incorrect' AND mode='choice' AND asset_id NOT IN (SELECT asset_id FROM flags) GROUP BY species_code,choice,kind ORDER BY count DESC`,
        )
        .all(profile),
    );
    return c.json({
      attempts: past.length,
      distinct_examples: new Set(past.map((a) => a.asset_id)).size,
      by_species: release.species
        .flatMap((s) =>
          (["photo", "audio"] as Kind[]).map((kind) => {
            const records = past.filter(
              (a) => a.species_code === s.ebird_species_code && a.kind === kind,
            );
            return {
              name: s.common_name,
              code: s.ebird_species_code,
              kind,
              attempts: records.length,
              recognized: records.filter((a) => a.outcome === "correct").length,
              distinct_examples: new Set(records.map((a) => a.asset_id)).size,
              label: records.length ? "Practicing" : "New",
            };
          }),
        )
        .filter((s) => s.attempts),
      confusion: confusion.map((r) => ({
        ...r,
        from: species(r.species_code).common_name,
        to: species(r.choice).common_name,
      })),
      flags: asRows(
        db
          .prepare(
            "SELECT asset_id,reason,at FROM flags WHERE profile_id=? ORDER BY at DESC",
          )
          .all(profile),
      ),
    });
  });
  app.post("/api/sessions", async (c) => {
    const body = await c.req.json();
    const { profile, location, day, kind, mode, focus } = body;
    if (
      !knownProfile(profile) ||
      !["photo", "audio"].includes(kind) ||
      !["choice", "recall"].includes(mode) ||
      !["now", "arriving", "weak"].includes(focus)
    )
      throw Error("Invalid practice settings");
    const ranked = priorities(release, location, day),
      pool = eligible(kind);
    if (pool.length < 2)
      throw Error("Not enough accepted examples for this practice mode");
    const past = history(profile),
      now = Date.now();
    const score = (code: string) => {
      const r = ranked.find((r) => r.species_code === code)!;
      const h = past.filter(
        (a) => a.species_code === code && a.kind === kind && a.mode === mode,
      );
      const last = h.at(-1);
      let streak = 0;
      for (const attempt of h.slice(-4).reverse()) {
        if (attempt.outcome !== "correct") break;
        streak++;
      }
      const due =
        !last ||
        last.outcome !== "correct" ||
        now - Date.parse(last.at) > Math.pow(2, streak) * dayMs;
      const weaknesses =
        h.slice(-5).filter((a) => a.outcome !== "correct").length /
        Math.max(1, Math.min(h.length, 5));
      return (
        (focus === "arriving"
          ? (r.approaching_window_rise ?? 0)
          : (r.learning_priority ?? 0)) +
        (due ? 0.12 : 0) +
        weaknesses * (focus === "weak" ? 0.7 : 0.15)
      );
    };
    const order = pool
      .filter((s) => {
        const r = ranked.find((r) => r.species_code === s.ebird_species_code)!;
        return (
          focus === "weak" ||
          (focus === "arriving"
            ? (r.approaching_window_rise ?? 0) > 0
            : (r.current_reporting_frequency ?? 0) > 0)
        );
      })
      .sort(
        (a, b) =>
          score(b.ebird_species_code) - score(a.ebird_species_code) ||
          a.ebird_species_code.localeCompare(b.ebird_species_code),
      );
    if (!order.length)
      throw Error(
        "No supported priorities for this focus and date; choose Here now or another date",
      );
    const questions: DbRow[] = [];
    const used = new Set<string>();
    // Interleave species; never repeat the same media within a session. Prefer unseen media between sessions.
    for (let round = 0; round < 5 && questions.length < 10; round++)
      for (const s of order) {
        const candidates = assets().filter(
          (a) =>
            a.kind === kind &&
            a.species_code === s.ebird_species_code &&
            !used.has(a.id),
        );
        candidates.sort(
          (a, b) =>
            past.filter((h) => h.asset_id === a.id).length -
              past.filter((h) => h.asset_id === b.id).length ||
            a.id.localeCompare(b.id),
        );
        const asset = candidates[0];
        if (!asset || questions.length >= 10) continue;
        used.add(asset.id);
        const qid = randomUUID();
        // Prior confusions are useful distractors; remaining choices come from the same usable modality pool.
        const mistakes = past
          .filter(
            (h) =>
              h.species_code === s.ebird_species_code &&
              h.outcome === "incorrect" &&
              h.mode === "choice",
          )
          .map((h) => h.choice);
        const others = [
          ...new Set([...mistakes, ...pool.map((p) => p.ebird_species_code)]),
        ]
          .filter(
            (code) =>
              code !== s.ebird_species_code &&
              pool.some((p) => p.ebird_species_code === code),
          )
          .slice(0, 3);
        const options = [s.ebird_species_code, ...others].sort((a, b) =>
          createHash("sha256")
            .update(qid + a)
            .digest("hex")
            .localeCompare(
              createHash("sha256")
                .update(qid + b)
                .digest("hex"),
            ),
        );
        questions.push({
          id: qid,
          asset_id: asset.id,
          correct: s.ebird_species_code,
          options,
        });
      }
    const id = randomUUID();
    db.prepare("INSERT INTO sessions VALUES(?,?,?,?,?,?,?,?,?)").run(
      id,
      profile,
      release.id,
      location,
      day,
      kind,
      mode,
      new Date().toISOString(),
      JSON.stringify(questions),
    );
    return c.json(publicSession(id));
  });
  app.get("/api/sessions/:id", (c) => c.json(publicSession(c.req.param("id"))));
  app.post("/api/answer", async (c) => {
    const { session_id, question_id, choice } = await c.req.json();
    const current = publicSession(session_id);
    const session = asRow(
      db.prepare("SELECT * FROM sessions WHERE id=?").get(session_id),
    )!;
    const q = JSON.parse(session.questions).find(
      (q: DbRow) => q.id === question_id,
    );
    const existing = asRow(
      db
        .prepare("SELECT * FROM attempts WHERE question_id=? AND session_id=?")
        .get(question_id, session_id),
    );
    if (
      !q ||
      (!existing && (current.done || current.question?.id !== question_id))
    )
      throw Error("Question is no longer active");
    if (existing && existing.choice !== choice)
      throw Error("This question already has a recorded answer");
    const allowed =
      session.mode === "choice"
        ? [...q.options, "unknown", "insufficient"]
        : ["known", "unknown", "insufficient"];
    if (!allowed.includes(choice)) throw Error("Choose a valid answer");
    const asset = release.assets.find((a) => a.id === q.asset_id)!;
    const outcome = ["unknown", "insufficient"].includes(choice)
      ? "uncertain"
      : choice === q.correct || choice === "known"
        ? "correct"
        : "incorrect";
    if (!existing)
      db.prepare("INSERT INTO attempts VALUES(?,?,?,?,?,?,?,?,?,?,?)").run(
        randomUUID(),
        session_id,
        question_id,
        session.profile_id,
        asset.id,
        q.correct,
        session.kind,
        session.mode,
        choice,
        outcome,
        new Date().toISOString(),
      );
    return c.json({
      outcome: existing?.outcome ?? outcome,
      answer: {
        code: q.correct,
        name: species(q.correct).common_name,
        scientific_name: species(q.correct).scientific_name,
      },
      credit: credit(asset),
      note:
        choice === "insufficient"
          ? "Marked uncertain. Flag this example if the media cannot support a species identification."
          : null,
    });
  });
  app.post("/api/reveal", async (c) => {
    const { session_id, question_id } = await c.req.json();
    const current = publicSession(session_id);
    if (
      current.mode !== "recall" ||
      current.done ||
      current.question?.id !== question_id
    )
      throw Error("No active recall question");
    const session = asRow(
      db.prepare("SELECT questions FROM sessions WHERE id=?").get(session_id),
    )!;
    const q = JSON.parse(session.questions).find(
      (q: DbRow) => q.id === question_id,
    );
    return c.json({
      answer: {
        code: q.correct,
        name: species(q.correct).common_name,
        scientific_name: species(q.correct).scientific_name,
      },
      credit: credit(release.assets.find((a) => a.id === q.asset_id)!),
    });
  });
  app.post("/api/flag", async (c) => {
    const { profile, asset_id, session_id, reason, suggested_species } =
      await c.req.json();
    if (
      !knownProfile(profile) ||
      !release.assets.some((a) => a.id === asset_id) ||
      typeof reason !== "string" ||
      !reason.trim() ||
      reason.length > 2000
    )
      throw Error("Choose a learner, example and reason");
    if (
      suggested_species &&
      !release.species.some((s) => s.ebird_species_code === suggested_species)
    )
      throw Error("Unknown suggested species");
    if (session_id) {
      const s = asRow(
        db
          .prepare("SELECT profile_id,questions FROM sessions WHERE id=?")
          .get(session_id),
      );
      if (
        !s ||
        s.profile_id !== profile ||
        !JSON.parse(s.questions).some((q: DbRow) => q.asset_id === asset_id)
      )
        throw Error("Flag context mismatch");
    }
    const id = randomUUID();
    db.prepare("INSERT INTO flags VALUES(?,?,?,?,?,?,?,?)").run(
      id,
      profile,
      asset_id,
      release.id,
      session_id ?? null,
      reason.trim(),
      suggested_species || null,
      new Date().toISOString(),
    );
    return c.json({
      id,
      status:
        "Locally hidden from practice for both learners, pending review. Related attempts excluded from progress.",
    });
  });
  app.get("/media/:id", (c) => {
    const asset = assets().find((a) => a.id === c.req.param("id"));
    if (!asset) return c.notFound();
    const path = realpathSync(resolve(root, asset.local_path));
    if (!path.startsWith(realpathSync(mediaRoot) + sep)) return c.notFound();
    const bytes = readFileSync(path);
    if (createHash("sha256").update(bytes).digest("hex") !== asset.sha256)
      throw Error("Content integrity check failed");
    const mime: Record<string, string> = {
      ".jpeg": "image/jpeg",
      ".jpg": "image/jpeg",
      ".png": "image/png",
      ".webp": "image/webp",
      ".mp3": "audio/mpeg",
      ".wav": "audio/wav",
      ".ogg": "audio/ogg",
    };
    c.header(
      "Content-Type",
      mime[extname(path).toLowerCase()] ?? "application/octet-stream",
    );
    c.header("Accept-Ranges", "bytes");
    const range = c.req.header("range");
    if (range) {
      const match = /^bytes=(\d+)-(\d*)$/.exec(range);
      if (!match)
        return c.body(null, 416, {
          "Content-Range": `bytes */${bytes.length}`,
        });
      const start = Number(match[1]),
        end = Math.min(
          match[2] ? Number(match[2]) : bytes.length - 1,
          bytes.length - 1,
        );
      if (start > end || start >= bytes.length)
        return c.body(null, 416, {
          "Content-Range": `bytes */${bytes.length}`,
        });
      return c.body(new Uint8Array(bytes.subarray(start, end + 1)), 206, {
        "Content-Range": `bytes ${start}-${end}/${bytes.length}`,
        "Content-Length": String(end - start + 1),
      });
    }
    return c.body(new Uint8Array(bytes), 200, {
      "Content-Length": String(statSync(path).size),
    });
  });
  app.get("/assets/*", serveStatic({ root: resolve(root, "app/dist") }));
  app.get("/", serveStatic({ path: resolve(root, "app/dist/index.html") }));
  return app;
}

if (
  process.argv[1] &&
  resolve(process.argv[1]) === fileURLToPath(import.meta.url)
) {
  const releasePath = resolve(privateRoot, "local-mvp/release.json");
  let release: Release;
  try {
    release = JSON.parse(readFileSync(releasePath, "utf8"));
  } catch {
    throw Error(
      "Prepare local content first: uv run python -m tooling.histograms && uv run python -m tooling.local_release",
    );
  }
  const stateDirectory = resolve(
    process.env.BIRDAHEAD_STATE_DIRECTORY ?? resolve(privateRoot, "local-mvp"),
  );
  if (!stateDirectory.startsWith(privateRoot + sep))
    throw Error("Learning state must remain in ignored private storage");
  mkdirSync(stateDirectory, { recursive: true });
  const db = new DatabaseSync(resolve(stateDirectory, "learning.sqlite"));
  const port = Number(process.env.BIRDAHEAD_PORT ?? 8788);
  if (!Number.isInteger(port) || port < 1024 || port > 65535)
    throw Error("Invalid BIRDAHEAD_PORT");
  serve(
    { fetch: createApp(release, db).fetch, hostname: "127.0.0.1", port },
    () => console.log(`BirdAhead local: http://127.0.0.1:${port}`),
  );
}

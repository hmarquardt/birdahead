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
import { renderPrivacyPage, renderRobots, renderSitemap, renderSourcesPage } from "./public-pages";

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
  if (!["birdahead-local-release-v1", "birdahead-local-release-v2"].includes(release.schema))
    throw Error("Unsupported private content release");
  const releaseFamily = release.compatibility_key ?? release.id;
  db.exec(`PRAGMA journal_mode=WAL;
    CREATE TABLE IF NOT EXISTS profiles(id TEXT PRIMARY KEY,name TEXT NOT NULL);
    INSERT OR IGNORE INTO profiles VALUES('birder-1','Birder 1'),('birder-2','Birder 2');
    CREATE TABLE IF NOT EXISTS sessions(id TEXT PRIMARY KEY,profile_id TEXT NOT NULL,release_id TEXT NOT NULL,location TEXT NOT NULL,outing_day TEXT NOT NULL,kind TEXT NOT NULL,mode TEXT NOT NULL,started TEXT NOT NULL,questions TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS attempts(id TEXT PRIMARY KEY,session_id TEXT NOT NULL,question_id TEXT UNIQUE NOT NULL,profile_id TEXT NOT NULL,asset_id TEXT NOT NULL,species_code TEXT NOT NULL,kind TEXT NOT NULL,mode TEXT NOT NULL,choice TEXT NOT NULL,outcome TEXT NOT NULL,at TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS flags(id TEXT PRIMARY KEY,profile_id TEXT NOT NULL,asset_id TEXT NOT NULL,release_id TEXT NOT NULL,session_id TEXT,reason TEXT NOT NULL,suggested_species TEXT,at TEXT NOT NULL);`);
  const sessionColumns = asRows(db.prepare("PRAGMA table_info(sessions)").all()).map((r) => r.name);
  if (!sessionColumns.includes("release_family"))
    db.exec("ALTER TABLE sessions ADD COLUMN release_family TEXT");
  const app = new Hono();
  const hidden = () =>
    new Set(
      asRows(db.prepare("SELECT DISTINCT asset_id FROM flags").all()).map(
        (r) => r.asset_id,
      ),
    );
  const assets = () => {
    const suppressed = hidden();
    return release.assets.filter((a) => !suppressed.has(a.id));
  };
  const knownProfile = (id: string) =>
    !!db.prepare("SELECT id FROM profiles WHERE id=?").get(id);
  const species = (code: string) =>
    release.species.find((s) => s.ebird_species_code === code) ?? {
      ebird_species_code: code,
      common_name: code,
      scientific_name: "Retained attempt; species absent from this content release",
    };
  const countAssets = (code: string, kind: Kind, visible = assets()) =>
    visible.filter((a) => a.kind === kind && a.species_code === code).length;
  const eligible = (kind: Kind, visible = assets()) =>
    release.species.filter((s) => countAssets(s.ebird_species_code, kind, visible) >= 2);
  const credit = (a: Asset) => ({
    creator: a.creator,
    attribution: a.attribution,
    source_url: a.source_url,
    license_url: a.license_url,
    license_code: a.license_code ?? null,
    source: a.source ?? null,
    validation:
      "Automatically accepted with source and model evidence; no expert verification claimed",
    vocalization: a.vocalization,
    derivative_of: a.derivative_of ?? null,
  });
  const PUBLIC_LICENSES = new Set(['cc0','cc-by','cc-by-sa','cc-by-nc','cc-by-nc-sa']);
  const isPublicAsset = (a: Asset) => a.public_delivery === true || (a.public_delivery === undefined && PUBLIC_LICENSES.has(String(a.license_code ?? '').toLowerCase()) && !!a.creator && !!a.license_url && !!a.source_url && !!a.attribution);
  const publicAssets = () => assets().filter((a) => isPublicAsset(a));
  const publicCredit = (a: Asset) => ({ ...credit(a), public_use_basis: a.public_use_basis ?? null, public_license_notice: a.public_license_notice ?? null,
    public_noncommercial_only: a.public_noncommercial_only ?? null, public_share_alike: a.public_share_alike ?? null });
  const publicAssetCard = (a: Asset) => ({ id:a.id, kind:a.kind, species_code:a.species_code, media_url:`/media/public/${a.id}`, bytes:Number(a.bytes??(a.local_path?statSync(resolve(root,a.local_path)).size:0)),
    sha256:a.sha256??null, content_type:a.content_type??a.media_format??(a.kind==='photo'?'image/jpeg':'audio/mpeg'), creator:a.creator,
    attribution:a.attribution, source_url:a.source_url, license_url:a.license_url, license_code:a.license_code ?? null, source:a.source ?? null,
    public_use_basis:a.public_use_basis ?? null, public_license_notice:a.public_license_notice ?? null, public_noncommercial_only:a.public_noncommercial_only ?? null,
    public_share_alike:a.public_share_alike ?? null, derivative:!!a.derivative_of, vocalization:a.vocalization ?? null, target_bbox_xyxy:a.target_bbox_xyxy ?? null,
    duration_seconds:(a as DbRow).duration_seconds??((a as DbRow).technical_metrics as DbRow|undefined)?.duration_seconds??null,
    validation:'Accepted source record; automated corroboration only, not expert certification' });
  const publicRanked = (location: string, day: string) => { const visible=publicAssets(); const counts=new Map<string,{photos:number;audio:number}>();
    for(const a of visible){const row=counts.get(a.species_code)??{photos:0,audio:0}; if(a.kind==='photo')row.photos++; else row.audio++; counts.set(a.species_code,row);}
    return priorities(release,location,day).map((r)=>{const s=species(r.species_code); const c=counts.get(r.species_code)??{photos:0,audio:0};
      return {...r,name:s.common_name,scientific_name:s.scientific_name,confusion_pair:s.confusion_pair??null,photos:c.photos,recordings:c.audio,photo_ready:c.photos>=1,audio_ready:c.audio>=1};}); };
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
    const compatible = session.release_family
      ? session.release_family === releaseFamily
      : session.release_id === release.id;
    if (!compatible)
      throw Error("Content release changed; start a new session");
    const visible = assets();
    const byId = new Map(visible.map((a) => [a.id, a]));
    const suppressed = hidden();
    const questions = (JSON.parse(session.questions) as DbRow[]).filter((q) =>
      byId.has(q.asset_id),
    );
    const answered = asRows(
      db
        .prepare("SELECT * FROM attempts WHERE session_id=? ORDER BY at")
        .all(id),
    );
    const completed = new Set(answered.map((a) => a.question_id));
    const question = questions.find(
      (q) => !completed.has(q.id) && !suppressed.has(q.asset_id),
    );
    const elapsed = Math.max(
      0,
      (Date.now() - Date.parse(session.started)) / 1000,
    );
    const missed = answered
      .filter((a) => a.outcome === "incorrect")
      .map((a) => ({
        name: species(a.species_code).common_name,
        kind: a.kind,
        choice: a.choice === "unknown" || a.choice === "insufficient" ? null : species(a.choice).common_name,
      }));
    const uncertain = answered
      .filter((a) => a.outcome === "uncertain")
      .map((a) => ({ name: species(a.species_code).common_name, kind: a.kind }));
    const current = question ? byId.get(question.asset_id) : undefined;
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
      data_vintage: release.data_vintage ?? null,
      coverage_summary: release.coverage_summary ?? null,
      summary: {
        recognized: answered.filter((a) => a.outcome === "correct").length,
        practice: answered.filter((a) => a.outcome === "incorrect").length,
        uncertain: answered.filter((a) => a.outcome === "uncertain").length,
        distinct_examples: new Set(answered.map((a) => a.asset_id)).size,
        missed: missed.slice(0, 10),
        uncertain_species: uncertain.slice(0, 10),
        coverage_note:
          "Practice results are not a mastery claim. Missing examples stay explicit; unknown media traits remain unknown.",
      },
      question:
        question && current && elapsed < 300
          ? {
              id: question.id,
              asset_id: question.asset_id,
              media_url: `/media/${question.asset_id}`,
              compare_with: (()=>{const cp=(species(current.species_code) as DbRow).confusion_pair as DbRow|undefined; return cp?.ebird_species_code?{code:cp.ebird_species_code,name:cp.common_name}:null;})(),
              kind: session.kind,
              options: question.options.map((code: string) => ({
                code,
                name: species(code).common_name,
              })),
              credit: credit(current),
              bbox: current.target_bbox_xyxy ?? null,
              source_evidence: current.source_verified
                ? "Source-verified record; automated model corroboration is not expert certification"
                : null,
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
      "default-src 'self'; script-src 'self' https://analytics.aismallbizguru.com; img-src 'self' data:; media-src 'self'; style-src 'self' 'unsafe-inline'; connect-src 'self' https://analytics.aismallbizguru.com; object-src 'none'; frame-ancestors 'none'; base-uri 'none'",
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
  app.get("/api/public/bootstrap", (c) => {
    const visible=publicAssets(); const counts=new Map<string,{photos:number;audio:number}>();
    for(const a of visible){const row=counts.get(a.species_code)??{photos:0,audio:0}; if(a.kind==='photo')row.photos++; else row.audio++; counts.set(a.species_code,row);}
    const rows=release.species.map((s)=>{const row=counts.get(s.ebird_species_code)??{photos:0,audio:0};return {code:s.ebird_species_code,name:s.common_name,scientific_name:s.scientific_name,priority_rank:s.priority_rank??null,
      public_photos:row.photos,public_recordings:row.audio,photo_practice_ready:row.photos>=2,audio_practice_ready:row.audio>=2,coverage_gap:row.photos<2&&row.audio<2};});
    return c.json({schema:'birdahead-public-bootstrap-v1',release_id:release.id,counties:release.counties,species:rows,public_assets:visible.length,
      public_photo_assets:visible.filter((a)=>a.kind==='photo').length,public_audio_assets:visible.filter((a)=>a.kind==='audio').length,
      coverage:{species:rows.length,public_photo_species:rows.filter((s)=>s.public_photos>0).length,public_audio_species:rows.filter((s)=>s.public_recordings>0).length,
        photo_practice_ready:rows.filter((s)=>s.photo_practice_ready).length,audio_practice_ready:rows.filter((s)=>s.audio_practice_ready).length,gaps:rows.filter((s)=>s.coverage_gap).length},
      data_vintage:release.data_vintage??null,data_source:{citation:'eBird. 2016–2025. eBird observation data; derived seasonal summaries.',terms_url:'https://www.birds.cornell.edu/home/ebird-data-access-terms-of-use/'},
      limitations:'Historical reporting frequency reflects complete checklists, not encounter probability. Automated media acceptance is not expert verification.'});
  });
  app.get("/api/public/curriculum", (c) => {
    const location=c.req.query('location')??''; const day=c.req.query('day')??isoDay(); const ranked=publicRanked(location,day);
    const arriving=ranked.filter((r)=>(r.approaching_window_rise??0)>0).sort((a,b)=>(b.approaching_window_rise??-1)-(a.approaching_window_rise??-1)).slice(0,25);
    return c.json({location,day,data_vintage:release.data_vintage??null,priorities:ranked,arriving_soon:arriving,note:'Historical reporting frequency and a 14–28 day rise; neither is an encounter forecast.'});
  });
  app.get("/api/public/library", (c) => {
    const query=(c.req.query('q')??'').trim().toLowerCase(); const kind=c.req.query('kind')??'all'; const location=c.req.query('location')??Object.keys(release.counties)[0]??''; const day=c.req.query('day')??isoDay();
    const visible=publicAssets(); const counts=new Map<string,{photos:number;audio:number}>(); const grouped=new Map<string,Asset[]>();
    for(const a of visible){const row=counts.get(a.species_code)??{photos:0,audio:0}; if(a.kind==='photo')row.photos++; else row.audio++; counts.set(a.species_code,row); if(kind!=='all'&&a.kind!==kind)continue; const list=grouped.get(a.species_code)??[]; list.push(a); grouped.set(a.species_code,list);}
    const seasonal=new Map(priorities(release,location,day).map((r)=>[r.species_code,r]));
    const rows=release.species.map((s)=>{const c=counts.get(s.ebird_species_code)??{photos:0,audio:0};const sr=seasonal.get(s.ebird_species_code);return {code:s.ebird_species_code,name:s.common_name,scientific_name:s.scientific_name,priority_rank:s.priority_rank??null,confusion_pair:s.confusion_pair??null,
      photos:c.photos,recordings:c.audio,photo_practice_ready:c.photos>=2,audio_practice_ready:c.audio>=2,coverage_gap:c.photos<2&&c.audio<2,current_reporting_frequency:sr?.current_reporting_frequency??null,approaching_window_rise:sr?.approaching_window_rise??null,sample_size:sr?.sample_size??null,bin_start:sr?.bin_start??null,bin_end:sr?.bin_end??null,assets:(grouped.get(s.ebird_species_code)??[]).map(publicAssetCard)};})
      .filter((r)=>!query||r.name.toLowerCase().includes(query)||r.scientific_name.toLowerCase().includes(query)||r.code.toLowerCase().includes(query)).sort((a,b)=>(a.priority_rank??9999)-(b.priority_rank??9999)||a.name.localeCompare(b.name));
    return c.json({location,day,query,kind,release_id:release.id,data_vintage:release.data_vintage??null,species:rows});
  });
  app.get("/api/public/seasonality", (c) => { const code=c.req.query('code')??''; const location=c.req.query('location')??''; const profile=release.profiles[location]; if(!profile) throw Error('Choose a supported county'); const s=species(code);
    return c.json({code,location,name:s.common_name,scientific_name:s.scientific_name,bins:profile.rows.filter((r)=>r.species_code===code).map((r)=>({start:r.start,end:r.end,frequency:r.frequency,sample_size:r.sample_size,value_status:r.value_status??null})),metadata:{start_year:profile.metadata.start_year,end_year:profile.metadata.end_year,bin_definition:profile.metadata.bin_definition,units:profile.metadata.units,taxonomy_version:profile.metadata.taxonomy_version,source_taxonomy_version:profile.metadata.source_taxonomy_version??null,source_note:profile.metadata.source_note??null},data_vintage:release.data_vintage??null}); });
  app.get("/api/public/practice", async (c) => {
    const location=c.req.query('location')??''; const day=c.req.query('day')??isoDay(); const kind:Kind=c.req.query('kind')==='audio'?'audio':'photo'; const mode=c.req.query('mode')==='recall'?'recall':'choice'; const focus=c.req.query('focus')??'now';
    const visible=publicAssets(); let candidates=publicRanked(location,day).filter((r)=>kind==='photo'?r.photo_ready:r.audio_ready);
    if(focus==='now')candidates=candidates.filter((r)=>(r.current_reporting_frequency??0)>0); if(focus==='arriving')candidates=candidates.filter((r)=>(r.approaching_window_rise??0)>0);
    if(candidates.length<2)throw Error('Not enough public media for this practice mode'); const questions:DbRow[]=[]; const used=new Set<string>();
    for(let round=0;round<4&&questions.length<10;round++)for(const candidate of candidates){if(questions.length>=10)break;const pool=visible.filter((a)=>a.species_code===candidate.species_code&&a.kind===kind&&!used.has(a.id));if(!pool.length)continue;const asset=pool[0];used.add(asset.id);const id=randomUUID();
      const options=mode==='choice'?[candidate.species_code,...candidates.filter((r)=>r.species_code!==candidate.species_code).slice(0,3).map((r)=>r.species_code)]:[];
      questions.push({id,asset_id:asset.id,species_code:candidate.species_code,name:candidate.name,compare_with:candidate.confusion_pair?.ebird_species_code?{code:candidate.confusion_pair.ebird_species_code,name:candidate.confusion_pair.common_name}:null,kind,mode,media_url:`/media/public/${asset.id}`,options:options.map((code)=>({code,name:species(code).common_name})),answer_code:candidate.species_code,credit:publicCredit(asset),bbox:asset.target_bbox_xyxy??null});}
    if(!questions.length)throw Error('No public practice questions are available'); return c.json({schema:'birdahead-public-practice-v1',guest:true,location,day,kind,mode,focus,questions});
  });
  app.get("/api/bootstrap", (c) => {
    const visible = assets();
    const counts = new Map<string, { photos: number; audio: number }>();
    for (const asset of visible) {
      const row = counts.get(asset.species_code) ?? { photos: 0, audio: 0 };
      if (asset.kind === "photo") row.photos++;
      else if (asset.kind === "audio") row.audio++;
      counts.set(asset.species_code, row);
    }
    const speciesRows = release.species.map((s) => {
      const row = counts.get(s.ebird_species_code) ?? { photos: 0, audio: 0 };
      return {
        code: s.ebird_species_code,
        name: s.common_name,
        scientific_name: s.scientific_name,
        pilot: (s as DbRow).pilot ?? false,
        priority_rank: (s as DbRow).priority_rank ?? null,
        photos: row.photos,
        recordings: row.audio,
        photo: row.photos >= 2,
        audio: row.audio >= 2,
        photo_target_met: row.photos >= 5,
        audio_target_met: row.audio >= 3,
        coverage_gap: row.photos < 2 && row.audio < 2,
      };
    });
    const firstProfile = Object.values(release.profiles ?? {})[0];
    const vintage =
      release.data_vintage ??
      (firstProfile
        ? {
            start_year: firstProfile.metadata.start_year,
            end_year: firstProfile.metadata.end_year,
            source_taxonomy_version: firstProfile.metadata.source_taxonomy_version ?? null,
            taxonomy_version: firstProfile.metadata.taxonomy_version,
            bin_definition: firstProfile.metadata.bin_definition,
            units: firstProfile.metadata.units,
            source_note: "Owner-supplied county histogram exports; source taxonomy release unknown.",
          }
        : null);
    return c.json({
      release_id: release.id,
      release_schema: release.schema,
      compatibility_key: releaseFamily,
      counties: release.counties,
      profiles: db.prepare("SELECT * FROM profiles ORDER BY id").all(),
      species: speciesRows,
      coverage: {
        photo: speciesRows.filter((s) => s.photo).length,
        audio: speciesRows.filter((s) => s.audio).length,
        species: speciesRows.length,
        photo_target: speciesRows.filter((s) => s.photo_target_met).length,
        audio_target: speciesRows.filter((s) => s.audio_target_met).length,
        gaps: speciesRows.filter((s) => s.coverage_gap).length,
      },
      coverage_summary: release.coverage_summary ?? null,
      data_vintage: vintage,
      confusion_pairs: release.confusion_pairs ?? [],
      source:
        "eBird 2016–2025, owner-supplied county histogram exports; 48 native bins/year",
      limitations:
        "Reporting frequency reflects submitted complete checklists, not your chance of an encounter. Sparse samples and observer/habitat bias remain. Missing media coverage is explicit.",
    });
  });
  app.get("/api/curriculum", (c) => {
    const profile = c.req.query("profile") ?? "";
    if (!knownProfile(profile)) throw Error("Choose a learner");
    const location = c.req.query("location") ?? "";
    const day = c.req.query("day") ?? isoDay();
    const past = history(profile);
    const visible = assets();
    const media = new Map<string, { photos: number; audio: number }>();
    for (const asset of visible) {
      const row = media.get(asset.species_code) ?? { photos: 0, audio: 0 };
      if (asset.kind === "photo") row.photos++;
      else if (asset.kind === "audio") row.audio++;
      media.set(asset.species_code, row);
    }
    const ranked = priorities(release, location, day).map((r) => {
      const counts = media.get(r.species_code) ?? { photos: 0, audio: 0 };
      return {
        ...r,
        name: species(r.species_code).common_name,
        scientific_name: species(r.species_code).scientific_name,
        pilot: (species(r.species_code) as DbRow).pilot ?? false,
        priority_rank: (species(r.species_code) as DbRow).priority_rank ?? null,
        photos: counts.photos,
        recordings: counts.audio,
        photo: counts.photos >= 2,
        audio: counts.audio >= 2,
        photo_target_met: counts.photos >= 5,
        audio_target_met: counts.audio >= 3,
        coverage_gap: counts.photos < 2 && counts.audio < 2,
        attempts: past.filter((a) => a.species_code === r.species_code).length,
        needs_practice: past.filter(
          (a) => a.species_code === r.species_code && a.outcome !== "correct",
        ).length,
      };
    });
    return c.json({
      location,
      day,
      data_vintage: release.data_vintage ?? null,
      coverage_summary: release.coverage_summary ?? null,
      priorities: ranked,
    });
  });
  const publicAsset = (asset: Asset) => ({
    id: asset.id,
    kind: asset.kind,
    species_code: asset.species_code,
    media_url: `/media/${asset.id}`,
    creator: asset.creator,
    attribution: asset.attribution,
    source_url: asset.source_url,
    license_url: asset.license_url,
    license_code: asset.license_code ?? null,
    source: asset.source ?? null,
    vocalization: asset.vocalization,
    sex: (asset as DbRow).sex ?? null,
    age: (asset as DbRow).age ?? null,
    plumage: (asset as DbRow).plumage ?? null,
    biological_attribute_status: (asset as DbRow).biological_attribute_status ?? null,
    target_bbox_xyxy: asset.target_bbox_xyxy,
    derivative_of: asset.derivative_of ?? null,
    duration_seconds:
      ((asset as DbRow).technical_metrics as DbRow | undefined)?.duration_seconds ??
      null,
    validation:
      "Automatically accepted source/model corroboration; no expert verification claimed",
  });
  app.get("/api/library", (c) => {
    const query = (c.req.query("q") ?? "").trim().toLowerCase();
    const kind = c.req.query("kind") ?? "all";
    const location = c.req.query("location") ?? Object.keys(release.counties)[0] ?? "";
    const day = c.req.query("day") ?? isoDay();
    const visible = assets();
    const media = new Map<string, { photos: number; audio: number }>();
    const grouped = new Map<string, Asset[]>();
    for (const asset of visible) {
      const row = media.get(asset.species_code) ?? { photos: 0, audio: 0 };
      if (asset.kind === "photo") row.photos++;
      else if (asset.kind === "audio") row.audio++;
      media.set(asset.species_code, row);
      if (kind !== "all" && asset.kind !== kind) continue;
      const list = grouped.get(asset.species_code) ?? [];
      list.push(asset);
      grouped.set(asset.species_code, list);
    }
    const seasonal = new Map(
      priorities(release, location, day).map((row) => [row.species_code, row]),
    );
    const rows = release.species
      .map((s) => {
        const counts = media.get(s.ebird_species_code) ?? { photos: 0, audio: 0 };
        const seasonalRow = seasonal.get(s.ebird_species_code);
        return {
          code: s.ebird_species_code,
          name: s.common_name,
          scientific_name: s.scientific_name,
          pilot: (s as DbRow).pilot ?? false,
          priority_rank: (s as DbRow).priority_rank ?? null,
          confusion_pair: (s as DbRow).confusion_pair ?? null,
          selection_rationale: (s as DbRow).selection_rationale ?? [],
          photos: counts.photos,
          recordings: counts.audio,
          photo_target_met: counts.photos >= 5,
          audio_target_met: counts.audio >= 3,
          photo_practice_ready: counts.photos >= 2,
          audio_practice_ready: counts.audio >= 2,
          coverage_gap: counts.photos < 2 && counts.audio < 2,
          current_reporting_frequency: seasonalRow?.current_reporting_frequency ?? null,
          approaching_window_rise: seasonalRow?.approaching_window_rise ?? null,
          sample_size: seasonalRow?.sample_size ?? null,
          bin_start: seasonalRow?.bin_start ?? null,
          bin_end: seasonalRow?.bin_end ?? null,
          assets: (grouped.get(s.ebird_species_code) ?? []).map(publicAsset),
        };
      })
      .filter(
        (row) =>
          !query ||
          row.name.toLowerCase().includes(query) ||
          row.scientific_name.toLowerCase().includes(query) ||
          row.code.toLowerCase().includes(query),
      )
      .sort(
        (a, b) =>
          (a.priority_rank ?? 9999) - (b.priority_rank ?? 9999) ||
          a.name.localeCompare(b.name),
      );
    return c.json({
      location,
      day,
      query,
      kind,
      release_id: release.id,
      data_vintage: release.data_vintage ?? null,
      coverage_summary: release.coverage_summary ?? null,
      species: rows,
    });
  });
  app.get("/api/coverage", (c) => {
    const location = c.req.query("location") ?? Object.keys(release.counties)[0] ?? "";
    const visible = assets();
    const count = (code: string, kind: Kind) =>
      visible.filter((a) => a.kind === kind && a.species_code === code).length;
    const describe = (code: string) => ({
      code,
      name: species(code).common_name,
      photos: count(code, "photo"),
      audio: count(code, "audio"),
    });
    const seasons: Record<string, string> = {
      winter: "2026-01-15",
      spring_migration: "2026-05-05",
      summer: "2026-07-15",
      fall_migration: "2026-09-10",
      now: isoDay(),
    };
    const decks: Record<string, DbRow> = {};
    for (const [label, day] of Object.entries(seasons)) {
      const ranking = priorities(release, location, day)
        .filter((row) => (row.current_reporting_frequency ?? 0) > 0)
        .slice(0, 25);
      decks[label] = {
        day,
        deck_size: ranking.length,
        photo_practice_ready: ranking.filter((row) => count(row.species_code, "photo") >= 2).length,
        audio_practice_ready: ranking.filter((row) => count(row.species_code, "audio") >= 2).length,
        photo_and_audio_target: ranking.filter(
          (row) => count(row.species_code, "photo") >= 5 && count(row.species_code, "audio") >= 3,
        ).length,
        photo_gaps: ranking
          .filter((row) => count(row.species_code, "photo") < 2)
          .slice(0, 12)
          .map((row) => describe(row.species_code)),
        audio_gaps: ranking
          .filter((row) => count(row.species_code, "audio") < 2)
          .slice(0, 12)
          .map((row) => describe(row.species_code)),
      };
    }
    const arriving = priorities(release, location, isoDay())
      .filter((row) => (row.approaching_window_rise ?? 0) > 0)
      .sort((a, b) => (b.approaching_window_rise ?? 0) - (a.approaching_window_rise ?? 0))
      .slice(0, 25);
    return c.json({
      location,
      data_vintage: release.data_vintage ?? null,
      coverage_summary: release.coverage_summary ?? null,
      decks,
      arriving_soon: {
        deck_size: arriving.length,
        photo_practice_ready: arriving.filter((row) => count(row.species_code, "photo") >= 2).length,
        audio_practice_ready: arriving.filter((row) => count(row.species_code, "audio") >= 2).length,
        gaps: arriving
          .filter((row) => count(row.species_code, "photo") < 2)
          .slice(0, 12)
          .map((row) => describe(row.species_code)),
      },
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
        from_code: r.species_code,
        to_code: r.choice,
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
      visible = assets(),
      pool = eligible(kind, visible);
    if (pool.length < 2)
      throw Error("Not enough accepted examples for this practice mode");
    const past = history(profile),
      now = Date.now();
    const score = (code: string) => {
      const r =
        ranked.find((row) => row.species_code === code) ??
        ({ approaching_window_rise: 0, learning_priority: 0, current_reporting_frequency: 0 } as Priority);
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
        const r =
          ranked.find((row) => row.species_code === s.ebird_species_code) ??
          ({ approaching_window_rise: 0, current_reporting_frequency: 0 } as Priority);
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
        const candidates = visible.filter(
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
    db.prepare("INSERT INTO sessions(id,profile_id,release_id,release_family,location,outing_day,kind,mode,started,questions) VALUES(?,?,?,?,?,?,?,?,?,?)").run(
      id,
      profile,
      release.id,
      releaseFamily,
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
    const asset = assets().find((a) => a.id === q.asset_id);
    if (!asset) throw Error("Media example is no longer available");
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
    const correct = species(q.correct);
    const own = assets().filter((a) => a.species_code === q.correct);
    const coverage = {
      photos: own.filter((a) => a.kind === "photo").length,
      audio: own.filter((a) => a.kind === "audio").length,
      photo_target_met: own.filter((a) => a.kind === "photo").length >= 5,
      audio_target_met: own.filter((a) => a.kind === "audio").length >= 3,
    };
    const pairs = ((release as DbRow).confusion_pairs ?? []) as DbRow[];
    const pair = pairs.find(
      (row) => row.left === correct.common_name || row.right === correct.common_name,
    );
    const partnerName = pair
      ? pair.left === correct.common_name
        ? pair.right
        : pair.left
      : null;
    const partner = partnerName
      ? release.species.find((s) => s.common_name === partnerName)
      : null;
    const resolved = existing?.outcome ?? outcome;
    const feedback =
      resolved === "correct"
        ? session.mode === "recall"
          ? "You recalled the source identification. Try another example to test transfer, not memorization."
          : "Recognized. This is one accepted example; different photographs or recordings test transfer."
        : resolved === "incorrect"
          ? `Not this time. The source identification is ${correct.common_name}. Review the source record rather than relying on an invented field mark.`
          : choice === "insufficient"
            ? "Marked as not enough information. That is a valid outcome; flag the example if the media cannot support a species answer."
            : "Left uncertain. Uncertainty is recorded separately from an incorrect species guess.";
    return c.json({
      outcome: resolved,
      answer: {
        code: q.correct,
        name: correct.common_name,
        scientific_name: correct.scientific_name,
      },
      credit: credit(asset),
      note:
        choice === "insufficient"
          ? "Marked uncertain. Flag this example if the media cannot support a species identification."
          : null,
      feedback,
      coverage,
      comparison_pair:
        partner && partnerName
          ? {
              code: partner.ebird_species_code,
              name: partnerName,
              photos: assets().filter(
                (a) => a.kind === "photo" && a.species_code === partner.ebird_species_code,
              ).length,
              audio: assets().filter(
                (a) => a.kind === "audio" && a.species_code === partner.ebird_species_code,
              ).length,
            }
          : null,
      evidence:
        "Automatically accepted source/model corroboration; no expert certification or field-mark annotation is implied.",
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
    const asset = assets().find((a) => a.id === q.asset_id);
    if (!asset) throw Error("Media example is no longer available");
    const correct = species(q.correct);
    const own = assets().filter((a) => a.species_code === q.correct);
    const pairs = ((release as DbRow).confusion_pairs ?? []) as DbRow[];
    const pair = pairs.find(
      (row) => row.left === correct.common_name || row.right === correct.common_name,
    );
    const partnerName = pair
      ? pair.left === correct.common_name
        ? pair.right
        : pair.left
      : null;
    const partner = partnerName
      ? release.species.find((s) => s.common_name === partnerName)
      : null;
    return c.json({
      answer: {
        code: q.correct,
        name: correct.common_name,
        scientific_name: correct.scientific_name,
      },
      credit: credit(asset),
      coverage: {
        photos: own.filter((a) => a.kind === "photo").length,
        audio: own.filter((a) => a.kind === "audio").length,
        photo_target_met: own.filter((a) => a.kind === "photo").length >= 5,
        audio_target_met: own.filter((a) => a.kind === "audio").length >= 3,
      },
      comparison_pair:
        partner && partnerName
          ? {
              code: partner.ebird_species_code,
              name: partnerName,
              photos: assets().filter(
                (a) => a.kind === "photo" && a.species_code === partner.ebird_species_code,
              ).length,
              audio: assets().filter(
                (a) => a.kind === "audio" && a.species_code === partner.ebird_species_code,
              ).length,
            }
          : null,
    });
  });
  app.post("/api/offline/sync", async (c) => {
    const body = await c.req.json().catch(() => null) as DbRow | null;
    const profile = String(body?.profile ?? body?.profile_id ?? "");
    const input = Array.isArray(body?.attempts) ? body.attempts : null;
    if (!knownProfile(profile) || !input || input.length > 100) throw Error("Choose a learner and send between 1 and 100 offline attempts");
    const visible = publicAssets();
    const byId = new Map(visible.map((asset) => [asset.id, asset]));
    const accepted: string[] = []; const duplicates: string[] = [];
    const rejected: Array<{ event_id: string; code: string }> = [];
    const eventPattern = /^offline:[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/;
    for (const raw of input) {
      const item = raw && typeof raw === "object" ? raw as DbRow : {};
      const eventId = typeof item.event_id === "string" ? item.event_id.toLowerCase() : "";
      if (!eventPattern.test(eventId)) { rejected.push({ event_id: String(item.event_id ?? "").slice(0, 80), code: "invalid_event_id" }); continue; }
      const asset = byId.get(String(item.asset_id ?? ""));
      const mode = item.mode === "recall" ? "recall" : item.mode === "choice" ? "choice" : "";
      const choice = String(item.choice ?? "");
      const at = Date.parse(String(item.at ?? ""));
      if (!asset || asset.kind !== item.kind) { rejected.push({ event_id: eventId, code: asset ? "kind_mismatch" : "media_withdrawn" }); continue; }
      if (!mode || !Number.isFinite(at) || at > Date.now() + 300_000 || at < Date.now() - 400 * 86_400_000) { rejected.push({ event_id: eventId, code: "invalid_attempt" }); continue; }
      if (!["unknown", "insufficient", "known", "incorrect"].includes(choice) && !release.species.some((s) => s.ebird_species_code === choice)) { rejected.push({ event_id: eventId, code: "invalid_choice" }); continue; }
      const outcome = choice === "unknown" || choice === "insufficient" ? "uncertain" : mode === "recall" ? (choice === "known" ? "correct" : "incorrect") : choice === asset.species_code ? "correct" : "incorrect";
      const prior = asRow(db.prepare("SELECT profile_id FROM attempts WHERE id=? OR question_id=?").get(eventId, eventId));
      if (prior) { if (prior.profile_id !== profile) rejected.push({ event_id: eventId, code: "profile_mismatch" }); else duplicates.push(eventId); continue; }
      const changes = db.prepare("INSERT OR IGNORE INTO attempts(id,session_id,question_id,profile_id,asset_id,species_code,kind,mode,choice,outcome,at) VALUES(?,?,?,?,?,?,?,?,?,?,?)").run(eventId, `offline:${eventId.slice(8)}`, eventId, profile, asset.id, asset.species_code, asset.kind, mode, choice, outcome, new Date(at).toISOString()).changes;
      if (changes > 0) accepted.push(eventId); else duplicates.push(eventId);
    }
    return c.json({ ok: true, profile_id: profile, release_id: release.id, accepted, duplicates, rejected });
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
        "Locally hidden from practice for both learners, pending review. Related attempts excluded from progress. Sync to the curation workbench with `uv run python -m tooling.flag_sync --apply`.",
    });
  });
  app.get("/media/public/:id", (c) => {
    const asset=publicAssets().find((a)=>a.id===c.req.param('id')); if(!asset)return c.notFound(); const path=realpathSync(resolve(root,asset.local_path));
    if(!path.startsWith(realpathSync(mediaRoot)+sep))return c.notFound(); const bytes=readFileSync(path); if(createHash('sha256').update(bytes).digest('hex')!==asset.sha256)throw Error('Content integrity check failed');
    const mime:Record<string,string>={'.jpeg':'image/jpeg','.jpg':'image/jpeg','.png':'image/png','.webp':'image/webp','.mp3':'audio/mpeg','.wav':'audio/wav','.ogg':'audio/ogg','.flac':'audio/flac','.m4a':'audio/mp4'};
    c.header('Content-Type',mime[extname(path).toLowerCase()]??'application/octet-stream'); c.header('Accept-Ranges','bytes'); c.header('Cache-Control','public, max-age=86400');
    const range=c.req.header('range'); if(range){const m=/^bytes=(\d+)-(\d*)$/.exec(range); if(!m)return c.body(null,416,{'Content-Range':`bytes */${bytes.length}`}); const start=Number(m[1]),end=Math.min(m[2]?Number(m[2]):bytes.length-1,bytes.length-1); if(start>end||start>=bytes.length)return c.body(null,416,{'Content-Range':`bytes */${bytes.length}`}); return c.body(new Uint8Array(bytes.subarray(start,end+1)),206,{'Content-Range':`bytes ${start}-${end}/${bytes.length}`,'Content-Length':String(end-start+1)});}
    return c.body(new Uint8Array(bytes),200,{'Content-Length':String(bytes.length)});
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
      ".flac": "audio/flac",
      ".m4a": "audio/mp4",
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
  app.get("/sources", (c) => c.html(renderSourcesPage(new URL(c.req.url).origin)));
  app.get("/privacy", (c) => c.html(renderPrivacyPage(new URL(c.req.url).origin)));
  app.get("/robots.txt", (c) => { c.header("Content-Type","text/plain"); return c.body(renderRobots(new URL(c.req.url).origin)); });
  app.get("/sitemap.xml", (c) => { c.header("Content-Type","application/xml"); return c.body(renderSitemap(new URL(c.req.url).origin,release.species.map((s)=>({code:s.ebird_species_code})),release.counties,isoDay())); });
  app.get("/regions/:county", (c) => c.redirect(`/?tab=explore&county=${encodeURIComponent(c.req.param("county"))}`, 302));
  app.get("/compare", (c) => c.redirect("/?tab=compare", 302));
  app.get("/birds/:code", (c) => c.redirect(`/?tab=guide&bird=${encodeURIComponent(c.req.param("code"))}`, 302));
  app.use("/narration/*", async (c, next) => { if (c.req.path.endsWith(".m4a")) return c.notFound(); await next(); });
  app.get("/assets/*", serveStatic({ root: resolve(root, "app/dist") }));
  app.use("/narration/*", async (c, next) => { await next(); c.res.headers.set("Content-Type", c.req.path.endsWith(".json") ? "application/json" : "audio/wav"); });
  app.get("/narration/*", serveStatic({ root: resolve(root, "app/dist") }));
  app.get("/comparisons.json", serveStatic({ path: resolve(root, "app/dist/comparisons.json") }));
  for (const asset of ["/sw.js", "/manifest.webmanifest", "/icon-192.png", "/icon-512.png", "/icon-maskable-512.png", "/apple-touch-icon.png"]) {
    app.get(asset, serveStatic({ path: resolve(root, "app/dist", asset.slice(1)) }));
  }
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

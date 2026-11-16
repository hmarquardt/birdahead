/// <reference lib="webworker" />
import { Hono } from "hono";
import { HTTPException } from "hono/http-exception";
import { escapeHtml, renderPrivacyPage, renderRegionPage, renderRobots, renderSitemap, renderSourcesPage, renderSpeciesPage } from "./public-pages";

type Row = Record<string, any>;
interface D1Prepared {
  bind(...values: any[]): D1Prepared;
  first<T = Row>(): Promise<T | null>;
  all<T = Row>(): Promise<{ results: T[]; success: boolean }>;
  run(): Promise<{ success: boolean; meta?: Row }>;
}
interface D1Database {
  prepare(sql: string): D1Prepared;
  batch(statements: D1Prepared[]): Promise<any[]>;
}
interface R2Bucket {
  get(key: string, options?: Row): Promise<any | null>;
  head(key: string): Promise<any | null>;
  put(key: string, value: any, options?: Row): Promise<any>;
  delete(key: string): Promise<void>;
}
interface Fetcher { fetch(request: Request): Promise<Response>; }
interface Env {
  DB: D1Database;
  CONTENT: R2Bucket;
  ASSETS: Fetcher;
  HANK_KEY: string;
  HEATHER_KEY: string;
  PUBLISH_TOKEN: string;
  APP_ORIGIN: string;
  DEPLOY_REVISION: string;
  LOGIN_LIMIT?: { limit(options: { key: string }): Promise<{ success: boolean }> };
  PUBLISH_LIMIT?: { limit(options: { key: string }): Promise<{ success: boolean }> };
  PUBLIC_LIMIT?: { limit(options: { key: string }): Promise<{ success: boolean }> };
}
type AppEnv = { Bindings: Env; Variables: { profile: string } };
interface Bin { species_code: string; start: string; end: string; frequency: number | null; sample_size: number | null; value_status?: string | null; }
interface Asset { id: string; kind: "photo" | "audio"; species_code: string; r2_key?: string; [key: string]: any; }
interface Release {
  id: string; schema: string; compatibility_key?: string; species: Row[]; counties: Record<string,string>;
  profiles: Record<string,{ rows: Bin[]; metadata: Row }>; assets: Asset[]; coverage_summary?: Row;
  data_vintage?: Row; confusion_pairs?: Row[]; limitations?: string[]; coverage?: Row; universe?: Row; public_data_terms?: Row;
}

const encoder = new TextEncoder();
const hex = (bytes: ArrayBuffer) => [...new Uint8Array(bytes)].map((b) => b.toString(16).padStart(2, "0")).join("");
const digest = async (text: string) => hex(await crypto.subtle.digest("SHA-256", encoder.encode(text)));
const randomToken = () => [...crypto.getRandomValues(new Uint8Array(32))].map((b) => b.toString(16).padStart(2, "0")).join("");
const safeEqual = (a: string, b: string) => {
  if (a.length !== b.length) return false;
  let diff = 0;
  for (let i = 0; i < a.length; i++) diff |= a.charCodeAt(i) ^ b.charCodeAt(i);
  return diff === 0;
};
const now = () => Math.floor(Date.now() / 1000);
const originHost = (origin: string) => new URL(origin).host;
const cookieName = (origin: string) => origin.startsWith("https:") ? "__Host-birdahead-session" : "birdahead-local-session";
function sessionCookie(origin: string, token: string, age = 60 * 60 * 24 * 30) {
  const secure = origin.startsWith("https:") ? "; Secure" : "";
  return `${cookieName(origin)}=${token}; Path=/; HttpOnly; SameSite=Strict; Max-Age=${age}${secure}`;
}
function tokenFromRequest(request: Request, origin: string) {
  const name = cookieName(origin);
  return (request.headers.get("Cookie") ?? "").split(";").map((v) => v.trim()).find((v) => v.startsWith(name + "="))?.slice(name.length + 1) ?? null;
}
function assertSameOrigin(c: any, env: Env) {
  const method = c.req.method.toUpperCase();
  if (!["POST", "PUT", "PATCH", "DELETE"].includes(method)) return;
  if (c.req.header("Origin") !== env.APP_ORIGIN || c.req.header("Sec-Fetch-Site") === "cross-site" || c.req.header("X-BirdAhead-Request") !== "1") {
    throw new HTTPException(403, { message: "Same-origin BirdAhead request required." });
  }
}
const profileNames: Record<string,string> = { hank: "Hank", heather: "Heather" };
const profileId = (v: string) => v === "heather" ? "heather" : "hank";

let releaseCache: { key: string; expires: number; data: Release } | null = null;
async function activeRelease(env: Env): Promise<Release> {
  const row = await env.DB.prepare("SELECT id,object_key FROM releases WHERE active=1 ORDER BY created_at DESC LIMIT 1").first() as any;
  if (!row) throw new HTTPException(503, { message: "No content release is active." });
  if (releaseCache && releaseCache.key === row.id && releaseCache.expires > Date.now()) return releaseCache.data;
  const object = await env.CONTENT.get(row.object_key);
  if (!object) throw new HTTPException(503, { message: "Active content release is unavailable." });
  const data = await object.json() as Release;
  data.id = row.id;
  releaseCache = { key: row.id, expires: Date.now() + 30_000, data };
  return data;
}
async function currentProfile(c: any) {
  const token = tokenFromRequest(c.req.raw, c.env.APP_ORIGIN);
  if (!token) throw new HTTPException(401, { message: "Sign in to BirdAhead." });
  const row = await c.env.DB.prepare("SELECT profile_id,expires_at FROM auth_sessions WHERE token_hash=?").bind(await digest(token)).first() as any;
  if (!row || Number(row.expires_at) <= now()) throw new HTTPException(401, { message: "Your session has expired. Sign in again." });
  return String(row.profile_id);
}
async function authMiddleware(c: any, next: () => Promise<void>) {
  assertSameOrigin(c, c.env);
  c.set("profile", await currentProfile(c));
  await next();
}

function priorities(release: Release, location: string, day: string): Row[] {
  const profile = release.profiles[location];
  if (!profile || !/^\d{4}-\d{2}-\d{2}$/.test(day) || Number.isNaN(Date.parse(day))) throw new HTTPException(400, { message: "Choose a supported county and date." });
  const [year, month, date] = day.split("-").map(Number);
  const actual = new Date(Date.UTC(year, month - 1, date));
  if (actual.toISOString().slice(0, 10) !== day) throw new HTTPException(400, { message: "Invalid calendar date." });
  const template = new Date(Date.UTC(2001, month - 1, month === 2 ? Math.min(date, 28) : date));
  return release.species.map((s) => {
    const rows = profile.rows.filter((r) => r.species_code === s.ebird_species_code);
    const at = (d: Date) => rows.find((r) => r.start <= `2001-${d.toISOString().slice(5, 10)}` && `2001-${d.toISOString().slice(5, 10)}` < r.end);
    const current = at(template), value = current?.frequency ?? null;
    const future = [14,21,28].map((n) => at(new Date(template.getTime()+n*86400000))?.frequency).filter((v): v is number => v !== undefined && v !== null);
    const peak = future.length ? Math.max(...future) : null;
    const rise = peak === null || value === null ? null : Math.max(0, peak - value);
    return { species_code: s.ebird_species_code, current_reporting_frequency: value, future_14_28_day_max: peak,
      approaching_window_rise: rise, learning_priority: value === null || rise === null ? null : Number((.6*value+.4*rise).toFixed(8)),
      sample_size: current?.sample_size ?? null, bin_start: current?.start ?? null, bin_end: current?.end ?? null };
  }).sort((a,b) => (b.learning_priority ?? -1)-(a.learning_priority ?? -1) || a.species_code.localeCompare(b.species_code));
}
const credit = (a: Asset) => ({ creator: a.creator, attribution: a.attribution, source_url: a.source_url, license_url: a.license_url,
  license_code: a.license_code ?? null, source: a.source ?? null, validation: "Automatically accepted with source and model evidence; no expert verification claimed",
  vocalization: a.vocalization, derivative_of: a.derivative_of ?? null });
const PUBLIC_EBIRD_TERMS = 'https://www.birds.cornell.edu/home/ebird-data-access-terms-of-use/';
const PUBLIC_EBIRD_CITATION = 'eBird. 2016-2025. eBird observation data; derived seasonal summaries. Cornell Lab of Ornithology, Ithaca, New York. https://ebird.org.';
const PUBLIC_SCOPE = 'Public noncommercial educational use; no advertising, monetization or paid access.';
const isPublicAsset = (a: Asset) => a.public_delivery === true && a.permitted_delivery !== false;
function publicAssets(release: Release, suppressed: Set<string>) { return release.assets.filter((a) => !suppressed.has(a.id) && isPublicAsset(a)); }
function publicCredit(a: Asset) { return { ...credit(a), public_use_basis: a.public_use_basis ?? null, public_license_notice: a.public_license_notice ?? null,
  public_noncommercial_only: a.public_noncommercial_only ?? null, public_share_alike: a.public_share_alike ?? null }; }
function publicAssetCard(a: Asset) { return { id:a.id, kind:a.kind, species_code:a.species_code, media_url:`/media/public/${a.id}`, bytes:Number(a.bytes??0),
  sha256:a.sha256??null, content_type:a.content_type??a.media_format??(a.kind==='photo'?'image/jpeg':'audio/mpeg'), creator:a.creator,
  attribution:a.attribution, source_url:a.source_url, license_url:a.license_url, license_code:a.license_code??null, source:a.source??null,
  public_use_basis:a.public_use_basis??null, public_license_notice:a.public_license_notice??null, public_noncommercial_only:a.public_noncommercial_only??null,
  public_share_alike:a.public_share_alike??null, derivative:!!a.derivative_of, vocalization:a.vocalization??null, sex:a.sex??null, age:a.age??null,
  plumage:a.plumage??null, duration_seconds:(a.technical_metrics as any)?.duration_seconds??a.duration_seconds??null, target_bbox_xyxy:a.target_bbox_xyxy??null, validation:'Member of the accepted public collection; automated corroboration only, not expert certification' }; }
function publicRanked(release: Release, location: string, day: string, visible: Asset[]): Row[] { const counts=mediaCounts(release,visible);
  return priorities(release,location,day).map((r)=>{ const s=speciesOf(release,r.species_code); const c=counts.get(r.species_code)??{photos:0,audio:0};
    return {...r,name:s.common_name,scientific_name:s.scientific_name,confusion_pair:s.confusion_pair??null,photos:c.photos,recordings:c.audio,photo_ready:c.photos>=1,audio_ready:c.audio>=1}; }); }
function publicSeasonality(release: Release, location: string, code: string): Row { const profile=release.profiles[location];
  if(!profile) throw new HTTPException(400,{message:'Choose a supported county.'}); const species=release.species.find((s)=>s.ebird_species_code===code);
  if(!species) throw new HTTPException(404,{message:'Species not found.'}); return { code, name:species.common_name, scientific_name:species.scientific_name,
    bins: profile.rows.filter((r)=>r.species_code===code).map((r)=>({start:r.start,end:r.end,frequency:r.frequency,sample_size:r.sample_size,value_status:r.value_status??null})), metadata:{start_year:profile.metadata.start_year,end_year:profile.metadata.end_year,bin_definition:profile.metadata.bin_definition,units:profile.metadata.units,taxonomy_version:profile.metadata.taxonomy_version,source_taxonomy_version:profile.metadata.source_taxonomy_version??null,source_note:profile.metadata.source_note??null} }; }
async function dbRows(db: D1Database, sql: string, ...bind: any[]): Promise<Row[]> {
  return (await db.prepare(sql).bind(...bind).all()).results;
}
async function hidden(db: D1Database) {
  return new Set((await dbRows(db, "SELECT asset_id FROM flags")).map((r) => String(r.asset_id)));
}
async function history(db: D1Database, profile: string) {
  return dbRows(db, "SELECT * FROM attempts WHERE profile_id=? AND asset_id NOT IN (SELECT asset_id FROM flags) ORDER BY at", profile);
}
const speciesOf = (release: Release, code: string) => release.species.find((s) => s.ebird_species_code === code) ?? { ebird_species_code: code, common_name: code, scientific_name: "Retained attempt; species absent from this release" };
function mediaCounts(release: Release, visible: Asset[]) {
  const map = new Map<string,{photos:number;audio:number}>();
  for (const a of visible) {
    const row = map.get(a.species_code) ?? { photos:0, audio:0 };
    if (a.kind === "photo") row.photos++; else row.audio++;
    map.set(a.species_code,row);
  }
  return map;
}
function visibleAssets(release: Release, suppressed: Set<string>) {
  return release.assets.filter((a) => !suppressed.has(a.id));
}
async function publicSession(db: D1Database, release: Release, id: string, profile: string) {
  const session = await db.prepare("SELECT * FROM sessions WHERE id=? AND profile_id=?").bind(id, profile).first() as any;
  if (!session) throw new HTTPException(404, { message: "Session not found." });
  const family = (release as Row).compatibility_key ?? release.id;
  const compatible = session.release_family ? session.release_family === family : session.release_id === release.id;
  if (!compatible) throw new HTTPException(409, { message: "Content release changed; start a new session." });
  const suppressed = await hidden(db);
  const visible = visibleAssets(release, suppressed);
  const byId = new Map(visible.map((a) => [a.id, a]));
  const questions = (JSON.parse(session.questions) as Row[]).filter((q) => byId.has(q.asset_id));
  const answered = await dbRows(db, "SELECT * FROM attempts WHERE session_id=? ORDER BY at", id);
  const completed = new Set(answered.map((a) => a.question_id));
  const question = questions.find((q) => !completed.has(q.id) && !suppressed.has(q.asset_id));
  const elapsed = Math.max(0, (Date.now() - Date.parse(session.started)) / 1000);
  const current = question ? byId.get(question.asset_id) : undefined;
  const missed = answered.filter((a) => a.outcome === "incorrect").map((a) => ({ name: speciesOf(release, a.species_code).common_name, kind: a.kind,
    choice: ["unknown","insufficient"].includes(a.choice) ? null : speciesOf(release, a.choice).common_name }));
  const uncertain = answered.filter((a) => a.outcome === "uncertain").map((a) => ({ name: speciesOf(release, a.species_code).common_name, kind: a.kind }));
  return { id, profile_id: session.profile_id, location: session.location, outing_day: session.outing_day, kind: session.kind, mode: session.mode,
    answered: answered.length, total: questions.length, elapsed_seconds: elapsed, done: !question || elapsed >= 300,
    data_vintage: release.data_vintage ?? null, coverage_summary: release.coverage_summary ?? null,
    summary: { recognized: answered.filter((a) => a.outcome === "correct").length, practice: answered.filter((a) => a.outcome === "incorrect").length,
      uncertain: answered.filter((a) => a.outcome === "uncertain").length, distinct_examples: new Set(answered.map((a) => a.asset_id)).size,
      missed: missed.slice(0,10), uncertain_species: uncertain.slice(0,10),
      coverage_note: "Practice results are not a mastery claim. Missing examples stay explicit; unknown media traits remain unknown." },
    question: question && current && elapsed < 300 ? { id: question.id, asset_id: question.asset_id, media_url: `/media/${question.asset_id}`, compare_with: (()=>{const cp=(speciesOf(release,current.species_code) as any).confusion_pair; return cp?.ebird_species_code?{code:cp.ebird_species_code,name:cp.common_name}:null;})(), kind: session.kind,
      options: question.options.map((code: string) => ({ code, name: speciesOf(release, code).common_name })), credit: credit(current), bbox: current.target_bbox_xyxy ?? null,
      source_evidence: current.source_verified ? "Source-verified record; automated model corroboration is not expert certification" : null } : null };
}
const app = new Hono<AppEnv>();
// Legacy Apple-generated narration is no longer deliverable. Static asset
// storage may retain old immutable files, so deny the path explicitly.
app.use("/narration/*", async (c, next) => { if (c.req.path.endsWith(".m4a")) return c.notFound(); await next(); });
app.use("*", async (c, next) => {
  const url = new URL(c.req.url); const host = url.host; const canonical = originHost(c.env.APP_ORIGIN);
  if (host === "www.birdahead.com" && canonical === "birdahead.com") return c.redirect("https://birdahead.com" + url.pathname + url.search, 308);
  if (canonical === "birdahead.com" && host !== "birdahead.com") return c.text("BirdAhead is available at https://birdahead.com.", 404);
  await next();
  c.header("X-Content-Type-Options", "nosniff"); c.header("Referrer-Policy", "no-referrer"); c.header("X-Frame-Options", "DENY");
  if (c.req.path.startsWith("/api/") || c.req.path.startsWith("/media/") || c.req.path === "/health" || c.req.path.startsWith("/admin")) c.header("X-Robots-Tag", "noindex, nofollow");
  c.header("Cross-Origin-Resource-Policy", "same-origin");
  c.header("Permissions-Policy", "camera=(), microphone=(), geolocation=(), payment=()");
  c.header("Content-Security-Policy", "default-src 'self'; script-src 'self' https://analytics.aismallbizguru.com; style-src 'self' 'unsafe-inline'; img-src 'self' data:; media-src 'self'; connect-src 'self' https://analytics.aismallbizguru.com; worker-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'");
  if (url.protocol === "https:") c.header("Strict-Transport-Security", "max-age=31536000");
  const path = c.req.path; const publicPath = path.startsWith("/api/public/") || path.startsWith("/media/public/") || path === "/robots.txt" || path === "/sitemap.xml" || path === "/sources" || path === "/privacy" || path.startsWith("/birds/") || path.startsWith("/regions/");
  if (!publicPath && (path.startsWith("/api/") || path.startsWith("/media/") || path === "/sw.js" || path === "/health" || c.res.headers.get("Content-Type")?.includes("text/html"))) c.header("Cache-Control", "no-store");
});
app.onError((err, c) => {
  if (err instanceof HTTPException) return c.json({ error: err.message }, err.status);
  console.error("BirdAhead request failed.");
  return c.json({ error: "BirdAhead could not complete this request." }, 500);
});
app.get("/health", async (c) => {
  const release = await activeRelease(c.env).catch(() => null);
  return c.json({ ok: true, app: "birdahead", revision: c.env.DEPLOY_REVISION, release: release?.id ?? null, auth: "session" });
});
app.use("/api/public/*", async (c, next) => {
  const ip = c.req.header("CF-Connecting-IP") ?? "local";
  if (c.env.PUBLIC_LIMIT && !(await c.env.PUBLIC_LIMIT.limit({ key: "public:" + ip })).success) {
    c.header("Retry-After", "60"); throw new HTTPException(429, { message: "Too many public requests. Try again shortly." });
  }
  await next();
  if (!c.res.headers.has("Cache-Control")) c.header("Cache-Control", "public, max-age=60, stale-while-revalidate=300");
});
app.use("/media/public/*", async (c, next) => {
  const ip = c.req.header("CF-Connecting-IP") ?? "local";
  if (c.env.PUBLIC_LIMIT && !(await c.env.PUBLIC_LIMIT.limit({ key: "public-media:" + ip })).success) return c.text("Too many media requests.", 429, { "Retry-After": "60" });
  await next();
});
app.get("/api/public/bootstrap", async (c) => {
  const release = await activeRelease(c.env); const visible = publicAssets(release, await hidden(c.env.DB)); const counts = mediaCounts(release, visible);
  const species = release.species.map((s) => { const row = counts.get(s.ebird_species_code) ?? { photos: 0, audio: 0 };
    return { code: s.ebird_species_code, name: s.common_name, scientific_name: s.scientific_name, priority_rank: s.priority_rank ?? null,
      public_photos: row.photos, public_recordings: row.audio, photo_practice_ready: row.photos >= 2, audio_practice_ready: row.audio >= 2,
      coverage_gap: row.photos < 2 && row.audio < 2 }; });
  return c.json({ schema: "birdahead-public-bootstrap-v1", release_id: release.id, counties: release.counties, species,
    public_assets: visible.length, public_photo_assets: visible.filter((a) => a.kind === "photo").length, public_audio_assets: visible.filter((a) => a.kind === "audio").length,
    coverage: { species: species.length, public_photo_species: species.filter((s) => s.public_photos > 0).length, public_audio_species: species.filter((s) => s.public_recordings > 0).length,
      photo_practice_ready: species.filter((s) => s.photo_practice_ready).length, audio_practice_ready: species.filter((s) => s.audio_practice_ready).length, gaps: species.filter((s) => s.coverage_gap).length },
    data_vintage: release.data_vintage ?? null, data_source: { citation: PUBLIC_EBIRD_CITATION, terms_url: PUBLIC_EBIRD_TERMS, notice: release.public_data_terms?.ebird_notice ?? "Derived seasonal summaries only; raw histogram exports are not public.", scope: PUBLIC_SCOPE },
    limitations: "Historical reporting frequency reflects complete checklists, not encounter probability. Automated media acceptance is not expert verification." });
});
app.get("/api/public/curriculum", async (c) => {
  const location = c.req.query("location") ?? ""; const day = c.req.query("day") ?? new Date().toISOString().slice(0, 10);
  const release = await activeRelease(c.env); const visible = publicAssets(release, await hidden(c.env.DB)); const ranked = publicRanked(release, location, day, visible);
  const arriving = ranked.filter((r) => (r.approaching_window_rise ?? 0) > 0).sort((a, b) => (b.approaching_window_rise ?? -1) - (a.approaching_window_rise ?? -1)).slice(0, 25);
  return c.json({ location, day, data_vintage: release.data_vintage ?? null, data_source: { citation: PUBLIC_EBIRD_CITATION, terms_url: PUBLIC_EBIRD_TERMS }, priorities: ranked, arriving_soon: arriving,
    note: "Here Now uses historical complete-checklist reporting frequency for the selected date; Arriving Soon uses the next 14–28 day rise. Neither is an encounter forecast." });
});
app.get("/api/public/seasonality", async (c) => {
  const location = c.req.query("location") ?? ""; const code = c.req.query("code") ?? ""; const release = await activeRelease(c.env); const detail = publicSeasonality(release, location, code);
  return c.json({ location, ...detail, data_vintage: release.data_vintage ?? null, data_source: { citation: PUBLIC_EBIRD_CITATION, terms_url: PUBLIC_EBIRD_TERMS } });
});
app.get("/api/public/library", async (c) => {
  const query = (c.req.query("q") ?? "").trim().toLowerCase(); const kind = c.req.query("kind") ?? "all";
  const location = c.req.query("location") ?? Object.keys((await activeRelease(c.env)).counties)[0] ?? ""; const day = c.req.query("day") ?? new Date().toISOString().slice(0, 10);
  const release = await activeRelease(c.env); const visible = publicAssets(release, await hidden(c.env.DB)); const counts = mediaCounts(release, visible); const grouped = new Map<string, Asset[]>();
  for (const a of visible) { if (kind !== "all" && a.kind !== kind) continue; const list = grouped.get(a.species_code) ?? []; list.push(a); grouped.set(a.species_code, list); }
  const seasonal = new Map(priorities(release, location, day).map((r) => [r.species_code, r]));
  const species = release.species.map((s) => { const count = counts.get(s.ebird_species_code) ?? { photos: 0, audio: 0 }; const sr = seasonal.get(s.ebird_species_code);
    return { code: s.ebird_species_code, name: s.common_name, scientific_name: s.scientific_name, priority_rank: s.priority_rank ?? null, confusion_pair: s.confusion_pair ?? null,
      photos: count.photos, recordings: count.audio, photo_practice_ready: count.photos >= 2, audio_practice_ready: count.audio >= 2, coverage_gap: count.photos < 2 && count.audio < 2,
      current_reporting_frequency: sr?.current_reporting_frequency ?? null, approaching_window_rise: sr?.approaching_window_rise ?? null, sample_size: sr?.sample_size ?? null, bin_start: sr?.bin_start ?? null, bin_end: sr?.bin_end ?? null,
      assets: (grouped.get(s.ebird_species_code) ?? []).map(publicAssetCard) }; })
    .filter((r) => !query || r.name.toLowerCase().includes(query) || r.scientific_name.toLowerCase().includes(query) || r.code.toLowerCase().includes(query))
    .sort((a, b) => (a.priority_rank ?? 9999) - (b.priority_rank ?? 9999) || a.name.localeCompare(b.name));
  return c.json({ location, day, query, kind, release_id: release.id, data_vintage: release.data_vintage ?? null, data_source: { citation: PUBLIC_EBIRD_CITATION, terms_url: PUBLIC_EBIRD_TERMS }, species });
});
app.get("/api/public/species/:code", async (c) => {
  const release = await activeRelease(c.env); const visible = publicAssets(release, await hidden(c.env.DB)); const code = c.req.param("code"); const location = c.req.query("location") ?? Object.keys(release.counties)[0] ?? "";
  const detail = publicSeasonality(release, location, code); const ranked = publicRanked(release, location, new Date().toISOString().slice(0, 10), visible).find((r) => r.species_code === code);
  return c.json({ ...detail, location, priority: ranked ?? null, assets: visible.filter((a) => a.species_code === code).map(publicAssetCard), data_vintage: release.data_vintage ?? null,
    data_source: { citation: PUBLIC_EBIRD_CITATION, terms_url: PUBLIC_EBIRD_TERMS, notice: release.public_data_terms?.ebird_notice ?? null } });
});
app.get("/api/public/practice", async (c) => {
  const location = c.req.query("location") ?? ""; const day = c.req.query("day") ?? new Date().toISOString().slice(0, 10); const kind = c.req.query("kind") === "audio" ? "audio" : "photo";
  const mode = c.req.query("mode") === "recall" ? "recall" : "choice"; const focus = ["now", "arriving", "weak"].includes(c.req.query("focus") ?? "") ? c.req.query("focus")! : "now";
  const release = await activeRelease(c.env); const visible = publicAssets(release, await hidden(c.env.DB)); const ranked = publicRanked(release, location, day, visible);
  let candidates = ranked.filter((r) => kind === "photo" ? r.photo_ready : r.audio_ready);
  if (focus === "now") candidates = candidates.filter((r) => (r.current_reporting_frequency ?? 0) > 0);
  if (focus === "arriving") candidates = candidates.filter((r) => (r.approaching_window_rise ?? 0) > 0);
  if (candidates.length < 2) throw new HTTPException(400, { message: "Not enough public media for this practice mode." });
  const questions: Row[] = []; const used = new Set<string>();
  for (let round = 0; round < 4 && questions.length < 10; round++) for (const candidate of candidates) {
    if (questions.length >= 10) break; const pool = visible.filter((a) => a.species_code === candidate.species_code && a.kind === kind && !used.has(a.id)); if (!pool.length) continue;
    const asset = pool[0]; used.add(asset.id); const qid = crypto.randomUUID();
    const otherCodes = candidates.filter((r) => r.species_code !== candidate.species_code).slice(0, 8).map((r) => r.species_code);
    const options = mode === "choice" ? [candidate.species_code, ...otherCodes.slice(0, 3)] : [];
    const hashed = await Promise.all(options.map(async (code) => [code, await digest(qid + code)] as const)); hashed.sort((a, b) => String(a[1]).localeCompare(String(b[1])));
    questions.push({ id: qid, asset_id: asset.id, species_code: candidate.species_code, name: candidate.name, compare_with: candidate.confusion_pair?.ebird_species_code ? { code: candidate.confusion_pair.ebird_species_code, name: candidate.confusion_pair.common_name } : null, kind, mode, media_url: `/media/public/${asset.id}`,
      options: hashed.map(([code]) => ({ code, name: speciesOf(release, code).common_name })), answer_code: candidate.species_code, credit: publicCredit(asset), bbox: asset.target_bbox_xyxy ?? null });
  }
  if (!questions.length) throw new HTTPException(400, { message: "No public practice questions are available for these settings." });
  return c.json({ schema: "birdahead-public-practice-v1", guest: true, location, day, kind, mode, focus, questions,
    data_source: { citation: PUBLIC_EBIRD_CITATION, terms_url: PUBLIC_EBIRD_TERMS }, note: "Guest practice is scored in this browser; no guest account or server-side guest history is created." });
});

app.post("/api/login", async (c) => {
  assertSameOrigin(c, c.env);
  const ip = c.req.header("CF-Connecting-IP") ?? "local";
  if (c.env.LOGIN_LIMIT && !(await c.env.LOGIN_LIMIT.limit({ key: "login:" + ip })).success) {
    c.header("Retry-After", "60"); throw new HTTPException(429, { message: "Too many attempts. Try again in a minute." });
  }
  const body = await c.req.json().catch(() => null) as Row | null;
  const who = body?.profile === "heather" ? "heather" : body?.profile === "hank" ? "hank" : null;
  const supplied = typeof body?.key === "string" ? body.key.trim() : "";
  if (!who || supplied.length < 16 || supplied.length > 256) throw new HTTPException(400, { message: "Choose Hank or Heather and enter the access key." });
  const expected = who === "hank" ? c.env.HANK_KEY : c.env.HEATHER_KEY;
  if (!expected) throw new HTTPException(503, { message: "Household access is not configured." });
  if (!safeEqual(await digest(supplied), await digest(expected))) throw new HTTPException(401, { message: "That access key was not accepted." });
  const token = randomToken(); const created = now();
  await c.env.DB.batch([
    c.env.DB.prepare("DELETE FROM auth_sessions WHERE expires_at<=?").bind(created),
    c.env.DB.prepare("INSERT INTO auth_sessions(token_hash,profile_id,expires_at,created_at) VALUES(?,?,?,?)").bind(await digest(token), who, created + 60*60*24*30, created),
  ]);
  c.header("Set-Cookie", sessionCookie(c.env.APP_ORIGIN, token));
  return c.json({ ok: true, profile_id: who, name: profileNames[who] });
});
app.get("/api/session", async (c) => { const p = await currentProfile(c); return c.json({ authenticated: true, profile_id: p, name: profileNames[p] }); });
app.post("/api/logout", async (c) => {
  assertSameOrigin(c, c.env);
  const token = tokenFromRequest(c.req.raw, c.env.APP_ORIGIN);
  if (token) await c.env.DB.prepare("DELETE FROM auth_sessions WHERE token_hash=?").bind(await digest(token)).run();
  c.header("Set-Cookie", sessionCookie(c.env.APP_ORIGIN, "", 0));
  return c.json({ ok: true });
});
app.use("/api/*", async (c, next) => { if (!["/api/login"].includes(c.req.path) && !c.req.path.startsWith("/api/admin/")) await authMiddleware(c, next); else await next(); });
app.get("/api/bootstrap", async (c) => {
  const profile = c.get("profile"); const release = await activeRelease(c.env); const suppressed = await hidden(c.env.DB);
  const visible = visibleAssets(release, suppressed); const counts = mediaCounts(release, visible);
  const speciesRows = release.species.map((s) => {
    const row = counts.get(s.ebird_species_code) ?? { photos:0, audio:0 };
    return { code:s.ebird_species_code, name:s.common_name, scientific_name:s.scientific_name, pilot:s.pilot ?? false, priority_rank:s.priority_rank ?? null,
      photos:row.photos, recordings:row.audio, photo:row.photos>=2, audio:row.audio>=2, photo_target_met:row.photos>=5, audio_target_met:row.audio>=3,
      coverage_gap:row.photos<2 && row.audio<2 };
  });
  const firstProfile = Object.values(release.profiles ?? {})[0];
  const vintage = release.data_vintage ?? (firstProfile ? { start_year:firstProfile.metadata.start_year, end_year:firstProfile.metadata.end_year,
    source_taxonomy_version:firstProfile.metadata.source_taxonomy_version ?? null, taxonomy_version:firstProfile.metadata.taxonomy_version,
    bin_definition:firstProfile.metadata.bin_definition, units:firstProfile.metadata.units,
    source_note:"Owner-supplied county histogram exports; source taxonomy release unknown." } : null);
  return c.json({ release_id:release.id, release_schema:release.schema, compatibility_key:(release as Row).compatibility_key ?? release.id,
    profile_id:profile, profile:profile, profile_name:profileNames[profile], profiles:[{id:"hank",name:"Hank"},{id:"heather",name:"Heather"}],
    counties:release.counties, species:speciesRows, coverage:{ photo:speciesRows.filter((s)=>s.photo).length, audio:speciesRows.filter((s)=>s.audio).length,
      species:speciesRows.length, photo_target:speciesRows.filter((s)=>s.photo_target_met).length, audio_target:speciesRows.filter((s)=>s.audio_target_met).length,
      gaps:speciesRows.filter((s)=>s.coverage_gap).length }, coverage_summary:release.coverage_summary ?? null, data_vintage:vintage,
    confusion_pairs:release.confusion_pairs ?? [], source:"eBird 2016–2025, owner-supplied county histogram exports; 48 native bins/year",
    limitations:"Reporting frequency reflects submitted complete checklists, not your chance of an encounter. Sparse samples and observer/habitat bias remain. Missing media coverage is explicit." });
});
app.get("/api/curriculum", async (c) => {
  const profile = c.get("profile"); const location = c.req.query("location") ?? ""; const day = c.req.query("day") ?? new Date().toISOString().slice(0,10);
  const release = await activeRelease(c.env); const past = await history(c.env.DB, profile); const visible = visibleAssets(release, await hidden(c.env.DB)); const media = mediaCounts(release, visible);
  const ranked = priorities(release, location, day).map((r) => { const s = speciesOf(release, r.species_code); const counts = media.get(r.species_code) ?? {photos:0,audio:0};
    return { ...r, name:s.common_name, scientific_name:s.scientific_name, pilot:s.pilot ?? false, priority_rank:s.priority_rank ?? null, photos:counts.photos, recordings:counts.audio,
      photo:counts.photos>=2, audio:counts.audio>=2, photo_target_met:counts.photos>=5, audio_target_met:counts.audio>=3, coverage_gap:counts.photos<2 && counts.audio<2,
      attempts:past.filter((a)=>a.species_code===r.species_code).length, needs_practice:past.filter((a)=>a.species_code===r.species_code && a.outcome!=="correct").length }; });
  return c.json({ location, day, data_vintage:release.data_vintage ?? null, coverage_summary:release.coverage_summary ?? null, priorities:ranked });
});
app.get("/api/library", async (c) => {
  const query=(c.req.query("q")??"").trim().toLowerCase(); const kind=c.req.query("kind")??"all"; const location=c.req.query("location")??Object.keys((await activeRelease(c.env)).counties)[0]??""; const day=c.req.query("day")??new Date().toISOString().slice(0,10);
  const release=await activeRelease(c.env); const visible=visibleAssets(release,await hidden(c.env.DB)); const media=mediaCounts(release,visible); const grouped=new Map<string,Asset[]>();
  for(const a of visible){ if(kind!=="all" && a.kind!==kind)continue; const list=grouped.get(a.species_code)??[]; list.push(a); grouped.set(a.species_code,list); }
  const seasonal=new Map(priorities(release,location,day).map((r)=>[r.species_code,r]));
  const rows=release.species.map((s)=>{ const counts=media.get(s.ebird_species_code)??{photos:0,audio:0}; const sr=seasonal.get(s.ebird_species_code);
    return { code:s.ebird_species_code,name:s.common_name,scientific_name:s.scientific_name,pilot:s.pilot??false,priority_rank:s.priority_rank??null,confusion_pair:s.confusion_pair??null,
      selection_rationale:s.selection_rationale??[],photos:counts.photos,recordings:counts.audio,photo_target_met:counts.photos>=5,audio_target_met:counts.audio>=3,
      photo_practice_ready:counts.photos>=2,audio_practice_ready:counts.audio>=2,coverage_gap:counts.photos<2&&counts.audio<2,current_reporting_frequency:sr?.current_reporting_frequency??null,
      approaching_window_rise:sr?.approaching_window_rise??null,sample_size:sr?.sample_size??null,bin_start:sr?.bin_start??null,bin_end:sr?.bin_end??null,
      assets:(grouped.get(s.ebird_species_code)??[]).map((a)=>({id:a.id,kind:a.kind,species_code:a.species_code,media_url:`/media/${a.id}`,creator:a.creator,attribution:a.attribution,source_url:a.source_url,
        license_url:a.license_url,license_code:a.license_code??null,source:a.source??null,vocalization:a.vocalization,sex:a.sex??null,age:a.age??null,plumage:a.plumage??null,
        biological_attribute_status:a.biological_attribute_status??null,target_bbox_xyxy:a.target_bbox_xyxy??null,derivative_of:a.derivative_of??null,
        duration_seconds:a.technical_metrics?.duration_seconds??null,validation:"Automatically accepted source/model corroboration; no expert verification claimed" })) };
  }).filter((r)=>!query||r.name.toLowerCase().includes(query)||r.scientific_name.toLowerCase().includes(query)||r.code.toLowerCase().includes(query))
    .sort((a,b)=>(a.priority_rank??9999)-(b.priority_rank??9999)||a.name.localeCompare(b.name));
  return c.json({location,day,query,kind,data_vintage:release.data_vintage??null,coverage_summary:release.coverage_summary??null,species:rows});
});
app.get("/api/coverage", async (c) => {
  const location=c.req.query("location")??Object.keys((await activeRelease(c.env)).counties)[0]??""; const release=await activeRelease(c.env); const visible=visibleAssets(release,await hidden(c.env.DB));
  const count=(code:string,kind:"photo"|"audio")=>visible.filter((a)=>a.kind===kind&&a.species_code===code).length; const describe=(code:string)=>({code,name:speciesOf(release,code).common_name,photos:count(code,"photo"),audio:count(code,"audio")});
  const seasons:Record<string,string>={winter:"2026-01-15",spring_migration:"2026-05-05",summer:"2026-07-15",fall_migration:"2026-09-10",now:new Date().toISOString().slice(0,10)}; const decks:Record<string,Row>={};
  for(const [label,day] of Object.entries(seasons)){ const ranking=priorities(release,location,day).filter((r)=>(r.current_reporting_frequency??0)>0).slice(0,25);
    decks[label]={day,deck_size:ranking.length,photo_practice_ready:ranking.filter((r)=>count(r.species_code,"photo")>=2).length,audio_practice_ready:ranking.filter((r)=>count(r.species_code,"audio")>=2).length,
      photo_and_audio_target:ranking.filter((r)=>count(r.species_code,"photo")>=5&&count(r.species_code,"audio")>=3).length,
      photo_gaps:ranking.filter((r)=>count(r.species_code,"photo")<2).slice(0,12).map((r)=>describe(r.species_code)),audio_gaps:ranking.filter((r)=>count(r.species_code,"audio")<2).slice(0,12).map((r)=>describe(r.species_code)) }; }
  const arriving=priorities(release,location,new Date().toISOString().slice(0,10)).filter((r)=>(r.approaching_window_rise??0)>0).sort((a,b)=>(b.approaching_window_rise??0)-(a.approaching_window_rise??0)).slice(0,25);
  return c.json({location,data_vintage:release.data_vintage??null,coverage_summary:release.coverage_summary??null,decks,arriving_soon:{deck_size:arriving.length,photo_practice_ready:arriving.filter((r)=>count(r.species_code,"photo")>=2).length,
    audio_practice_ready:arriving.filter((r)=>count(r.species_code,"audio")>=2).length,gaps:arriving.filter((r)=>count(r.species_code,"photo")<2).slice(0,12).map((r)=>describe(r.species_code))}});
});
app.get("/api/progress", async (c) => {
  const profile=c.get("profile"); const release=await activeRelease(c.env); const past=await history(c.env.DB,profile);
  const confusion=await dbRows(c.env.DB,`SELECT species_code,choice,kind,COUNT(*) AS count FROM attempts WHERE profile_id=? AND outcome='incorrect' AND mode='choice' AND asset_id NOT IN (SELECT asset_id FROM flags) GROUP BY species_code,choice,kind ORDER BY count DESC`,profile);
  const flags=await dbRows(c.env.DB,"SELECT asset_id,reason,at FROM flags WHERE profile_id=? ORDER BY at DESC",profile);
  return c.json({attempts:past.length,distinct_examples:new Set(past.map((a)=>a.asset_id)).size,by_species:release.species.flatMap((s)=>(["photo","audio"] as const).map((kind)=>{const records=past.filter((a)=>a.species_code===s.ebird_species_code&&a.kind===kind);return {name:s.common_name,code:s.ebird_species_code,kind,attempts:records.length,recognized:records.filter((a)=>a.outcome==="correct").length,distinct_examples:new Set(records.map((a)=>a.asset_id)).size,label:records.length?"Practicing":"New"}})).filter((s)=>s.attempts),
    confusion:confusion.map((r)=>({...r,from:speciesOf(release,r.species_code).common_name,to:speciesOf(release,r.choice).common_name,from_code:r.species_code,to_code:r.choice})),flags,profile_id:profile,profile_name:profileNames[profile]});
});
app.post("/api/sessions", async (c) => {
  const profile=c.get("profile"); const body=await c.req.json().catch(()=>null) as Row|null;
  const location=body?.location, day=body?.day, kind=body?.kind, mode=body?.mode, focus=body?.focus;
  if(!location||!day||!["photo","audio"].includes(kind)||!["choice","recall"].includes(mode)||!["now","arriving","weak"].includes(focus)) throw new HTTPException(400,{message:"Invalid practice settings."});
  const release=await activeRelease(c.env); const ranked=priorities(release,location,day); const visible=visibleAssets(release,await hidden(c.env.DB)); const counts=mediaCounts(release,visible);
  const pool=release.species.filter((s)=>(counts.get(s.ebird_species_code)?.photos??0)>=2||false);
  const poolForKind=release.species.filter((s)=>{const v=counts.get(s.ebird_species_code)??{photos:0,audio:0};return kind==="photo"?v.photos>=2:v.audio>=2;});
  if(poolForKind.length<2) throw new HTTPException(400,{message:"Not enough accepted examples for this practice mode."});
  const past=await history(c.env.DB,profile); let nowms=Date.now();
  const score=(code:string)=>{const r=ranked.find((x)=>x.species_code===code)??{approaching_window_rise:0,learning_priority:0,current_reporting_frequency:0};const h=past.filter((a)=>a.species_code===code&&a.kind===kind&&a.mode===mode);const last=h.at(-1);let streak=0;for(const a of h.slice(-4).reverse()){if(a.outcome!=="correct")break;streak++;}const due=!last||last.outcome!=="correct"||nowms-Date.parse(last.at)>Math.pow(2,streak)*86400000;const weaknesses=h.slice(-5).filter((a)=>a.outcome!=="correct").length/Math.max(1,Math.min(h.length,5));return (focus==="arriving"?(r.approaching_window_rise??0):(r.learning_priority??0))+(due?.12:0)+weaknesses*(focus==="weak"?.7:.15);};
  const order=poolForKind.filter((s)=>{const r=ranked.find((x)=>x.species_code===s.ebird_species_code)??{approaching_window_rise:0,current_reporting_frequency:0};return focus==="weak"||(focus==="arriving"?(r.approaching_window_rise??0)>0:(r.current_reporting_frequency??0)>0);}).sort((a,b)=>score(b.ebird_species_code)-score(a.ebird_species_code)||a.ebird_species_code.localeCompare(b.ebird_species_code));
  if(!order.length) throw new HTTPException(400,{message:"No supported priorities for this focus and date; choose Here now or another date."});
  const questions:Row[]=[]; const used=new Set<string>();
  for(let round=0;round<5&&questions.length<10;round++) for(const s of order){
    const candidates=visible.filter((a)=>a.kind===kind&&a.species_code===s.ebird_species_code&&!used.has(a.id));
    candidates.sort((a,b)=>past.filter((h)=>h.asset_id===a.id).length-past.filter((h)=>h.asset_id===b.id).length||a.id.localeCompare(b.id));
    const asset=candidates[0]; if(!asset||questions.length>=10)continue; used.add(asset.id); const qid=crypto.randomUUID();
    const mistakes=past.filter((h)=>h.species_code===s.ebird_species_code&&h.outcome==="incorrect"&&h.mode==="choice").map((h)=>h.choice);
    const others=[...new Set([...mistakes,...poolForKind.map((p)=>p.ebird_species_code)])].filter((code)=>code!==s.ebird_species_code&&poolForKind.some((p)=>p.ebird_species_code===code)).slice(0,3);
    const optionCodes=[s.ebird_species_code,...others]; const hashed=await Promise.all(optionCodes.map(async(code)=>[code,await digest(qid+code)])); hashed.sort((a,b)=>String(a[1]).localeCompare(String(b[1])));
    questions.push({id:qid,asset_id:asset.id,correct:s.ebird_species_code,options:hashed.map((x)=>x[0])});
  }
  const id=crypto.randomUUID(); const family=(release as Row).compatibility_key??release.id;
  await c.env.DB.prepare("INSERT INTO sessions(id,profile_id,release_id,release_family,location,outing_day,kind,mode,started,questions) VALUES(?,?,?,?,?,?,?,?,?,?)").bind(id,profile,release.id,family,location,day,kind,mode,new Date().toISOString(),JSON.stringify(questions)).run();
  return c.json(await publicSession(c.env.DB,release,id,profile));
});
app.get("/api/sessions/:id", async (c) => { const release=await activeRelease(c.env); return c.json(await publicSession(c.env.DB,release,c.req.param("id"),c.get("profile"))); });
app.post("/api/answer", async (c) => {
  const profile=c.get("profile"); const body=await c.req.json(); const {session_id,question_id,choice}=body;
  const release=await activeRelease(c.env); const session=await c.env.DB.prepare("SELECT * FROM sessions WHERE id=? AND profile_id=?").bind(session_id,profile).first() as any;
  if(!session) throw new HTTPException(404,{message:"Session not found."}); const q=(JSON.parse(session.questions) as Row[]).find((x)=>x.id===question_id); if(!q)throw new HTTPException(400,{message:"Question is no longer active."});
  const existing=await c.env.DB.prepare("SELECT * FROM attempts WHERE question_id=? AND session_id=?").bind(question_id,session_id).first() as any;
  if(existing&&existing.choice!==choice)throw new HTTPException(400,{message:"This question already has a recorded answer."});
  const allowed=session.mode==="choice"?[...q.options,"unknown","insufficient"]:["known","unknown","insufficient"]; if(!allowed.includes(choice))throw new HTTPException(400,{message:"Choose a valid answer."});
  const asset=release.assets.find((a)=>a.id===q.asset_id); if(!asset)throw new HTTPException(409,{message:"Media example is no longer available."});
  const outcome=["unknown","insufficient"].includes(choice)?"uncertain":choice===q.correct||choice==="known"?"correct":"incorrect";
  if(!existing) await c.env.DB.prepare("INSERT INTO attempts(id,session_id,question_id,profile_id,asset_id,species_code,kind,mode,choice,outcome,at) VALUES(?,?,?,?,?,?,?,?,?,?,?)").bind(crypto.randomUUID(),session_id,question_id,profile,asset.id,q.correct,session.kind,session.mode,choice,outcome,new Date().toISOString()).run();
  const correct=speciesOf(release,q.correct); const own=release.assets.filter((a)=>a.species_code===q.correct);
  const coverage={photos:own.filter((a)=>a.kind==="photo").length,audio:own.filter((a)=>a.kind==="audio").length,photo_target_met:own.filter((a)=>a.kind==="photo").length>=5,audio_target_met:own.filter((a)=>a.kind==="audio").length>=3};
  const pairs=(release.confusion_pairs??[]) as Row[]; const pair=pairs.find((r)=>r.left===correct.common_name||r.right===correct.common_name); const partnerName=pair?(pair.left===correct.common_name?pair.right:pair.left):null; const partner=partnerName?release.species.find((s)=>s.common_name===partnerName):null;
  const resolved=existing?.outcome??outcome; const feedback=resolved==="correct"?(session.mode==="recall"?"You recalled the source identification. Try another example to test transfer, not memorization.":"Recognized. This is one accepted example; different photographs or recordings test transfer."):resolved==="incorrect"?`Not this time. The source identification is ${correct.common_name}. Review the source record rather than relying on an invented field mark.`:choice==="insufficient"?"Marked as not enough information. That is a valid outcome; flag the example if the media cannot support a species answer.":"Left uncertain. Uncertainty is recorded separately from an incorrect species guess.";
  return c.json({outcome:resolved,answer:{code:q.correct,name:correct.common_name,scientific_name:correct.scientific_name},credit:credit(asset),note:choice==="insufficient"?"Marked uncertain. Flag this example if the media cannot support a species identification.":null,feedback,coverage,comparison_pair:partner&&partnerName?{code:partner.ebird_species_code,name:partnerName,photos:release.assets.filter((a)=>a.kind==="photo"&&a.species_code===partner.ebird_species_code).length,audio:release.assets.filter((a)=>a.kind==="audio"&&a.species_code===partner.ebird_species_code).length}:null,evidence:"Automatically accepted source/model corroboration; no expert certification or field-mark annotation is implied."});
});
app.post("/api/reveal", async (c) => {
  const profile=c.get("profile"); const {session_id,question_id}=await c.req.json(); const release=await activeRelease(c.env); const session=await c.env.DB.prepare("SELECT * FROM sessions WHERE id=? AND profile_id=?").bind(session_id,profile).first() as any; if(!session)throw new HTTPException(404,{message:"Session not found."});
  const q=(JSON.parse(session.questions) as Row[]).find((x)=>x.id===question_id); if(!q)throw new HTTPException(400,{message:"Question is no longer active."}); const asset=release.assets.find((a)=>a.id===q.asset_id); if(!asset)throw new HTTPException(409,{message:"Media example is no longer available."});
  const correct=speciesOf(release,q.correct); const own=release.assets.filter((a)=>a.species_code===q.correct); const pairs=(release.confusion_pairs??[]) as Row[]; const pair=pairs.find((r)=>r.left===correct.common_name||r.right===correct.common_name); const partnerName=pair?(pair.left===correct.common_name?pair.right:pair.left):null; const partner=partnerName?release.species.find((s)=>s.common_name===partnerName):null;
  return c.json({answer:{code:q.correct,name:correct.common_name,scientific_name:correct.scientific_name},credit:credit(asset),coverage:{photos:own.filter((a)=>a.kind==="photo").length,audio:own.filter((a)=>a.kind==="audio").length,photo_target_met:own.filter((a)=>a.kind==="photo").length>=5,audio_target_met:own.filter((a)=>a.kind==="audio").length>=3},comparison_pair:partner&&partnerName?{code:partner.ebird_species_code,name:partnerName,photos:release.assets.filter((a)=>a.kind==="photo"&&a.species_code===partner.ebird_species_code).length,audio:release.assets.filter((a)=>a.kind==="audio"&&a.species_code===partner.ebird_species_code).length}:null});
});
app.post("/api/offline/sync", async (c) => {
  assertSameOrigin(c, c.env);
  const profile = c.get("profile");
  const body = await c.req.json().catch(() => null) as Row | null;
  const input = Array.isArray(body?.attempts) ? body!.attempts : null;
  if (!input || input.length > 100) throw new HTTPException(400, { message: "Send between 1 and 100 offline attempts." });
  const release = await activeRelease(c.env);
  const visible = publicAssets(release, await hidden(c.env.DB));
  const assets = new Map(visible.map((asset) => [asset.id, asset]));
  const accepted: string[] = [];
  const duplicates: string[] = [];
  const rejected: Array<{ event_id: string; code: string }> = [];
  const eventPattern = /^offline:[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/;
  for (const raw of input) {
    const item = raw && typeof raw === "object" ? raw as Row : {};
    const eventId = typeof item.event_id === "string" ? item.event_id.toLowerCase() : "";
    if (!eventPattern.test(eventId)) {
      rejected.push({ event_id: String(item.event_id ?? "").slice(0, 80), code: "invalid_event_id" });
      continue;
    }
    const asset = assets.get(String(item.asset_id ?? ""));
    const mode = item.mode === "recall" ? "recall" : item.mode === "choice" ? "choice" : "";
    const choice = String(item.choice ?? "");
    const at = Date.parse(String(item.at ?? ""));
    if (!asset || asset.kind !== item.kind) {
      rejected.push({ event_id: eventId, code: asset ? "kind_mismatch" : "media_withdrawn" });
      continue;
    }
    if (!mode || !Number.isFinite(at) || at > Date.now() + 300_000 || at < Date.now() - 400 * 86_400_000) {
      rejected.push({ event_id: eventId, code: "invalid_attempt" });
      continue;
    }
    if (!["unknown", "insufficient", "known", "incorrect"].includes(choice) && !release.species.some((s) => s.ebird_species_code === choice)) {
      rejected.push({ event_id: eventId, code: "invalid_choice" });
      continue;
    }
    const outcome = choice === "unknown" || choice === "insufficient" ? "uncertain"
      : mode === "recall" ? (choice === "known" ? "correct" : "incorrect")
      : choice === asset.species_code ? "correct" : "incorrect";
    const prior = await c.env.DB.prepare("SELECT profile_id FROM attempts WHERE id=? OR question_id=?").bind(eventId, eventId).first<{ profile_id: string }>();
    if (prior) {
      if (prior.profile_id !== profile) rejected.push({ event_id: eventId, code: "profile_mismatch" });
      else duplicates.push(eventId);
      continue;
    }
    const result = await c.env.DB.prepare("INSERT OR IGNORE INTO attempts(id,session_id,question_id,profile_id,asset_id,species_code,kind,mode,choice,outcome,at) VALUES(?,?,?,?,?,?,?,?,?,?,?)")
      .bind(eventId, `offline:${eventId.slice(8)}`, eventId, profile, asset.id, asset.species_code, asset.kind, mode, choice, outcome, new Date(at).toISOString()).run();
    if (Number(result.meta?.changes ?? 0) > 0) accepted.push(eventId); else duplicates.push(eventId);
  }
  return c.json({ ok: true, profile_id: profile, release_id: release.id, accepted, duplicates, rejected });
});
app.post("/api/flag", async (c) => {
  const profile=c.get("profile"); const body=await c.req.json(); const release=await activeRelease(c.env); const {asset_id,session_id,reason,suggested_species}=body;
  if(!release.assets.some((a)=>a.id===asset_id)||typeof reason!=="string"||!reason.trim()||reason.length>2000)throw new HTTPException(400,{message:"Choose an example and reason."});
  if(suggested_species&&!release.species.some((s)=>s.ebird_species_code===suggested_species))throw new HTTPException(400,{message:"Unknown suggested species."});
  if(session_id){const s=await c.env.DB.prepare("SELECT profile_id,questions FROM sessions WHERE id=?").bind(session_id).first() as any; if(!s||s.profile_id!==profile||!JSON.parse(s.questions).some((q:Row)=>q.asset_id===asset_id))throw new HTTPException(400,{message:"Flag context mismatch."});}
  const id=crypto.randomUUID(); await c.env.DB.prepare("INSERT INTO flags(id,profile_id,asset_id,release_id,session_id,reason,suggested_species,at) VALUES(?,?,?,?,?,?,?,?)").bind(id,profile,asset_id,release.id,session_id??null,reason.trim(),suggested_species||null,new Date().toISOString()).run();
  return c.json({id,status:"Hidden from practice for both learners, pending review. Related attempts excluded from progress. Sync to the curation workbench with `uv run python -m tooling.flag_sync --apply`."});
});
app.use("/api/admin/*", async (c, next) => {
  const ip=c.req.header("CF-Connecting-IP")??"local";
  if(c.env.PUBLISH_LIMIT&&!(await c.env.PUBLISH_LIMIT.limit({key:"publish:"+ip})).success) throw new HTTPException(429,{message:"Publish rate limit reached."});
  const supplied=c.req.header("X-Publish-Token")??"";
  if(!c.env.PUBLISH_TOKEN)throw new HTTPException(503,{message:"Publishing is not configured."});
  if(!safeEqual(await digest(supplied),await digest(c.env.PUBLISH_TOKEN)))throw new HTTPException(401,{message:"Publisher authentication failed."});
  await next();
});
app.put("/api/admin/object", async (c) => {
  const key=c.req.query("key")??"";
  if(!/^(media|releases)\/[A-Za-z0-9._/-]+$/.test(key)||key.includes(".."))throw new HTTPException(400,{message:"Invalid object key."});
  const declared=Number(c.req.header("Content-Length")??"0"); if(!Number.isFinite(declared)||declared<=0||declared>12_000_000)throw new HTTPException(413,{message:"Object size is outside the publish limit."});
  const expected=(c.req.header("X-Content-SHA256")??"").toLowerCase(); if(!/^[a-f0-9]{64}$/.test(expected))throw new HTTPException(400,{message:"A SHA-256 header is required."});
  const raw=await c.req.arrayBuffer(); if(raw.byteLength!==declared)throw new HTTPException(422,{message:"Object length did not match Content-Length."});
  const actual=hex(await crypto.subtle.digest("SHA-256",raw)); if(actual!==expected)throw new HTTPException(422,{message:"Object checksum did not match."});
  const existing=await c.env.CONTENT.head(key);
  if(existing&&existing.size===declared&&existing.customMetadata?.sha256===actual)return c.json({ok:true,skipped:true,key,bytes:declared,sha256:actual});
  const contentType=c.req.header("Content-Type")??"application/octet-stream";
  await c.env.CONTENT.put(key,raw,{httpMetadata:{contentType},customMetadata:{sha256:actual}});
  return c.json({ok:true,skipped:false,key,bytes:declared,sha256:actual});
});
app.get("/api/admin/object", async (c) => {
  const key=c.req.query("key")??""; if(!/^(media|releases)\/[A-Za-z0-9._/-]+$/.test(key)||key.includes(".."))throw new HTTPException(400,{message:"Invalid object key."});
  const head=await c.env.CONTENT.head(key); if(!head)return c.json({exists:false,key});
  return c.json({exists:true,key,bytes:head.size,sha256:head.customMetadata?.sha256??null,uploaded:head.uploaded??null});
});
app.post("/api/admin/release", async (c) => {
  const body=await c.req.json(); const id=String(body.id??""), objectKey=String(body.object_key??""), compatibility=String(body.compatibility_key??"");
  if(!/^[a-f0-9]{64}$/.test(id)||!/^releases\/[a-f0-9]{64}\/catalog\.json$/.test(objectKey))throw new HTTPException(400,{message:"Invalid release identity."});
  const object=await c.env.CONTENT.head(objectKey); if(!object)throw new HTTPException(422,{message:"Release catalog is not in R2."});
  await c.env.DB.prepare("INSERT INTO releases(id,object_key,compatibility_key,created_at,active) VALUES(?,?,?,?,0) ON CONFLICT(id) DO UPDATE SET object_key=excluded.object_key,compatibility_key=excluded.compatibility_key").bind(id,objectKey,compatibility,new Date().toISOString()).run();
  if(body.activate){await c.env.DB.batch([c.env.DB.prepare("UPDATE releases SET active=0 WHERE active=1"),c.env.DB.prepare("UPDATE releases SET active=1 WHERE id=?").bind(id)]);releaseCache=null;}
  return c.json({ok:true,id,active:!!body.activate});
});
app.post("/api/admin/rollback", async (c) => {
  const id=String((await c.req.json()).id??""); if(!/^[a-f0-9]{64}$/.test(id))throw new HTTPException(400,{message:"Invalid release identity."});
  const row=await c.env.DB.prepare("SELECT id FROM releases WHERE id=?").bind(id).first(); if(!row)throw new HTTPException(404,{message:"Release not found."});
  await c.env.DB.batch([c.env.DB.prepare("UPDATE releases SET active=0 WHERE active=1"),c.env.DB.prepare("UPDATE releases SET active=1 WHERE id=?").bind(id)]); releaseCache=null;
  return c.json({ok:true,id,active:true});
});
app.get("/api/admin/releases", async (c) => c.json({releases:(await dbRows(c.env.DB,"SELECT id,object_key,compatibility_key,created_at,active FROM releases ORDER BY created_at DESC"))}));
app.on(["GET","HEAD"], "/media/public/:id", async (c) => {
  const release=await activeRelease(c.env); const suppressed=await hidden(c.env.DB); const asset=release.assets.find((a)=>a.id===c.req.param("id"));
  if(!asset||!isPublicAsset(asset)||suppressed.has(asset.id))return c.notFound(); const key=asset.r2_key??`media/${asset.id}`; const size=Number(asset.bytes??0);
  let range:Row|undefined; const rangeHeader=c.req.header("Range");
  if(rangeHeader){const m=/^bytes=(\d+)-(\d*)$/.exec(rangeHeader); if(!m)return new Response(null,{status:416,headers:{"Content-Range":`bytes */${size}`,"Accept-Ranges":"bytes"}}); const start=Number(m[1]); const end=m[2]?Math.min(Number(m[2]),size-1):size-1; if(start>end||start>=size)return new Response(null,{status:416,headers:{"Content-Range":`bytes */${size}`,"Accept-Ranges":"bytes"}}); range={offset:start,length:end-start+1};}
  const object=await c.env.CONTENT.get(key,range?{range}:undefined); if(!object)return c.notFound();
  const headers:Record<string,string>={"Content-Type":asset.content_type??asset.media_format??"application/octet-stream","Content-Length":String(range?.length??object.size??size),"Accept-Ranges":"bytes","Cache-Control":"public, max-age=86400, stale-while-revalidate=604800","ETag":`"${asset.sha256}"`, "X-Content-SHA256":asset.sha256};
  if(range)headers["Content-Range"]=`bytes ${range.offset}-${range.offset+range.length-1}/${size}`;
  return new Response(c.req.method==="HEAD"?null:object.body,{status:range?206:200,headers});
});
app.on(["GET","HEAD"], "/media/:id", async (c) => {
  await currentProfile(c); const release=await activeRelease(c.env); const suppressed=await hidden(c.env.DB); const asset=release.assets.find((a)=>a.id===c.req.param("id"));
  if(!asset||suppressed.has(asset.id))return c.notFound(); const key=asset.r2_key??`media/${asset.id}`; const size=Number(asset.bytes??0);
  let range:Row|undefined; const rangeHeader=c.req.header("Range");
  if(rangeHeader){const m=/^bytes=(\d+)-(\d*)$/.exec(rangeHeader); if(!m)return new Response(null,{status:416,headers:{"Content-Range":`bytes */${size}`,"Accept-Ranges":"bytes"}}); const start=Number(m[1]); const end=m[2]?Math.min(Number(m[2]),size-1):size-1; if(start>end||start>=size)return new Response(null,{status:416,headers:{"Content-Range":`bytes */${size}`,"Accept-Ranges":"bytes"}}); range={offset:start,length:end-start+1};}
  const object=await c.env.CONTENT.get(key,range?{range}:undefined); if(!object)return c.notFound();
  const headers:Record<string,string>={"Content-Type":asset.content_type??asset.media_format??"application/octet-stream","Content-Length":String(range?.length??object.size??size),"Accept-Ranges":"bytes","Cache-Control":"private, no-store","Vary":"Cookie","ETag":`"${asset.sha256}"`, "X-Content-SHA256":asset.sha256};
  if(range)headers["Content-Range"]=`bytes ${range.offset}-${range.offset+range.length-1}/${size}`;
  return new Response(c.req.method==="HEAD"?null:object.body,{status:range?206:200,headers});
});
app.get("/compare", (c) => c.redirect("/?tab=compare", 302));
app.get("/birds/:code", async (c) => {
  const release=await activeRelease(c.env); const code=c.req.param("code"); const visible=publicAssets(release,await hidden(c.env.DB)); const location=c.req.query("location")??Object.keys(release.counties)[0]??"";
  const detail=publicSeasonality(release,location,code); const priority=publicRanked(release,location,new Date().toISOString().slice(0,10),visible).find((r)=>r.species_code===code);
  const bins=Array.isArray(detail.bins)?detail.bins:[]; const assets=visible.filter((a)=>a.species_code===code).map(publicAssetCard);
  const html=renderSpeciesPage(c.env.APP_ORIGIN,{code,name:String(detail.name),scientific_name:String(detail.scientific_name),confusion_pair:(release.species.find((s)=>s.ebird_species_code===code) as Row|undefined)?.confusion_pair??null,public_photos:assets.filter((a)=>a.kind==="photo").length,public_recordings:assets.filter((a)=>a.kind==="audio").length,
    priority:{current_reporting_frequency:priority?.current_reporting_frequency??null,approaching_window_rise:priority?.approaching_window_rise??null,sample_size:priority?.sample_size??null,bin_start:priority?.bin_start??null,bin_end:priority?.bin_end??null},assets,bins: bins.map((b:Row)=>({start:b.start,end:b.end,frequency:b.frequency,sample_size:b.sample_size})),});
  c.header("Cache-Control","public, max-age=600, stale-while-revalidate=3600"); return c.html(html);
});
app.get("/regions/:county", async (c) => {
  const release=await activeRelease(c.env); const code=c.req.param("county"); const name=release.counties[code]; if(!name) throw new HTTPException(404,{message:"Region not found."});
  const visible=publicAssets(release,await hidden(c.env.DB)); const ranked=publicRanked(release,code,new Date().toISOString().slice(0,10),visible).filter((r)=>r.photo_ready||r.audio_ready).slice(0,30);
  const vintage=release.data_vintage?`${release.data_vintage.start_year}–${release.data_vintage.end_year} historical eBird reporting profiles`:"Historical eBird reporting profiles";
  const html=renderRegionPage(c.env.APP_ORIGIN,code,name,ranked.map((r)=>({code:r.species_code,name:r.name,frequency:r.current_reporting_frequency,rise:r.approaching_window_rise,photos:r.photos,audio:r.recordings})),vintage);
  c.header("Cache-Control","public, max-age=600, stale-while-revalidate=3600"); return c.html(html);
});
app.get("/sources", (c) => { c.header("Cache-Control","public, max-age=3600"); return c.html(renderSourcesPage(c.env.APP_ORIGIN)); });
app.get("/privacy", (c) => { c.header("Cache-Control","public, max-age=3600"); return c.html(renderPrivacyPage(c.env.APP_ORIGIN)); });
app.get("/about", (c) => c.redirect("/sources", 308));
app.get("/robots.txt", async (c) => { c.header("Content-Type","text/plain; charset=utf-8"); c.header("Cache-Control","public, max-age=3600"); return c.body(renderRobots(c.env.APP_ORIGIN)); });
app.get("/sitemap.xml", async (c) => { const release=await activeRelease(c.env); c.header("Content-Type","application/xml; charset=utf-8"); c.header("Cache-Control","public, max-age=3600");
  return c.body(renderSitemap(c.env.APP_ORIGIN,release.species.map((s)=>({code:s.ebird_species_code})),release.counties,new Date().toISOString().slice(0,10))); });
app.all("/api/*", (c) => c.json({error:"Not found"},404));
app.all("/media/*", (c) => c.json({error:"Not found"},404));
app.all("*", async (c) => { const response=await c.env.ASSETS.fetch(c.req.raw); if(c.req.path==="/sw.js"){const h=new Headers(response.headers);h.set("Cache-Control","no-store");return new Response(response.body,{status:response.status,headers:h});} if(c.req.path==="/"){const h=new Headers(response.headers);h.set("Cache-Control","public, max-age=300, stale-while-revalidate=3600");return new Response(response.body,{status:response.status,headers:h});} return response; });
export default app;

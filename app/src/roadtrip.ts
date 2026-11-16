import type {
  NarrationManifest, OfflineAsset, OfflineCatalog, OfflinePackDefinition, OfflineSpecies,
  RoadTripConfig, RoadTripExercise, RoadTripPlan, RoadTripSegment,
} from "./offline";

const INSTRUCTION = (key: string) => `instructions/${key}.wav`;
const NAME = (code: string) => `names/${code}.wav`;
const SILENCE = (seconds: number) => `silence/${seconds}.wav`;

function narrationAsset(manifest: NarrationManifest, path: string): OfflineAsset | null {
  const file = manifest.files[path];
  if (!file) return null;
  return {
    id: `narration:${path}`, kind: "audio", species_code: "__narration",
    media_url: `/narration/${path}`, bytes: file.bytes, sha256: file.sha256,
    content_type: file.content_type, duration_seconds: file.duration_seconds ?? null,
    creator: "BirdAhead local narration (Kokoro-82M, Apache-2.0)", attribution: null, source_url: "https://huggingface.co/hexgrad/Kokoro-82M", license_url: "https://www.apache.org/licenses/LICENSE-2.0",
    public_license_notice: "Locally generated with Kokoro-82M (Apache-2.0); not bird media.",
  };
}
function audioAssets(species: OfflineSpecies): OfflineAsset[] {
  return (species.assets ?? []).filter((asset) => asset.kind === "audio" && asset.media_url.startsWith("/media/public/") && asset.sha256 && Number(asset.bytes) > 0);
}
function estimate(asset: OfflineAsset | null): number { return Math.max(1, Number(asset?.duration_seconds) || 20); }
function exerciseSeconds(exercise: RoadTripExercise, config: RoadTripConfig): number {
  const first = estimate(exercise.recordings[0] ?? null);
  const second = exercise.recordings[1] ? estimate(exercise.recordings[1]) + 1 : 0;
  return first + second + 4 + (config.mode === "quiz" ? config.interval_seconds : 0);
}
function speciesCandidates(catalog: OfflineCatalog, config: RoadTripConfig, weakCodes: string[]): OfflineSpecies[] {
  const withAudio = catalog.species.filter((row) => audioAssets(row).length > 0);
  const weak = new Set(weakCodes);
  const ranked = [...withAudio].sort((a, b) => {
    if (config.focus === "weak") {
      const aw = weak.has(a.code) ? 1 : 0; const bw = weak.has(b.code) ? 1 : 0;
      if (aw !== bw) return bw - aw;
    }
    const aScore = (a.current_reporting_frequency ?? 0) + (a.approaching_window_rise ?? 0) * 0.6;
    const bScore = (b.current_reporting_frequency ?? 0) + (b.approaching_window_rise ?? 0) * 0.6;
    return bScore - aScore || (a.priority_rank ?? 9999) - (b.priority_rank ?? 9999) || a.code.localeCompare(b.code);
  });
  if (config.focus === "here") return ranked.filter((row) => (row.current_reporting_frequency ?? 0) > 0);
  if (config.focus === "arriving") return ranked.filter((row) => (row.approaching_window_rise ?? 0) > 0);
  if (config.focus === "weak" && weak.size) return ranked.filter((row) => weak.has(row.code)).concat(ranked.filter((row) => !weak.has(row.code)));
  return ranked;
}
function shuffled<T>(rows: T[], random: () => number): T[] {
  const out = [...rows];
  for (let i = out.length - 1; i > 0; i -= 1) {
    const j = Math.floor(random() * (i + 1));
    [out[i], out[j]] = [out[j]!, out[i]!];
  }
  return out;
}
function exerciseRows(catalog: OfflineCatalog, config: RoadTripConfig, manifest: NarrationManifest, weakCodes: string[], random: () => number): RoadTripExercise[] {
  const exercises: RoadTripExercise[] = [];
  for (const species of speciesCandidates(catalog, config, weakCodes)) {
    const assets = audioAssets(species);
    const nameAsset = narrationAsset(manifest, NAME(species.code));
    if (!nameAsset) continue;
    for (let index = 0; index < assets.length; index += 1) {
      const first = assets[index]!;
      const second = assets.length > 1 ? assets[(index + 1) % assets.length]! : null;
      exercises.push({
        id: `${species.code}:${first.id}:${index}`, species_code: species.code, name: species.name,
        recordings: second && second.id !== first.id ? [first, second] : [first],
        name_url: nameAsset.media_url, name_text: species.name,
      });
    }
  }
  return config.order === "shuffled" ? shuffled(exercises, random) : exercises;
}

function instruction(manifest: NarrationManifest, key: string): OfflineAsset | null {
  return narrationAsset(manifest, INSTRUCTION(key));
}
function segmentFor(asset: OfflineAsset, exercise: number, kind: RoadTripSegment["kind"], text?: string): RoadTripSegment {
  return { kind, url: asset.media_url, asset_id: asset.id, exercise, text, duration_seconds: asset.duration_seconds ?? null };
}

/** Build a compact, duration-specific road-trip plan from one public catalog
 * snapshot and the reviewed narration manifest. Only accepted public audio is
 * used for bird playback; narration has its own generated license notice. */
export function planRoadTrip(
  catalog: OfflineCatalog, manifest: NarrationManifest, config: RoadTripConfig,
  weakCodes: string[] = [], random: () => number = Math.random,
): OfflinePackDefinition {
  const candidates = exerciseRows(catalog, config, manifest, weakCodes, random);
  const target = Math.max(30, config.minutes * 60); const chosen: RoadTripExercise[] = [];
  let estimated = 8;
  for (const exercise of candidates) {
    if (chosen.length > 0 && estimated >= target) break;
    chosen.push(exercise); estimated += exerciseSeconds(exercise, config);
    if (chosen.length >= 240) break;
  }
  if (!chosen.length) throw new Error("No public audio recordings are available for this road-trip configuration.");
  const intro = instruction(manifest, "intro"); const answer = instruction(manifest, "answer");
  const next = instruction(manifest, "next"); const another = instruction(manifest, "another");
  const listen = instruction(manifest, "listen"); const complete = instruction(manifest, "complete");
  const silence = narrationAsset(manifest, SILENCE(config.interval_seconds));
  const segments: RoadTripSegment[] = [];
  if (intro) segments.push(segmentFor(intro, 0, "narration", "Road Trip. Listen to each bird recording. Guess the species during the pause. The answer follows."));
  if (config.mode === "listen" && listen) segments.push(segmentFor(listen, 0, "narration", "Listen and learn. The species is announced before its recordings."));
  chosen.forEach((exercise, exerciseIndex) => {
    const name = narrationAsset(manifest, `names/${exercise.species_code}.wav`);
    if (config.mode === "listen") {
      if (next) segments.push(segmentFor(next, exerciseIndex, "narration", "The next bird is"));
      if (name) segments.push(segmentFor(name, exerciseIndex, "narration", exercise.name));
      segments.push(segmentFor(exercise.recordings[0]!, exerciseIndex, "recording"));
    } else {
      segments.push(segmentFor(exercise.recordings[0]!, exerciseIndex, "recording"));
      if (silence) segments.push(segmentFor(silence, exerciseIndex, "silence"));
      if (answer) segments.push(segmentFor(answer, exerciseIndex, "narration", "The answer is"));
      if (name) segments.push(segmentFor(name, exerciseIndex, "narration", exercise.name));
    }
    if (exercise.recordings[1]) {
      if (another) segments.push(segmentFor(another, exerciseIndex, "narration", "Here is another recording."));
      segments.push(segmentFor(exercise.recordings[1], exerciseIndex, "recording"));
    }
  });
  if (complete) segments.push(segmentFor(complete, chosen.length, "narration", "Session complete. Pull over safely before using the screen."));
  const byId = new Map<string, OfflineAsset>();
  for (const segment of segments) {
    const asset = chosen.flatMap((exercise) => exercise.recordings).find((row) => row.id === segment.asset_id)
      ?? (segment.url.startsWith("/narration/") ? narrationAsset(manifest, segment.url.slice("/narration/".length)) : null);
    if (asset) byId.set(asset.id, asset);
  }
  const assets = [...byId.values()];
  const roadTrip: RoadTripPlan = { config, exercises: chosen, segments, narration_version: manifest.narration_version };
  return {
    id: `roadtrip:${config.minutes}:${config.focus}:${config.interval_seconds}:${config.order}:${config.mode}:${config.county}:${config.day}:${manifest.narration_version}`,
    title: `Road trip · ${config.minutes} min`,
    description: `${config.focus} · ${config.mode === "quiz" ? "guess and reveal" : "listen and learn"} · ${config.interval_seconds}s interval · ${config.order}`,
    release_id: catalog.release_id, county: catalog.county, day: catalog.day,
    created_at: new Date().toISOString(), assetIds: assets.map((asset) => asset.id), assets,
    species: chosen.map((exercise) => ({ code: exercise.species_code, name: exercise.name })),
    bytes: assets.reduce((sum, asset) => sum + Number(asset.bytes || 0), 0), roadTrip,
  };
}

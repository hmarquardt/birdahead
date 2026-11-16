export interface ComparisonSource { publisher: string; title: string; url: string; }
export interface ComparisonTrait { dimension: string; left: string; right: string; source_ids: string[]; }
export interface ComparisonPair {
  id: string; priority: number;
  left: { code: string; name: string }; right: { code: string; name: string };
  traits: ComparisonTrait[]; gaps: string[];
}
export interface ComparisonCatalog {
  schema: string; version: string; review_status: string; review_note: string;
  sources: Record<string, ComparisonSource>; pairs: ComparisonPair[];
}
export interface ComparisonAsset {
  id: string; kind: "photo" | "audio"; species_code: string; media_url: string;
  bytes?: number; sha256?: string; creator?: string | null; attribution?: string | null;
  source_url?: string | null; license_url?: string | null; license_code?: string | null;
  public_license_notice?: string | null; vocalization?: string | null; age?: string | null;
  sex?: string | null; plumage?: string | null; biological_attribute_status?: string | null;
}
export interface SeasonalOverlap {
  common_bins: number; total_bins: number; left_max: number | null; right_max: number | null;
}
export interface ComparativeQuestion {
  id: string; pair_id: string; side: "left" | "right"; species_code: string;
  asset: ComparisonAsset; choices: Array<{ code: string; name: string }>;
}

export function recommendedPairs(catalog: ComparisonCatalog, progress: Record<string, any> | null, attempts: Array<{ species_code: string; outcome?: string }> = []): ComparisonPair[] {
  const scores = new Map<string, number>();
  const add = (code: string) => {
    for (const pair of catalog.pairs) if (pair.left.code === code || pair.right.code === code) scores.set(pair.id, (scores.get(pair.id) ?? 0) + 1);
  };
  for (const row of progress?.confusion ?? []) { add(String(row.from_code ?? "")); add(String(row.to_code ?? "")); }
  for (const row of attempts) if (row.outcome !== "correct") add(row.species_code);
  return [...catalog.pairs].sort((a, b) => (scores.get(b.id) ?? 0) - (scores.get(a.id) ?? 0) || a.priority - b.priority);
}

export function seasonalOverlap(left: Array<{ start: string; end: string; frequency: number | null }>, right: Array<{ start: string; end: string; frequency: number | null }>): SeasonalOverlap {
  const rightByKey = new Map(right.map((row) => [`${row.start}|${row.end}`, row.frequency]));
  let common = 0; let total = 0;
  let leftMax: number | null = null; let rightMax: number | null = null;
  for (const row of left) {
    const other = rightByKey.get(`${row.start}|${row.end}`);
    if (other === undefined) continue;
    total += 1;
    const l = row.frequency; if (l !== null && (leftMax === null || l > leftMax)) leftMax = l;
    if (other !== null && (rightMax === null || other > rightMax)) rightMax = other;
    if ((l ?? 0) > 0 && (other ?? 0) > 0) common += 1;
  }
  return { common_bins: common, total_bins: total, left_max: leftMax, right_max: rightMax };
}

export function comparativeQuestion(
  pair: ComparisonPair,
  leftAssets: ComparisonAsset[], rightAssets: ComparisonAsset[], kind: "photo" | "audio",
  history: Array<{ asset_id: string }> = [], random: () => number = Math.random,
): ComparativeQuestion | null {
  const seen = new Set(history.map((row) => row.asset_id));
  const pool = [...leftAssets, ...rightAssets].filter((asset) => asset.kind === kind && asset.media_url?.startsWith("/media/public/"));
  if (!pool.length) return null;
  const fresh = pool.filter((asset) => !seen.has(asset.id));
  if (!fresh.length) return null;
  const asset = fresh[Math.floor(random() * fresh.length)]!;
  const side = asset.species_code === pair.left.code ? "left" : "right";
  return {
    id: `comparative:${pair.id}:${asset.id}:${Date.now()}`,
    pair_id: pair.id, side, species_code: asset.species_code, asset,
    choices: [{ code: pair.left.code, name: pair.left.name }, { code: pair.right.code, name: pair.right.name }],
  };
}

export function assetGaps(pair: ComparisonPair, leftAssets: ComparisonAsset[], rightAssets: ComparisonAsset[]): string[] {
  const gaps: string[] = [];
  for (const side of ["left", "right"] as const) {
    const code = pair[side].code; const assets = side === "left" ? leftAssets : rightAssets;
    if (!assets.some((asset) => asset.kind === "photo")) gaps.push(`${pair[side].name}: no accepted public photograph`);
    if (!assets.some((asset) => asset.kind === "audio")) gaps.push(`${pair[side].name}: no accepted public recording`);
  }
  return gaps;
}

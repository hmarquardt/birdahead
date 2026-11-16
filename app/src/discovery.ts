export const DISCOVERY_BINS = 48;
export const YEAR_ROUND_SHARE = 0.80;
export const STRONG_SEASONAL_SHARE = 0.50;
export const MIN_OBSERVED = 8;

export interface DiscoveryBin { index: number; start: string; end: string; month: number; period: number; }
export interface DiscoveryMetrics {
  observed_bins: number; active_bins: number; missing_bins: number;
  annual_mean: number | null; max_frequency: number | null; min_active_frequency: number | null;
  peak_bins: Array<{ index: number; start: string; end: string; frequency: number }>;
  largest_rise: { from_index: number; to_index: number; delta: number } | null;
  largest_fall: { from_index: number; to_index: number; delta: number } | null;
  classification: "insufficient" | "year_round" | "strongly_seasonal" | "seasonal";
}
export interface DiscoverySpecies {
  code: string; name: string; scientific_name: string; taxon_id: string | null; teaching: boolean;
  media: { photos: number; audio: number; field_guide: boolean; photo_practice_ready: boolean; audio_practice_ready: boolean };
  practice_ready: boolean; confusion_pair: { common_name: string; ebird_species_code: string } | null;
  counties: Record<string, Array<number | null>>;
  regional: { frequency: Array<number | null>; support: Array<number | null>; counties_used: number[] };
}
export interface DiscoveryCatalog {
  schema: string; version: string; data_vintage: Record<string, any>;
  counties: Record<string, { name: string; sample_sizes: number[]; checklist_total: number }>;
  bins: DiscoveryBin[]; richness: { by_county: Record<string, number[]>; regional: number[] };
  species: DiscoverySpecies[];
  regional_method: { method: string; formula: string; support_meaning: string; missing_policy: string; calendar: string };
  classification_thresholds: Record<string, number>;
  limitations: string[]; candidate_counts?: Record<string, number>;
}

function mean(values: number[]): number | null {
  return values.length ? values.reduce((sum, value) => sum + value, 0) / values.length : null;
}
export function discoveryMetrics(values: Array<number | null>): DiscoveryMetrics {
  const observed = values.map((value, index) => value === null ? -1 : index).filter((index) => index >= 0);
  const active = observed.filter((index) => (values[index] ?? 0) > 0);
  const known = observed.map((index) => values[index] as number);
  const activeValues = active.map((index) => values[index] as number);
  const peakBins = [...active].sort((a, b) => (values[b] as number) - (values[a] as number) || a - b).slice(0, 3)
    .map((index) => ({ index, start: "", end: "", frequency: values[index] as number }));
  const rises: Array<{ from_index: number; to_index: number; delta: number }> = [];
  const falls: Array<{ from_index: number; to_index: number; delta: number }> = [];
  for (let index = 1; index < values.length; index += 1) {
    const before = values[index - 1]; const after = values[index];
    if (before === null || after === null) continue;
    const delta = after - before;
    if (delta > 0) rises.push({ from_index: index - 1, to_index: index, delta });
    else if (delta < 0) falls.push({ from_index: index - 1, to_index: index, delta });
  }
  const maximum = known.length ? Math.max(...known) : null;
  const minimumActive = activeValues.length ? Math.min(...activeValues) : null;
  const share = active.length / DISCOVERY_BINS;
  const classification = observed.length < MIN_OBSERVED || active.length < 2 ? "insufficient"
    : share >= YEAR_ROUND_SHARE && (minimumActive ?? 0) >= 0.05 ? "year_round"
      : share <= STRONG_SEASONAL_SHARE || (maximum !== null && minimumActive !== null && maximum / minimumActive >= 4) ? "strongly_seasonal"
        : "seasonal";
  return {
    observed_bins: observed.length, active_bins: active.length, missing_bins: DISCOVERY_BINS - observed.length,
    annual_mean: mean(known), max_frequency: maximum, min_active_frequency: minimumActive,
    peak_bins: peakBins, largest_rise: rises.sort((a, b) => b.delta - a.delta)[0] ?? null,
    largest_fall: falls.sort((a, b) => a.delta - b.delta)[0] ?? null, classification,
  };
}

export function seriesFor(row: DiscoverySpecies, county: string): Array<number | null> {
  return county === "regional" ? row.regional.frequency : row.counties[county] ?? Array(DISCOVERY_BINS).fill(null);
}

export function binAtDate(bins: DiscoveryBin[], date: string): number {
  if (!date || !/^\d{4}-\d{2}-\d{2}$/.test(date)) return 0;
  const [, month, day] = date.split("-").map(Number);
  const template = `2001-${String(month).padStart(2, "0")}-${String(day).padStart(2, "0")}`;
  return Math.max(0, bins.findIndex((bin) => bin.start <= template && template < bin.end));
}

export function reportingChange(values: Array<number | null>, index: number): number | null {
  if (index <= 0) return null;
  const before = values[index - 1]; const after = values[index];
  return before === null || after === null ? null : after - before;
}
export function filterDiscovery(
  species: DiscoverySpecies[], county: string, index: number, query: string, pattern: string,
  mediaOnly: boolean, sort: string,
): DiscoverySpecies[] {
  const needle = query.trim().toLowerCase();
  const filtered = species.filter((row) => (!needle || `${row.name} ${row.scientific_name} ${row.code}`.toLowerCase().includes(needle))
    && (!mediaOnly || row.media.photos + row.media.audio > 0)
    && (pattern === "all" || discoveryMetrics(seriesFor(row, county)).classification === pattern));
  return filtered.sort((a, b) => {
    if (sort === "name") return a.name.localeCompare(b.name);
    if (sort === "peak") return (discoveryMetrics(seriesFor(b, county)).max_frequency ?? -1) - (discoveryMetrics(seriesFor(a, county)).max_frequency ?? -1);
    if (sort === "coverage") return Number(b.teaching) - Number(a.teaching) || a.name.localeCompare(b.name);
    const av = seriesFor(a, county)[index] ?? -1; const bv = seriesFor(b, county)[index] ?? -1;
    return bv - av || a.name.localeCompare(b.name);
  });
}

export function binLabel(bin: DiscoveryBin): string {
  const months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
  const endDate = new Date(`${bin.end}T00:00:00Z`); endDate.setUTCDate(endDate.getUTCDate() - 1);
  const end = `${months[endDate.getUTCMonth()]} ${endDate.getUTCDate()}`;
  return `${months[bin.month - 1]} ${Number(bin.start.slice(8, 10))}–${end}`;
}

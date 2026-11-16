/** Optional lazy geographic client; no national dataset is imported into the application bundle. */
export interface RegionEntry { id: string; parent?: string | null; url: string; sha256: string; bytes: number; }
export interface RegionalIndex { schema: string; version: string; regions: RegionEntry[]; }
export type ProfileCell = [number, number, number, number | null, string, number];
export interface GeographicProfile { schema: string; version: string; region: string; parent?: string | null; species: Record<string, ProfileCell[]>; }
const inFlight = new Map<string, Promise<GeographicProfile>>();
export async function loadGeographicProfile(index: RegionalIndex, id: string,
  fetcher: typeof fetch = fetch): Promise<GeographicProfile> {
  const entry = index.regions.find(r => r.id === id);
  const expected = `/api/public/geography/${index.version}/${id}`;
  if (!/^[a-f0-9]{64}$/.test(index.version) || !entry || entry.url !== expected || !/^[A-Za-z0-9][A-Za-z0-9_-]{0,95}$/.test(id)
    || !Number.isSafeInteger(entry.bytes) || entry.bytes <= 0 || entry.bytes > 2_000_000 || !/^[a-f0-9]{64}$/.test(entry.sha256)) throw new Error('Unsupported geographic region.');
  if (!inFlight.has(entry.url)) inFlight.set(entry.url, (async () => {
    // The browser HTTP cache holds immutable, anonymous responses by version and region.
    const response = await fetcher(entry.url, { credentials: 'omit', cache: 'force-cache' });
    if (!response.ok) throw new Error('Regional profile unavailable.');
    const raw = await response.arrayBuffer();
    const hash = [...new Uint8Array(await crypto.subtle.digest('SHA-256',raw))].map(b=>b.toString(16).padStart(2,'0')).join('');
    if (raw.byteLength !== entry.bytes || hash !== entry.sha256) throw new Error('Regional profile failed integrity verification.');
    const profile = JSON.parse(new TextDecoder().decode(raw)) as GeographicProfile;
    if (profile.schema !== 'birdahead-geographic-profile-v1' || profile.version !== index.version || profile.region !== id || profile.parent !== entry.parent) throw new Error('Invalid regional profile.');
    return profile;
  })().catch(error => { inFlight.delete(entry.url); throw error; }));
  return inFlight.get(entry.url)!;
}
export async function supportedGeographicCell(index: RegionalIndex, id: string, species: string, bin: number,
  loader: (id: string) => Promise<GeographicProfile> = id => loadGeographicProfile(index,id)) {
  const visited = new Set<string>(); let current: string | null | undefined = id;
  while (current) {
    if (visited.has(current)) throw new Error('Cyclic geographic fallback.');
    visited.add(current);
    const entry = index.regions.find(r => r.id === current);
    if (!entry) throw new Error('Unpublished geographic parent.');
    const profile = await loader(current);
    const cell = profile.species[species]?.find(c => c[0] === bin);
    if (cell?.[4] === 'supported' && cell[3] !== null) return { requested_region: id, effective_region: current,
      used_parent: current !== id, signal: 'historical_reporting_frequency', cell };
    current = entry.parent;
  }
  return { requested_region: id, effective_region: null, used_parent: false, signal: 'historical_reporting_frequency', cell: null };
}

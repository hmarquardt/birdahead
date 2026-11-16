/** Selective geographic delivery. Only the active catalog's eligible allowlist reaches R2. */
export interface GeographicRegion {
  id: string; name: string; kind: string; parent?: string | null; key: string; bytes: number; sha256: string;
}
export interface GeographicIndex {
  schema: 'birdahead-geographic-index-v1'; version: string; regions: GeographicRegion[];
  public_noncommercial_eligible: true; attribution: string; terms_url: string;
}
const hash = /^[a-f0-9]{64}$/;
const identifier = /^[A-Za-z0-9][A-Za-z0-9_-]{0,95}$/;
export function validateGeographicIndex(value: unknown): GeographicIndex {
  const x = value as GeographicIndex;
  if (x?.schema !== 'birdahead-geographic-index-v1' || x.public_noncommercial_eligible !== true || !hash.test(x.version)
    || !x.attribution || !x.terms_url || !Array.isArray(x.regions) || !x.regions.length || x.regions.length > 5000) throw new Error('Geography unavailable.');
  const ids = new Set<string>();
  for (const r of x.regions) {
    if (!identifier.test(r.id) || ids.has(r.id) || !r.name || !r.kind || !hash.test(r.sha256)
      || !Number.isSafeInteger(r.bytes) || r.bytes <= 0 || r.bytes > 2_000_000
      || r.key !== `releases/geography/${x.version}/${r.id}.json`) throw new Error('Invalid geographic entry.');
    ids.add(r.id);
  }
  for (const r of x.regions) {
    const visited = new Set([r.id]); let parent = r.parent;
    while (parent) {
      if (!ids.has(parent) || visited.has(parent)) throw new Error('Invalid geographic fallback.');
      visited.add(parent); parent = x.regions.find(r => r.id === parent)?.parent;
    }
  }
  return x;
}
export function publicGeographicIndex(index: GeographicIndex) {
  return { schema: index.schema, version: index.version, attribution: index.attribution, terms_url: index.terms_url,
    regions: index.regions.map(r => ({ id:r.id, name:r.name, kind:r.kind, parent:r.parent,
      sha256:r.sha256, bytes:r.bytes, url: `/api/public/geography/${index.version}/${r.id}` })) };
}
export async function geographicResponse(value: unknown, version: string, id: string,
  read: (key: string) => Promise<ArrayBuffer | null>): Promise<Response> {
  let index: GeographicIndex;
  try { index = validateGeographicIndex(value); } catch { return Response.json({ error: 'Geography unavailable.' }, { status: 404 }); }
  const region = index.version === version ? index.regions.find(r => r.id === id) : undefined;
  if (!region) return Response.json({ error: 'Geographic profile unavailable.' }, { status: 404 });
  const raw = await read(region.key);
  if (!raw || raw.byteLength !== region.bytes) return Response.json({ error: 'Geographic profile unavailable.' }, { status: 503 });
  const actual = [...new Uint8Array(await crypto.subtle.digest('SHA-256', raw))].map(b => b.toString(16).padStart(2,'0')).join('');
  if (actual !== region.sha256) return Response.json({ error: 'Geographic integrity check failed.' }, { status: 503 });
  const allowed = new Set(['schema','version','region','parent','signal','calendar','years','minimum_support','columns','species',
    'source_snapshot','source_taxonomy_version','target_taxonomy_version','attribution','terms_url','limitations']);
  try {
    const product = JSON.parse(new TextDecoder().decode(raw));
    if (product.schema !== 'birdahead-geographic-profile-v1' || product.version !== version || product.region !== id
      || Object.keys(product).some(k => !allowed.has(k))) throw new Error();
  } catch { return Response.json({ error: 'Invalid geographic product.' }, { status: 503 }); }
  const etag = `"${actual}"`;
  return new Response(raw, { headers: { 'Content-Type': 'application/json; charset=utf-8',
    'Cache-Control': 'public, max-age=31536000, immutable', ETag: etag, 'X-Content-Type-Options': 'nosniff' } });
}

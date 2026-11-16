/** Crawlable public pages. Private learning data never reaches this module. */
export const ANALYTICS_SCRIPT = "https://analytics.aismallbizguru.com/script.js";
export const ANALYTICS_SITE = "as_Bq4kGnf2EkSW3dS0HZAddF";
export const EBIRD_TERMS = "https://www.birds.cornell.edu/home/ebird-data-access-terms-of-use/";
export const EBIRD_CITATION = "eBird. 2016–2025. eBird observation data; derived seasonal summaries. Cornell Lab of Ornithology, Ithaca, New York. https://ebird.org.";
export const FAVICON = 'data:image/svg+xml,%3Csvg%20xmlns=%22http://www.w3.org/2000/svg%22%20viewBox=%220%200%2064%2064%22%3E%3Ccircle%20cx=%2232%22%20cy=%2232%22%20r=%2232%22%20fill=%22%23183e34%22/%3E%3Cpath%20d=%22M11%2041c15%200%2015-19%2032-19l8-10%205%2010-8%208c3%2016-11%2024-27%2019l-10%205%205-10z%22%20fill=%22%23dce9b5%22/%3E%3Cpath%20d=%22M25%2036c5%201%2010-1%2014-5%22%20fill=%22none%22%20stroke=%22%23183e34%22%20stroke-width=%224%22%20stroke-linecap=%22round%22/%3E%3C/svg%3E';
export const PUBLIC_SCOPE = "Public noncommercial educational use. No advertising, monetization, paid access or commercial clearance.";

export function escapeHtml(value: unknown): string {
  return String(value ?? "").replace(/[&<>"']/g, (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[char] as string));
}
const pct = (value: number | null | undefined) => value === null || value === undefined ? "Unknown" : `${(value * 100).toFixed(1)}%`;
const jsonLd = (value: unknown) => JSON.stringify(value).replace(/</g, "\\u003c");

export interface PublicPageAsset {
  id: string; kind: "photo" | "audio"; media_url: string; creator: string; attribution?: string | null;
  source_url: string; license_url: string; license_code?: string | null; source?: string | null;
  public_license_notice?: string | null; vocalization?: string | null;
}
export interface PublicPageSpecies {
  code: string; name: string; scientific_name: string; public_photos?: number; public_recordings?: number;
  priority: { current_reporting_frequency: number | null; approaching_window_rise: number | null; sample_size: number | null; bin_start?: string | null; bin_end?: string | null };
  assets: PublicPageAsset[];
  confusion_pair?: { common_name: string; ebird_species_code: string } | null;
  bins: Array<{ start: string; end: string; frequency: number | null; sample_size: number | null }>;
}

function shell(origin: string, title: string, description: string, canonical: string, body: string, image?: string, structured?: unknown) {
  const imageUrl = origin + "/og-birdahead.png";
  return `<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>${escapeHtml(title)}</title><meta name="description" content="${escapeHtml(description)}">
<link rel="canonical" href="${escapeHtml(canonical)}"><meta name="robots" content="index,follow">
<meta property="og:type" content="website"><meta property="og:site_name" content="BirdAhead"><meta property="og:title" content="${escapeHtml(title)}">
<meta property="og:description" content="${escapeHtml(description)}"><meta property="og:url" content="${escapeHtml(canonical)}"><meta property="og:image" content="${escapeHtml(imageUrl)}">
<meta property="og:image:alt" content="BirdAhead regional bird learning"><meta property="og:image:width" content="1200"><meta property="og:image:height" content="630"><meta name="twitter:card" content="summary_large_image">
<meta name="theme-color" content="#183e34"><link rel="manifest" href="/manifest.webmanifest"><link rel="icon" href="${FAVICON}">
<link rel="stylesheet" href="/public-pages.css"><script defer src="${ANALYTICS_SCRIPT}" data-site="${ANALYTICS_SITE}"></script>
${structured ? `<script type="application/ld+json">${jsonLd(structured)}</script>` : ""}</head><body>
<header class="site-header"><a class="site-brand" href="/"><span class="birdmark">◆</span> BirdAhead</a><nav><a href="/?tab=explore">Explore</a><a href="/?tab=guide">Field guide</a><a href="/?tab=practice">Practice</a><a href="/?tab=compare">Compare</a><a href="/sources">Sources &amp; privacy</a></nav></header>
${body}
<footer class="site-footer"><p><strong>BirdAhead</strong> · Learn the birds you're about to meet. Public seasonal exploration and practice; household sign-in is optional.</p><p>${escapeHtml(PUBLIC_SCOPE)} <a href="/sources">Data and media credits</a> · <a href="/privacy">Privacy</a></p></footer></body></html>`;
}


export function renderSpeciesPage(origin: string, species: PublicPageSpecies) {
  const canonical = `${origin}/birds/${species.code}`;
  const description = `${species.name} (${species.scientific_name}) in southwestern Indiana: seasonal occurrence, public photographs, recordings and identification practice.`;
  const photo = species.assets.find((a) => a.kind === "photo");
  const audio = species.assets.find((a) => a.kind === "audio");
  const credits = species.assets.map((a) => `<li><a href="${escapeHtml(a.source_url)}" rel="noreferrer">${escapeHtml(a.creator)}</a>${a.vocalization ? ` · ${escapeHtml(a.vocalization)}` : ""} · <a href="${escapeHtml(a.license_url)}" rel="noreferrer">${escapeHtml(a.license_code ?? "license")}</a>${a.public_license_notice ? `<small>${escapeHtml(a.public_license_notice)}</small>` : ""}</li>`).join("");
  const bins = species.bins.map((b) => `<tr><td>${escapeHtml(b.start)} – ${escapeHtml(b.end)}</td><td><meter min="0" max="1" value="${Math.max(0, Math.min(1, b.frequency ?? 0))}"></meter></td><td>${pct(b.frequency)}</td><td>${b.sample_size ?? "—"}</td></tr>`).join("");
  const current = species.priority;
  const compare = species.confusion_pair;
  const compareLink = compare?.ebird_species_code ? `<a class="button secondary" href="/?tab=compare&a=${encodeURIComponent(species.code)}&b=${encodeURIComponent(compare.ebird_species_code)}">Compare with ${escapeHtml(compare.common_name)}</a>` : "";
  const body = `<main class="page"><p class="eyebrow">SOUTHWESTERN INDIANA · PUBLIC FIELD GUIDE</p><h1>${escapeHtml(species.name)}</h1><p class="latin">${escapeHtml(species.scientific_name)}</p>
<p class="lede">${escapeHtml(description)}</p>
<div class="actions"><a class="button" href="/?bird=${encodeURIComponent(species.code)}&tab=practice&kind=${photo ? "photo" : "audio"}">Practice this bird</a><a class="button secondary" href="/?tab=guide&q=${encodeURIComponent(species.name)}">Browse the field guide</a>${compareLink}</div>
<section class="panel two-col"><div>${photo ? `<img class="hero-photo" src="${escapeHtml(photo.media_url)}" alt="${escapeHtml(species.name)} photograph by ${escapeHtml(photo.creator)}" loading="eager">` : `<p class="gap">No public photograph is currently available for this species.</p>`}${photo ? `<p class="credit">Photograph: ${escapeHtml(photo.creator)} · <a href="${escapeHtml(photo.source_url)}" rel="noreferrer">source</a> · <a href="${escapeHtml(photo.license_url)}" rel="noreferrer">${escapeHtml(photo.license_code ?? "license")}</a></p>` : ""}${audio ? `<p><strong>Listen:</strong></p><audio controls preload="none" src="${escapeHtml(audio.media_url)}"></audio><p class="credit">Recording: ${escapeHtml(audio.creator)} · <a href="${escapeHtml(audio.source_url)}" rel="noreferrer">source</a> · <a href="${escapeHtml(audio.license_url)}" rel="noreferrer">${escapeHtml(audio.license_code ?? "license")}</a></p>` : ""}</div><div><h2>Historical seasonal signal</h2><p>Complete-checklist reporting frequency by native bins/year. This is historical reporting frequency, not an encounter probability or abundance estimate.</p><div class="signal"><div><b>${pct(current.current_reporting_frequency)}</b><span>current reporting frequency</span></div><div><b>${pct(current.approaching_window_rise)}</b><span>potential 14–28 day rise</span></div><div><b>${current.sample_size ?? "—"}</b><span>checklists in current bin</span></div></div></div></section>
<section class="panel"><h2>Season by season</h2><div class="table-wrap"><table><caption>Owner-supplied 2016–2025 county histograms; derived summaries only. Raw eBird exports are not public.</caption><thead><tr><th>Period</th><th>Reporting</th><th>Frequency</th><th>Checklists</th></tr></thead><tbody>${bins || '<tr><td colspan="4">No historical bins available.</td></tr>'}</tbody></table></div></section>
${credits ? `<section class="panel"><h2>Public media and attribution</h2><ul class="credits">${credits}</ul><p class="fine">Media are accepted source records, not expert-verified specimens. Creator, source, exact license and attribution travel with every object.</p></section>` : ""}
<p class="fine">${escapeHtml(EBIRD_CITATION)} <a href="${EBIRD_TERMS}">eBird Data Access Terms</a>. ${escapeHtml(PUBLIC_SCOPE)}</p></main>`;
  return shell(origin, `${species.name} · BirdAhead`, description, canonical, body, photo?.media_url, {
    "@context": "https://schema.org", "@type": "Article", headline: `${species.name} seasonal occurrence and identification`,
    about: { "@type": "Thing", name: species.name, alternateName: species.scientific_name }, isAccessibleForFree: true,
    publisher: { "@type": "Organization", name: "BirdAhead" }, citation: EBIRD_CITATION,
  });
}


export function renderRegionPage(origin: string, countyCode: string, countyName: string, priorities: Array<{ code: string; name: string; frequency: number | null; rise: number | null; photos: number; audio: number }>, vintage: string) {
  const canonical = `${origin}/regions/${countyCode}`;
  const description = `Seasonal birds of ${countyName} County, Indiana: here now, arriving soon, historical reporting signals and public identification practice.`;
  const rows = priorities.map((r) => `<tr><td><a href="/birds/${encodeURIComponent(r.code)}">${escapeHtml(r.name)}</a></td><td>${pct(r.frequency)}</td><td>${pct(r.rise)}</td><td>${r.photos} / ${r.audio}</td></tr>`).join("");
  const body = `<main class="page"><p class="eyebrow">REGIONAL FIELD GUIDE</p><h1>${escapeHtml(countyName)} County</h1><p class="lede">Birds to know before you go, ranked from historical complete-checklist reporting and the next 14–28 day seasonal signal.</p><div class="actions"><a class="button" href="/?county=${encodeURIComponent(countyCode)}&tab=explore">Open regional explorer</a><a class="button secondary" href="/?county=${encodeURIComponent(countyCode)}&tab=practice">Start a public exercise</a></div><section class="panel"><h2>Here now and arriving soon</h2><div class="table-wrap"><table><caption>${escapeHtml(vintage)} · historical reporting frequency, not encounter probability.</caption><thead><tr><th>Species</th><th>Now</th><th>14–28 day rise</th><th>Public photos / audio</th></tr></thead><tbody>${rows}</tbody></table></div></section><p class="fine">${escapeHtml(EBIRD_CITATION)} <a href="${EBIRD_TERMS}">eBird Data Access Terms</a>. ${escapeHtml(PUBLIC_SCOPE)}</p></main>`;
  return shell(origin, `${countyName} County birds · BirdAhead`, description, canonical, body, undefined, { "@context": "https://schema.org", "@type": "Place", name: `${countyName} County, Indiana`, isAccessibleForFree: true });
}

export function renderPrivacyPage(origin: string) {
  const canonical = `${origin}/privacy`;
  const body = `<main class="page prose"><p class="eyebrow">PRIVACY NOTICE</p><h1>A public bird guide, with private corners.</h1><p>You can explore seasonal birds, the field guide, public media and practice exercises without an account. Public browsing does not require a household key.</p><h2>Guest practice</h2><p>Guest practice history is stored in your browser's <code>localStorage</code> and offline practice records may also be kept in IndexedDB. It stays on that device and is not sent to BirdAhead. Clearing site data removes it. There is no guest account, registration or server-side guest profile.</p><h2>Offline downloads</h2><p>Downloaded public media and pack metadata are stored in Cache Storage and IndexedDB on your device. They contain only public, eligible content and its attribution/license notices. Signed-in offline answers are queued locally with the learner profile and release id; they are sent only to that authenticated profile when the device reconnects. Authenticated media and API responses are never stored by the service worker. Removing a pack deletes shared media only when no other downloaded pack needs it.</p><h2>Household sign-in</h2><p>Hank and Heather can optionally sign in with a household access key. Sign-in is for private progress, server-backed practice history, profile isolation and cross-device continuity. Session cookies are host-only, Secure, HttpOnly and SameSite=Strict. Access keys are never placed in client assets, analytics or URLs.</p><h2>Analytics</h2><p>BirdAhead uses the existing CFLab analytics collector. It honors Do Not Track and Global Privacy Control, stores no cookies and no persistent visitor ID, and keeps only a random session identifier in sessionStorage for 30 minutes of inactivity. We do not send access keys, household identity, quiz answers, private progress, precise locations or raw media. Public page paths and aggregate feature events (such as opening the field guide or starting a public exercise) are collected to understand whether the public resource is useful.</p><h2>Data sources</h2><p>See <a href="/sources">sources, rights and limits</a> for eBird terms, media licenses and attribution.</p></main>`;
  return shell(origin, "Privacy notice · BirdAhead", "BirdAhead public browsing, guest local storage, household authentication and privacy-preserving CFLab analytics.", canonical, body);
}

export function renderRobots(origin: string) {
  return `User-agent: *\nAllow: /\nDisallow: /api/\nDisallow: /admin\nDisallow: /media/\nAllow: /media/public/\nSitemap: ${origin}/sitemap.xml\n`;
}

export function renderSitemap(origin: string, species: Array<{ code: string }>, counties: Record<string, string>, lastmod: string) {
  const urls = ["/", "/sources", "/privacy", ...species.map((s) => `/birds/${s.code}`), ...Object.keys(counties).map((c) => `/regions/${c}`)];
  return `<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">${urls.map((path) => `<url><loc>${escapeHtml(origin + path)}</loc><lastmod>${escapeHtml(lastmod)}</lastmod></url>`).join("")}</urlset>`;
}

export function renderSourcesPage(origin: string) {
  const canonical = `${origin}/sources`;
  const body = `<main class="page prose"><p class="eyebrow">SOURCES, RIGHTS AND LIMITS</p><h1>Where BirdAhead comes from.</h1><p>BirdAhead is a free, noncommercial educational project. It does not sell access, show advertising or claim expert or scientific certification. Every public media object is delivered with its creator, original record, exact license and attribution.</p><h2>Seasonal occurrence</h2><p>Derived seasonal summaries use owner-supplied 2016–2025 eBird county histograms. Raw histogram exports are not published. Historical reporting frequency is the fraction of complete checklists reporting a species in a period; it is not an encounter probability, abundance estimate or forecast for a particular outing.</p><p>${escapeHtml(EBIRD_CITATION)}</p><p><a class="button secondary" href="${EBIRD_TERMS}" rel="noreferrer">Read the eBird Data Access Terms</a></p><p class="fine">eBird data are supplied for applied and basic research and education. Reproduction of eBird data or derived products for commercial purposes requires prior written permission. Derived products are supplied with the same terms; raw eBird data are not redistributed. A derived-product notification is prepared for owner review; sending it remains an owner action.</p><h2>Photographs and recordings</h2><p>Public media comes from iNaturalist photographs and Xeno-canto recordings under CC0, CC BY, CC BY-SA, CC BY-NC or CC BY-NC-SA licenses. NC and SA objects are public only in this noncommercial context; share-alike and attribution obligations remain. A source license does not imply endorsement by the creator or provider.</p><ul><li>CC0: public-domain dedication; credit retained as a courtesy.</li><li>CC BY: attribution required.</li><li>CC BY-SA: attribution required; adaptations carry the same license.</li><li>CC BY-NC: attribution required; public noncommercial use only.</li><li>CC BY-NC-SA: attribution and share-alike required; public noncommercial use only.</li></ul><h2>What we do not publish</h2><p>No raw eBird exports, precise observation coordinates, restricted Cornell media, rejected media, household keys, private learning histories, model weights or administrative data are public. Public media remains behind the BirdAhead Worker and private R2 binding; the bucket itself is not public.</p><h2>Corrections</h2><p>Biological acceptance is automated source/model corroboration, not expert verification. If a source record or license changes, an asset can be removed from public delivery without affecting unrelated public functionality. See the <a href="/privacy">privacy notice</a>.</p></main>`;
  return shell(origin, "Sources, rights and limits · BirdAhead", "BirdAhead data sources, eBird terms, media licenses, attribution and public-use limitations.", canonical, body);
}

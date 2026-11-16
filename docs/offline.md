# Offline learning

BirdAhead Phase Four adds selective offline learning without changing the public/private boundary. Public exploration and guest practice still need no account. Offline attempts for a signed-in household learner sync only to that authenticated profile.

## Packs

The Downloads section plans six packs from the active public catalog:

| Pack | Content |
| --- | --- |
| County outing | Here Now plus Arriving Soon media for the selected county/date |
| Here Now | Eligible media for species with historical reporting signal |
| Arriving Soon | Eligible media for species with a 14–28 day rise |
| Photo identification | Every eligible public photograph |
| Audio identification | Every eligible public recording |
| Complete eligible collection | Every public photograph and recording |

The UI displays the number of files and actual byte total from the public catalog, the incremental size after shared media, available storage where the browser exposes `navigator.storage.estimate`, download progress, downloaded packs and removal controls. Shared assets are counted once in each pack and written once to the device.

## Storage model

- **IndexedDB `birdahead-offline-v1`** stores pack definitions/progress, the profile-bound sync queue and local attempt records.
- **Cache Storage `birdahead-pack-assets-v1`** stores one response per public media URL. Removing a pack deletes an asset only when no remaining pack references it.
- **Service-worker shell `birdahead-shell-v2`** is versioned separately. Activating a new shell deletes old `birdahead-shell-*` caches only; it never deletes `birdahead-pack-assets-v1`.
- The service worker caches only `/media/public/*`. Authenticated `/media/*` and every `/api/*` response remain network-only.

A download is resumable at asset granularity: each completed asset is persisted before the next starts. An interrupted tab, aborted fetch or connection loss leaves the pack in `downloading`; Resume verifies already-cached assets and continues with the rest. Every asset must match the release `bytes` and SHA-256 digest before it enters the cache. Cache eviction or a digest mismatch causes that asset to be downloaded again.

## Offline practice and sync

Offline practice uses the stored pack snapshot, not a hidden authenticated API. It supports photo/audio choice or recall, source reveal, a session summary, and adaptive ordering toward assets/species with prior misses. Guest answers remain in this browser. A signed-in learner's answers are recorded in IndexedDB with a durable `offline:<uuid>` event identifier, the pack release identifier and the profile id.

When online, `POST /api/offline/sync` accepts at most 100 events per request. The Worker:

- authenticates the household session and ignores any client-supplied profile;
- rejects an event whose existing id belongs to another learner;
- treats a repeated id for the same learner as a duplicate, not a second attempt;
- validates the current active-release asset, kind, mode, choice and timestamp;
- records a withdrawn/invalid asset as a rejected event without failing the whole batch.

The client removes accepted, duplicate and permanently rejected events from the queue and keeps the queue on an expired session (HTTP 401), dispatching the existing auth-expiry event so the learner can sign in again. It never syncs a guest queue or another profile's queue. If the active content release changes, downloaded packs remain usable offline and the UI marks them stale; refresh replaces the pack, while a withdrawn asset is rejected on sync rather than being written to progress.

## Verification

Automated browser verification (local fixture server with a small synthetic public catalog) covered complete offline reload, photo and audio practice, guest history, interrupted/resumed downloads, deduplication, deletion/reclamation, and service-worker shell preservation. The same flow was repeated against production with a tiny intercepted catalog, including real media bytes; production public smoke passed 23/23 and private smoke 23/23. The full record is in [Phase Four offline evidence](../experiments/phase-four-offline.json). Physical iPhone/Android install, background audio, storage eviction by the OS, and long-running downloads remain device-owner checks. See the Phase Four verification note in `docs/phase-three.md` and the repository smoke outputs.

## Hands-free groundwork

Packs preserve species, media, credits, release id and kind metadata, and practice state is local-first. A later hands-free road-trip mode can consume the same audio pack and queue without changing the service-worker/cache or sync contracts. That mode is intentionally not implemented in this phase.

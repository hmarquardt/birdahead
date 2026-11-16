"""Private, bounded source transfers. URLs and authenticated exceptions are never logged."""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import shutil
import urllib.error
import urllib.parse
import urllib.request

from tooling.discover import PRIVATE, now, save

MISSION = 'BirdAhead public noncommercial educational bird learning; private raw data, compact attributed derived profiles'


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def private_path(path):
    path = Path(path).resolve()
    if not path.is_relative_to(PRIVATE.resolve()):
        raise ValueError('Source, spill and intermediate paths must remain in experiments/private')
    path.mkdir(parents=True, exist_ok=True)
    path.chmod(0o700)
    return path


@dataclass(frozen=True)
class Limits:
    max_download_bytes: int = 64_000_000
    max_input_bytes: int = 500_000_000
    disk_reserve_bytes: int = 20_000_000_000
    memory_mb: int = 2048
    threads: int = 2
    max_spill_bytes: int = 4_000_000_000

    def __post_init__(self):
        if any(value <= 0 for value in self.__dict__.values()):
            raise ValueError('Resource limits must be positive')

    def check_disk(self, directory, additional=0):
        free = shutil.disk_usage(directory).free
        if free - additional < self.disk_reserve_bytes:
            raise ValueError('Disk reserve would be violated')
        return free


class SafeRedirect(urllib.request.HTTPRedirectHandler):
    def __init__(self, hosts, charge):
        self.hosts = set(hosts)
        self.charge = charge

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        target = urllib.parse.urlsplit(newurl)
        if target.scheme != 'https' or target.hostname not in self.hosts:
            raise ValueError('Provider redirect host is not approved')
        self.charge()
        # Signed destination URLs supplied by the provider are used verbatim. No auth headers follow.
        return urllib.request.Request(newurl, method=req.get_method(), headers={'User-Agent': MISSION})


class Transfer:
    def __init__(self, hosts, limits=Limits(), max_requests=20):
        self.hosts, self.limits = set(hosts), limits
        self.remaining, self.requests, self.bytes = limits.max_download_bytes, 0, 0
        self.max_requests = max_requests
        self.events = []
        self.opener = urllib.request.build_opener(SafeRedirect(hosts, self.charge))

    def charge(self):
        if self.requests >= self.max_requests:
            raise ValueError('Request ceiling reached')
        self.requests += 1

    def open(self, url, method='GET', headers=None):
        p = urllib.parse.urlsplit(url)
        if p.scheme != 'https' or p.hostname not in self.hosts or p.username or p.password:
            raise ValueError('Only explicit approved HTTPS provider hosts are supported')
        self.charge()
        try:
            return self.opener.open(urllib.request.Request(url, method=method,
                headers={'User-Agent': MISSION, 'Accept-Encoding': 'identity', **(headers or {})}), timeout=45)
        except urllib.error.HTTPError as exc:
            self.events.append({'method': method, 'http_status': exc.code, 'at': now()})
            raise RuntimeError(f'Provider HTTP {exc.code}; stopped without retry') from None
        except (OSError, urllib.error.URLError):
            raise RuntimeError('Provider transport unavailable; URL omitted') from None

    def metadata(self, url):
        with self.open(url, 'HEAD') as response:
            result = {'bytes': int(response.headers['Content-Length']) if response.headers.get('Content-Length') else None,
                      'etag': response.headers.get('ETag'), 'accept_ranges': response.headers.get('Accept-Ranges'),
                      'content_type': response.headers.get('Content-Type')}
        self.events.append({'method': 'HEAD', 'http_status': 200, **result})
        return result

    def download(self, url, destination, *, expected_sha256=None):
        destination = Path(destination)
        private_path(destination.parent)
        receipt = destination.with_suffix(destination.suffix + '.receipt.json')
        if destination.exists():
            actual = digest(destination)
            pinned = expected_sha256 or (json.loads(receipt.read_text())['sha256'] if receipt.exists() else None)
            if not pinned or actual != pinned:
                raise ValueError('Cached source checksum mismatch')
            return {'bytes': destination.stat().st_size, 'sha256': actual, 'cached': True}
        meta = self.metadata(url)
        size = meta['bytes']
        if size is None or size <= 0 or size > self.limits.max_download_bytes:
            raise ValueError('Unknown or oversized source artifact; no GET issued')
        partial = destination.with_suffix(destination.suffix + '.part')
        checkpoint = partial.with_suffix(partial.suffix + '.json')
        offset = partial.stat().st_size if partial.exists() else 0
        prior = json.loads(checkpoint.read_text()) if checkpoint.exists() else None
        # Resume only a strong, unchanged entity; do not combine bytes across provider snapshots.
        if offset and (not prior or prior != meta or not meta['etag'] or meta['etag'].startswith('W/') or meta['accept_ranges'] != 'bytes'):
            raise ValueError('Partial source cannot safely resume; use a new destination')
        if offset > size or size - offset > self.remaining:
            raise ValueError('Transfer would exceed run byte ceiling')
        self.limits.check_disk(destination.parent, size - offset)
        save(checkpoint, meta)
        if offset != size:
            headers = {'Range': f'bytes={offset}-', 'If-Range': meta['etag']} if offset else {}
            with self.open(url, headers=headers) as response:
                if offset and (response.status != 206 or response.headers.get('Content-Range') != f'bytes {offset}-{size-1}/{size}'):
                    raise ValueError('Provider did not honor the exact resume range')
                if response.headers.get('ETag') != meta['etag']:
                    raise ValueError('Provider entity changed after preflight')
                if any(s in response.headers.get('Content-Type', '').lower() for s in ['text/html', 'application/xhtml']):
                    raise ValueError('Challenge/HTML is not a source artifact')
                with partial.open('ab' if offset else 'wb') as stream:
                    os.chmod(partial, 0o600)
                    received = offset
                    while chunk := response.read(min(1024 * 1024, size - received + 1)):
                        self.bytes += len(chunk)
                        self.remaining -= len(chunk)
                        if self.remaining < 0 or received + len(chunk) > size:
                            raise ValueError('Provider exceeded declared size/byte ceiling')
                        if received == 0 and chunk.lstrip().lower().startswith((b'<!doctype html', b'<html')):
                            raise ValueError('HTTP 200 HTML/challenge body is not an acquisition')
                        self.limits.check_disk(destination.parent, len(chunk))
                        stream.write(chunk)
                        received += len(chunk)
            if received != size:
                raise ValueError('Incomplete transfer; private partial retained for resume')
        actual = digest(partial)
        if expected_sha256 and actual != expected_sha256:
            raise ValueError('Source checksum mismatch')
        partial.replace(destination)
        checkpoint.unlink()
        save(receipt, {'sha256': actual, 'bytes': size})
        self.events.append({'method': 'GET', 'http_status': 206 if offset else 200, 'bytes': size-offset})
        return {'bytes': size, 'sha256': actual, 'cached': False, 'resumed_bytes': offset}

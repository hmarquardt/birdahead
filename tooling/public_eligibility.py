"""Public noncommercial delivery eligibility, independent of biological acceptance.

This is a conservative, explicit policy layer. An asset is publicly deliverable only
when its own license, attribution, source record and delivery permission all pass.
NC/SA assets remain noncommercial and attribution/share-alike obligations travel with
the media. Raw eBird exports are never eligible for public delivery."""
from __future__ import annotations

PUBLIC_LICENSES = {
    'cc0': {'basis': 'CC0 1.0 public-domain dedication; no attribution required by the license, credit retained as a courtesy.', 'noncommercial_only': False, 'share_alike': False},
    'cc-by': {'basis': 'CC BY 4.0 permits sharing and adaptation with attribution.', 'noncommercial_only': False, 'share_alike': False},
    'cc-by-sa': {'basis': 'CC BY-SA 4.0 permits sharing and adaptation with attribution; adaptations carry the same license.', 'noncommercial_only': False, 'share_alike': True},
    'cc-by-nc': {'basis': 'CC BY-NC 4.0 permits public noncommercial sharing with attribution; BirdAhead has no advertising, monetization or paid access.', 'noncommercial_only': True, 'share_alike': False},
    'cc-by-nc-sa': {'basis': 'CC BY-NC-SA 4.0 permits public noncommercial sharing with attribution; adaptations carry the same license and BirdAhead has no monetization.', 'noncommercial_only': True, 'share_alike': True},
}
PUBLIC_SOURCES = {'inaturalist', 'xeno_canto'}


def evaluate(asset: dict) -> dict:
    code = (asset.get('license_code') or '').lower()
    policy = PUBLIC_LICENSES.get(code)
    source = (asset.get('source') or '').lower()
    reasons = []
    if not asset.get('permitted_delivery'):
        reasons.append('delivery permission missing')
    if not policy:
        reasons.append('license not on public allowlist')
    if source not in PUBLIC_SOURCES:
        reasons.append('source not on public allowlist')
    for field in ('license_url', 'creator', 'source_url', 'attribution'):
        if not asset.get(field):
            reasons.append(f'{field} missing')
    derivative = isinstance(asset.get('derivative_of'), dict)
    if derivative and asset.get('license_code') == 'cc0':
        # CC0 permits adaptation; retain the notice, no share-alike obligation.
        pass
    eligible = not reasons
    return {
        'public_delivery': eligible,
        'public_use_basis': policy['basis'] if eligible else None,
        'public_noncommercial_only': bool(policy and policy['noncommercial_only']) if eligible else None,
        'public_share_alike': bool(policy and (policy['share_alike'] or asset.get('share_alike'))) if eligible else None,
        'public_license_notice': (
            'Public noncommercial educational display with creator, source and license attribution. '
            + ('Adaptation/derivative media remains under the source share-alike terms. ' if derivative and policy and policy['share_alike'] else '')
            + ('No advertising, monetization or paid access is present.' if policy and policy['noncommercial_only'] else '')
        ) if eligible else None,
        'public_eligibility_reasons': reasons,
    }

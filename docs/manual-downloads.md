# Official eBird histogram downloads for Phase 0.5

The API key does not provide an authenticated Cornell website session. If a chart returns an access challenge, complete this step in your ordinary signed-in browser. Do not send browser cookies, passwords or the API key.

## Seven consistent county exports

1. Sign into eBird in your browser. Open each county chart below.
2. Confirm the selected location is that county, with **January–December, 2016–2025 inclusive**. Use the same dates for every county; this excludes partial 2026. If the links do not apply the dates, use **Change Date** to set them.
3. Scroll to the bottom and click **Download Histogram Data**. Save the original, unedited export. A chart screenshot or PDF is not sufficient.
4. Put the seven files in `experiments/private/occurrence/incoming/` in this repository. Use the filenames below (preserve the file contents). Record any different date range, units or unavailable county; do not silently mix scopes.
5. Tell the agent when files are saved, or provide their local directory if saved elsewhere. These files stay private and must not be committed.

| County | Official chart | Save as |
| --- | --- | --- |
| Gibson | [Open chart](https://ebird.org/barchart?r=US-IN-051&bmo=1&emo=12&byr=2016&eyr=2025) | `US-IN-051.txt` |
| Pike | [Open chart](https://ebird.org/barchart?r=US-IN-125&bmo=1&emo=12&byr=2016&eyr=2025) | `US-IN-125.txt` |
| Greene | [Open chart](https://ebird.org/barchart?r=US-IN-055&bmo=1&emo=12&byr=2016&eyr=2025) | `US-IN-055.txt` |
| Posey | [Open chart](https://ebird.org/barchart?r=US-IN-129&bmo=1&emo=12&byr=2016&eyr=2025) | `US-IN-129.txt` |
| Knox | [Open chart](https://ebird.org/barchart?r=US-IN-083&bmo=1&emo=12&byr=2016&eyr=2025) | `US-IN-083.txt` |
| Vanderburgh | [Open chart](https://ebird.org/barchart?r=US-IN-163&bmo=1&emo=12&byr=2016&eyr=2025) | `US-IN-163.txt` |
| Warrick | [Open chart](https://ebird.org/barchart?r=US-IN-173&bmo=1&emo=12&byr=2016&eyr=2025) | `US-IN-173.txt` |

Source: [Cornell's histogram download instructions](https://support.ebird.org/en/support/solutions/articles/48001255130-ebird-bar-charts-and-graphs). Export format, bin boundaries, units and sample-size availability will be validated from the actual files. No assumption that this is a 52-week export is built into the import contract.

## Optional destination validation after counties

Use the same date settings and download mechanism for [Cane Ridge WMA](https://ebird.org/barchart?r=L320465&bmo=1&emo=12&byr=2016&eyr=2025), [Gibson Lake Wildlife Habitat](https://ebird.org/barchart?r=L1872968&bmo=1&emo=12&byr=2016&eyr=2025) and [Snakey Point Marsh](https://ebird.org/barchart?r=L564337&bmo=1&emo=12&byr=2016&eyr=2025). Save as the corresponding hotspot ID plus `.txt`. County acquisition takes priority; hotspot and county frequencies must retain separate geographic labels.

If the export omits checklist sample sizes, report that fact; do not calculate denominators from species reports. If it uses 48 month subdivisions, preserve their native definitions. Empty cells, zeros and unsupported bins must remain distinct until the source semantics are established.

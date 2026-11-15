# Bootstrap histogram download record — completed

**All seven owner-supplied exports have been imported. No further per-county downloads are requested or planned as a recurring operation.** The owner rejects recurring manual geographic acquisition. Use [the regional EBD/SED and official API architecture](geographic-acquisition.md) for expansion and refresh.

The original files are preserved byte-for-byte in ignored `experiments/private/occurrence/incoming/`, with their downloaded filenames `ebird_US-IN-NNN__2016_2025_1_12_barchart.txt`. Counties are Gibson 051, Greene 055, Knox 083, Pike 125, Posey 129, Vanderburgh 163 and Warrick 173. All scopes are January–December, 2016–2025 inclusive, based on owner download context and filename; bodies do not embed geography, years or taxonomy release.

Reproduce the offline import with `uv run python -m tooling.histograms`. Profiles and full source/crosswalk evidence remain private; [aggregate validation](../experiments/histogram-validation.json) includes hashes, row/sample counts and actual seasonal demonstrations. Raw files are not committed.

For provenance, these were obtained using Cornell's signed-in Bar Charts → **Download Histogram Data** workflow. The API credential does not substitute for a website session. No browser cookies were collected and no challenge was bypassed. [Official export guidance](https://support.ebird.org/en/support/solutions/articles/48001255130-ebird-bar-charts-and-graphs).

An optional future reference export may help diagnose a specific discrepancy, but it must not become an operational requirement. [One coherent EBD/SED access request and delivery clarification](geographic-acquisition.md#one-time-owner-setup-without-per-county-operations) replaces repetitive owner intervention.

# Timeline-GPX-Exporter
Convert Google Timeline JSON exported from an Android device into GPX files (daily or combined).

This script reads these types of files:
- `Timeline.json` (newer format)
- `timeline.json` (case variants)
- `location-history.json` (legacy format with `locations` array)
- `locationHistory.json`, etc.

## Quick start
1. Export timeline from Android: **Settings > Location > Timeline > Export Timeline data**.
2. Copy the JSON file into the script folder (same directory as `Timeline-GPX-Exporter.py`).
3. (recommended) Create and activate a virtual environment:
   - `python -m venv venv`
   - `venv\Scripts\Activate.ps1` (PowerShell) or `venv\Scripts\activate` (cmd)
4. Install dependencies:
   - `python -m pip install -r requirements.txt`
5. Run script as desired:
   - `python Timeline-GPX-Exporter.py`

## Command-line usage
- Default (auto-detect input, per-day output, no overwrite):
  - `python Timeline-GPX-Exporter.py`
- With date range (European format):
  - `python Timeline-GPX-Exporter.py --from 13/05/2023 --to 16/05/2023`
- Single combined GPX output for range:
  - `python Timeline-GPX-Exporter.py --from 13/05/2023 --to 16/05/2023 --single`
- Force overwriting existing output:
  - `python Timeline-GPX-Exporter.py --overwrite`
- Explicit input file:
  - `python Timeline-GPX-Exporter.py --input location-history.json`
- Custom output folder:
  - `python Timeline-GPX-Exporter.py --output .\MyGPX`

## Interactive mode (no flags)
If you run with no arguments, the script prompts for:
- output mode (multiple daily vs single file)
- full range or custom date range (start/end in `DD/MM/YYYY`)
- overwrite existing files (yes/no)
- optional input filename (blank for auto-detect)
- optional output directory (default `GPX_Output`)

Example interactive:
1. `venv\Scripts\python.exe Timeline-GPX-Exporter.py`
2. Answer the prompts.

## Output behavior
- Default: one file per date `YYYY-MM-DD.gpx` under `GPX_Output`.
- Single mode: `YYYY-MM-DD_YYYY-MM-DD.gpx` (date range from selected bounds).
- Overwrite disabled: existing files are skipped and reported.
- Overwrite enabled: existing files are replaced.

## Internal parser support
- `parse_json` handles `semanticSegments` > `timelinePath` points.
- `parse_json2` handles `locations` arrays and `timelineObjects` or old/outdated variants.
- GPS coordinates are normalized (`°`, `Â`, `geo:` cleanup).

## Notes
- Output GPX may not pass strict validators depending on viewer, but works in standard GPX apps.
- The script preserves previous behavior while adding safety, interactive flow, and explicit control.

## Example run
`venv\Scripts\python.exe Timeline-GPX-Exporter.py --from 01/06/2023 --to 05/06/2023 --single --overwrite`

This writes one combined GPX file for the range, replacing existing output file if present.


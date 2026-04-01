import os
import json
import argparse
import sys
import xml.etree.ElementTree as ET
import xml.dom.minidom
from datetime import datetime, timedelta
from dateutil import parser

def create_gpx_file(points, output_file):
    gpx = ET.Element("gpx", version="1.1", creator="https://github.com/Makeshit/Timeline-GPX-Exporter")
    trk = ET.SubElement(gpx, "trk")
    trkseg = ET.SubElement(trk, "trkseg")

    for point in points:
        trkpt = ET.SubElement(trkseg, "trkpt", lat=str(point["lat"]), lon=str(point["lon"]))
        ET.SubElement(trkpt, "time").text = point["time"]

    # Generate pretty XML
    xml_str = xml.dom.minidom.parseString(ET.tostring(gpx)).toprettyxml(indent="  ")

    # Write the pretty XML to a file
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(xml_str)

def parse_json(input_file):
    with open(input_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    points_by_date = {}

    # Extract data points
    for segment in data.get("semanticSegments", []):
        for path_point in segment.get("timelinePath", []):
            try:
                # Extract and parse data
                raw_coords = _normalize_point_string(path_point.get("point", ""))
                coords = [c.strip() for c in raw_coords.split(",") if c.strip()]
                if len(coords) < 2:
                    continue
                lat, lon = float(coords[0]), float(coords[1])
                time = path_point.get("time")

                # Extract date for grouping
                date = datetime.fromisoformat(time).date().isoformat()

                # Group by date
                if date not in points_by_date:
                    points_by_date[date] = []
                points_by_date[date].append({"lat": lat, "lon": lon, "time": time})
            except (KeyError, ValueError):
                continue  # Skip invalid points

    return points_by_date

def _normalize_point_string(raw_point):
    return raw_point.replace("°", "").replace("Â", "").replace("geo:", "").strip()


def parse_json2(input_file):
    with open(input_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    points_by_date = {}

    if isinstance(data, dict):
        if "semanticSegments" in data:
            return parse_json(input_file)
        if "locations" in data:
            for loc in data.get("locations", []):
                try:
                    lat = float(loc.get("latitudeE7", 0)) / 1e7
                    lon = float(loc.get("longitudeE7", 0)) / 1e7
                    timestamp_ms = int(loc.get("timestampMs", 0))
                    time = datetime.utcfromtimestamp(timestamp_ms / 1000)
                    date = time.date().isoformat()
                    points_by_date.setdefault(date, []).append({"lat": lat, "lon": lon, "time": time.isoformat() + "Z"})
                except (KeyError, ValueError, TypeError):
                    continue
            return points_by_date
        data = data.get("timelineObjects", []) if "timelineObjects" in data else []

    if isinstance(data, list):
        for segment in data:
            if isinstance(segment, str):
                continue
            if not isinstance(segment, dict):
                continue

            start_time_value = segment.get("startTime") or segment.get("startTimeUtc")
            if start_time_value:
                try:
                    start_time = parser.parse(start_time_value)
                except (TypeError, ValueError):
                    start_time = None
            else:
                start_time = None

            timeline_path = segment.get("timelinePath") or []
            for path_point in timeline_path:
                try:
                    raw_coords = _normalize_point_string(path_point.get("point", ""))
                    coords = [c.strip() for c in raw_coords.split(",") if c.strip()]
                    if len(coords) < 2:
                        continue
                    lat, lon = float(coords[0]), float(coords[1])

                    if start_time is not None and path_point.get("durationMinutesOffsetFromStartTime") is not None:
                        time = start_time + timedelta(minutes=float(path_point.get("durationMinutesOffsetFromStartTime")))
                    else:
                        time = parser.parse(path_point.get("time")) if path_point.get("time") else None

                    if time is None:
                        continue

                    date = time.date().isoformat()
                    points_by_date.setdefault(date, []).append({"lat": lat, "lon": lon, "time": time.isoformat()})
                except (KeyError, ValueError, TypeError):
                    continue

            # Also check for visit/activity latLng entries in timeline objects
            for activity_key in ("activitySegment", "placeVisit"):
                activity = segment.get(activity_key)
                if not isinstance(activity, dict):
                    continue
                start_time_activity = activity.get("duration", {}).get("startTimestamp") if activity.get("duration") else None
                if start_time_activity:
                    try:
                        time = parser.parse(start_time_activity)
                        date = time.date().isoformat()
                        latlng = activity.get("location", {}).get("latitudeE7") if activity.get("location") else None
                        if latlng is not None:
                            lat = float(activity["location"]["latitudeE7"]) / 1e7
                            lon = float(activity["location"]["longitudeE7"]) / 1e7
                            points_by_date.setdefault(date, []).append({"lat": lat, "lon": lon, "time": time.isoformat()})
                    except (KeyError, ValueError, TypeError):
                        continue

    return points_by_date

def parse_date(date_str):
    if not date_str:
        return None
    try:
        return datetime.strptime(date_str, "%d/%m/%Y").date()
    except ValueError:
        raise argparse.ArgumentTypeError("Date must be in DD/MM/YYYY format")


def ask_yes_no(prompt, default=False):
    yes = {"y", "yes"}
    no = {"n", "no"}
    if default:
        prompt = f"{prompt} [Y/n]: "
    else:
        prompt = f"{prompt} [y/N]: "

    while True:
        value = input(prompt).strip().lower()
        if not value:
            return default
        if value in yes:
            return True
        if value in no:
            return False
        print("Please enter y/yes or n/no.")


def ask_date(prompt):
    while True:
        value = input(prompt).strip()
        try:
            return parse_date(value)
        except argparse.ArgumentTypeError as e:
            print(e)


def filter_points_by_range(points_by_date, from_date, to_date):
    if from_date is None and to_date is None:
        return points_by_date

    filtered = {}
    for ymd, points in points_by_date.items():
        current = datetime.strptime(ymd, "%Y-%m-%d").date()
        if from_date and current < from_date:
            continue
        if to_date and current > to_date:
            continue
        filtered[ymd] = points
    return filtered


def combine_points(points_by_date):
    records = []
    for ymd in sorted(points_by_date):
        for point in points_by_date[ymd]:
            records.append(point)
    return records


def main():
    parser = argparse.ArgumentParser(description="Convert Google Timeline JSON to GPX")
    parser.add_argument("--input", "-i", default=None, help="Input JSON file (optional)." )
    parser.add_argument("--output", "-o", default="GPX_Output", help="Output directory (default GPX_Output)")
    parser.add_argument("--from", dest="date_from", type=parse_date, default=None, help="Start date DD/MM/YYYY")
    parser.add_argument("--to", dest="date_to", type=parse_date, default=None, help="End date DD/MM/YYYY")
    parser.add_argument("--single", action="store_true", help="Create one GPX file for whole range instead of one per day")
    parser.add_argument("--overwrite", action="store_true", help="Allow overwriting existing files in output folder")
    args = parser.parse_args()

    if len(sys.argv) == 1:
        print("Interactive mode: no arguments provided.")
        args.single = ask_yes_no("Create a single GPX file (instead of one file per day)?", default=False)

        range_full = ask_yes_no("Use complete range (all dates in input)?", default=True)
        if not range_full:
            args.date_from = ask_date("Start date (DD/MM/YYYY): ")
            args.date_to = ask_date("End date (DD/MM/YYYY): ")
            while args.date_to < args.date_from:
                print("End date must be the same or after start date. Try again.")
                args.date_from = ask_date("Start date (DD/MM/YYYY): ")
                args.date_to = ask_date("End date (DD/MM/YYYY): ")
        else:
            args.date_from = None
            args.date_to = None

        args.overwrite = ask_yes_no("Overwrite existing output files?", default=False)

        input_file_response = input("Input file name (leave empty to autodetect): ").strip()
        args.input = input_file_response or None

        output_dir_response = input("Output directory (default GPX_Output): ").strip()
        args.output = output_dir_response or "GPX_Output"

    script_dir = os.getcwd()

    candidates = ["Timeline.json", "timeline.json", "location-history.json", "Location-History.json", "locationHistory.json"]
    input_file = None

    if args.input:
        explicit_path = os.path.join(script_dir, args.input)
        if os.path.exists(explicit_path):
            input_file = explicit_path
        elif os.path.exists(args.input):
            input_file = args.input
        else:
            print(f"Input file '{args.input}' not found. Aborting.")
            return

    if input_file is None:
        for name in candidates:
            path = os.path.join(script_dir, name)
            if os.path.exists(path):
                input_file = path
                break

    if input_file is None:
        print(f"Input file not found in {script_dir}. Expected one of: {', '.join(candidates)}")
        return

    output_dir = os.path.join(script_dir, args.output)
    os.makedirs(output_dir, exist_ok=True)

    # Determine parser based on JSON content
    with open(input_file, "r", encoding="utf-8") as f:
        raw_data = json.load(f)

    if isinstance(raw_data, dict) and "semanticSegments" in raw_data:
        points_by_date = parse_json(input_file)
    else:
        points_by_date = parse_json2(input_file)

    points_by_date = filter_points_by_range(points_by_date, args.date_from, args.date_to)

    if not points_by_date:
        print("No points found in selected date range.")
        return

    if args.single:
        all_points = combine_points(points_by_date)
        if not all_points:
            print("No points found to write.")
            return

        # determine filename with selected range or full range if not set
        start = args.date_from or min(datetime.strptime(d, "%Y-%m-%d").date() for d in points_by_date)
        end = args.date_to or max(datetime.strptime(d, "%Y-%m-%d").date() for d in points_by_date)
        filename = f"{start.strftime('%Y-%m-%d')}_{end.strftime('%Y-%m-%d')}.gpx"
        output_file = os.path.join(output_dir, filename)

        if os.path.exists(output_file) and not args.overwrite:
            print(f"Output file already exists and overwrite disabled: {output_file}")
            return

        create_gpx_file(all_points, output_file)
        print(f"Created: {output_file}")
        return

    # per-day generation
    created = 0
    skipped = 0
    for date in sorted(points_by_date):
        points = points_by_date[date]
        formatted_date = datetime.strptime(date, "%Y-%m-%d").strftime("%Y-%m-%d")
        output_file = os.path.join(output_dir, f"{formatted_date}.gpx")

        if os.path.exists(output_file) and not args.overwrite:
            skipped += 1
            print(f"Skipped existing: {output_file}")
            continue

        create_gpx_file(points, output_file)
        created += 1
        print(f"Created: {output_file}")

    print(f"Summary: created {created}, skipped {skipped}, total days processed {len(points_by_date)}")


if __name__ == "__main__":
    main()
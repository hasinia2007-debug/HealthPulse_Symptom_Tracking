"""
HealthPulse - Symptom Tracking (single-file version)

Log symptoms with a severity (1-10), view history, get summaries,
trends (improving / stable / worsening) and safety alerts.
Data is saved in healthpulse_data.json next to this file.

NOTE: Educational project only - NOT a medical device.
"""
import csv
import json
import os
from collections import defaultdict
from datetime import date, datetime, timedelta
from statistics import mean

DB_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "healthpulse_data.json")
RED_FLAGS = {"chest pain", "shortness of breath", "fainting",
             "blood in stool", "slurred speech", "confusion"}
HIGH_SEVERITY = 8
DISCLAIMER = ("NOTE: HealthPulse is an educational project and NOT a medical device. "
              "Always consult a doctor for medical advice.")


# ------------------------- storage -------------------------
def load_logs():
    if not os.path.exists(DB_FILE):
        return []
    try:
        with open(DB_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, list):
            return []
        return data
    except (OSError, TypeError, ValueError, json.JSONDecodeError):
        return []


def save_logs(logs):
    os.makedirs(os.path.dirname(DB_FILE), exist_ok=True)
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(logs, f, indent=2)


# ------------------------- core operations -------------------------
def validate(symptom, severity, log_date):
    if not isinstance(symptom, str) or not symptom.strip():
        raise ValueError("Symptom name cannot be empty.")
    try:
        severity_num = int(severity)
    except (TypeError, ValueError):
        raise ValueError("Severity must be between 1 and 10.")
    if not 1 <= severity_num <= 10:
        raise ValueError("Severity must be between 1 and 10.")
    try:
        datetime.strptime(str(log_date), "%Y-%m-%d")
    except (TypeError, ValueError):
        raise ValueError("Date must be in YYYY-MM-DD format.")
    return severity_num


def add_log(logs, symptom, severity, notes="", log_date=None):
    log_date = log_date or date.today().isoformat()
    severity_num = validate(symptom, severity, log_date)
    entry = {
        "id": max((l["id"] for l in logs), default=0) + 1,
        "date": str(log_date),
        "symptom": symptom.strip().lower(),
        "severity": severity_num,
        "notes": notes,
    }
    logs.append(entry)
    save_logs(logs)
    return entry


def delete_log(logs, log_id):
    remaining = [l for l in logs if l["id"] != log_id]
    if len(remaining) == len(logs):
        return False
    logs[:] = remaining
    save_logs(logs)
    return True


# ------------------------- analysis -------------------------
def summary(logs):
    grouped = defaultdict(list)
    for l in logs:
        grouped[l["symptom"]].append(l["severity"])
    return {s: {"count": len(v), "avg": round(mean(v), 2), "max": max(v)}
            for s, v in sorted(grouped.items(), key=lambda kv: -len(kv[1]))}


def trend(logs, symptom, days=7):
    items = [l for l in logs if l["symptom"] == symptom]
    if not items:
        return "no data"
    latest = max(datetime.strptime(l["date"], "%Y-%m-%d") for l in items)
    recent_start = latest - timedelta(days=days - 1)
    prev_start = recent_start - timedelta(days=days)
    recent, prev = [], []
    for l in items:
        d = datetime.strptime(l["date"], "%Y-%m-%d")
        if d >= recent_start:
            recent.append(l["severity"])
        elif d >= prev_start:
            prev.append(l["severity"])
    if not recent or not prev:
        return "not enough data"
    diff = mean(recent) - mean(prev)
    if diff <= -0.5:
        return "improving"
    if diff >= 0.5:
        return "worsening"
    return "stable"


def alerts(logs):
    out = []
    for l in sorted(logs, key=lambda x: (x["date"], x["id"])):
        if l["symptom"] in RED_FLAGS:
            out.append(f"[URGENT] {l['date']}: '{l['symptom']}' logged - consider seeking medical care.")
        elif l["severity"] >= HIGH_SEVERITY:
            out.append(f"[HIGH] {l['date']}: '{l['symptom']}' severity {l['severity']}/10.")
    return out


# ------------------------- display -------------------------
def bar(n):
    return "#" * n + "." * (10 - n)


def show_logs(logs, symptom=None):
    items = sorted(logs, key=lambda l: (l["date"], l["id"]))
    if symptom:
        items = [l for l in items if l["symptom"] == symptom.strip().lower()]
    if not items:
        print("No symptom logs found.")
        return
    print(f"{'ID':<4}{'DATE':<12}{'SYMPTOM':<14}{'SEVERITY':<16}NOTES")
    print("-" * 70)
    for l in items:
        print(f"{l['id']:<4}{l['date']:<12}{l['symptom']:<14}"
              f"{bar(l['severity'])} {l['severity']:<3}{l['notes']}")


def show_summary(logs):
    if not logs:
        print("No data to summarise.")
        return
    print(f"{'SYMPTOM':<16}{'COUNT':<8}{'AVG':<8}{'MAX':<6}TREND")
    print("-" * 56)
    for name, v in summary(logs).items():
        print(f"{name:<16}{v['count']:<8}{v['avg']:<8}{v['max']:<6}{trend(logs, name)}")
    al = alerts(logs)
    if al:
        print("\nALERTS")
        for a in al:
            print("  " + a)
    print("\n" + DISCLAIMER)


def import_csv(logs, path):
    n = 0
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            add_log(logs, row["symptom"], int(row["severity"]),
                    row.get("notes", ""), row["date"])
            n += 1
    print(f"Imported {n} logs from {path}")


def export_csv(logs, path):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["id", "date", "symptom", "severity", "notes"])
        for l in sorted(logs, key=lambda x: (x["date"], x["id"])):
            w.writerow([l["id"], l["date"], l["symptom"], l["severity"], l["notes"]])
    print(f"Exported {len(logs)} logs to {path}")


def load_demo_data(logs):
    demo = [
        ("2026-10-20", "headache", 6, "After long screen time"),
        ("2026-10-21", "headache", 7, "Worse in the evening"),
        ("2026-10-22", "fever", 5, "Mild temperature 99.5F"),
        ("2026-10-23", "headache", 6, ""),
        ("2026-10-24", "cough", 4, "Dry cough"),
        ("2026-10-25", "headache", 5, "Better after rest"),
        ("2026-10-26", "fatigue", 7, "Poor sleep"),
        ("2026-10-27", "headache", 4, "Drank more water"),
        ("2026-10-28", "cough", 5, ""),
        ("2026-10-29", "headache", 3, "Much better"),
        ("2026-10-30", "fever", 8, "High temperature 102F"),
        ("2026-10-31", "fatigue", 5, ""),
        ("2026-11-01", "headache", 2, "Almost gone"),
        ("2026-11-02", "chest pain", 6, "Tightness after climbing stairs"),
    ]
    for d, s, sev, n in demo:
        add_log(logs, s, sev, n, d)
    print(f"Loaded {len(demo)} demo logs.")


# ------------------------- menu -------------------------
MENU = """
===== HealthPulse - Symptom Tracking =====
1. Add symptom
2. View all logs
3. View logs for one symptom
4. Summary, trends & alerts
5. Delete a log
6. Export to CSV
7. Import from CSV
8. Load demo data
0. Exit
"""


def main():
    logs = load_logs()
    while True:
        print(MENU)
        choice = input("Choose an option: ").strip()
        try:
            if choice == "1":
                symptom = input("Symptom name: ")
                severity = int(input("Severity (1-10): "))
                notes = input("Notes (optional): ")
                d = input("Date YYYY-MM-DD (blank = today): ").strip() or None
                e = add_log(logs, symptom, severity, notes, d)
                print(f"Added #{e['id']}: {e['date']} | {e['symptom']} | severity {e['severity']}/10")
            elif choice == "2":
                show_logs(logs)
            elif choice == "3":
                show_logs(logs, input("Symptom name: "))
            elif choice == "4":
                show_summary(logs)
            elif choice == "5":
                ok = delete_log(logs, int(input("Log ID to delete: ")))
                print("Deleted." if ok else "No log with that ID.")
            elif choice == "6":
                export_csv(logs, input("File name (e.g. report.csv): "))
            elif choice == "7":
                import_csv(logs, input("CSV file path: "))
            elif choice == "8":
                load_demo_data(logs)
            elif choice == "0":
                print("Stay healthy! Goodbye.")
                break
            else:
                print("Invalid option. Please choose 0-8.")
        except ValueError as e:
            print(f"Error: {e}")
        except (FileNotFoundError, KeyError) as e:
            print(f"Error: file problem - {e}")


if __name__ == "__main__":
    main()

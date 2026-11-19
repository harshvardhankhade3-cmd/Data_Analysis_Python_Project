"""Google Sheet madhun client data ghete -> MySQL madhe takte -> dashboard banvte.

Ha program chalu rahto ani config.py madhlya REFRESH_MINUTES nusar pratyek veli:
  1) Google Sheet vachte (download)
  2) Chuki-chi rows kadhte (clean)
  3) MySQL madhe 'results' table madhe takte
  4) MySQL madhun SQL queries chalvun dashboard report (reports/dashboard.html) banvte

Band karayche asel tar Ctrl+C dabva.
"""
import base64
import io
import os
import re
import time
from io import StringIO
from urllib.parse import quote_plus

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
import requests
from sqlalchemy import create_engine

import config

BASE = os.path.dirname(os.path.abspath(__file__))
REPORT_DIR = os.path.join(BASE, "reports")
OUT_FILE = os.path.join(REPORT_DIR, "dashboard.html")
os.makedirs(REPORT_DIR, exist_ok=True)

# Sheet madhe ya column names asayla hav-yat (header row madhe agadi he sarkhech naav)
REQUIRED_COLUMNS = ["student_name", "city", "batch", "subject", "marks", "attendance_pct", "exam_date"]

QUERIES = {
    "kpi": f"""
        SELECT COUNT(DISTINCT student_name) AS students,
               ROUND(AVG(marks), 1) AS avg_marks,
               ROUND(100 * SUM(marks >= {config.PASS_MARK}) / COUNT(*), 1) AS pass_pct,
               ROUND(AVG(attendance_pct), 1) AS avg_attendance
        FROM results
    """,
    "subject": f"""
        SELECT subject,
               ROUND(AVG(marks), 1) AS avg_marks,
               ROUND(100 * SUM(marks >= {config.PASS_MARK}) / COUNT(*), 1) AS pass_pct
        FROM results
        GROUP BY subject
        ORDER BY avg_marks DESC
    """,
    "batch": """
        SELECT batch, ROUND(AVG(marks), 1) AS avg_marks
        FROM results
        GROUP BY batch
        ORDER BY batch
    """,
    "city": """
        SELECT city, ROUND(AVG(marks), 1) AS avg_marks
        FROM results
        GROUP BY city
        ORDER BY avg_marks DESC
    """,
    "grade": """
        SELECT CASE WHEN marks >= 80 THEN 'A (80+)'
                    WHEN marks >= 60 THEN 'B (60-79)'
                    WHEN marks >= 40 THEN 'C (40-59)'
                    ELSE 'F (below 40)' END AS grade,
               COUNT(*) AS results
        FROM results
        GROUP BY grade
        ORDER BY grade
    """,
    "attendance": "SELECT attendance_pct, marks FROM results WHERE attendance_pct IS NOT NULL",
}

CSS = (
    "body{font-family:Arial,sans-serif;background:#f4f6fb;color:#222;margin:20px}"
    "h1{margin:0 0 4px}.sub{color:#666;margin-bottom:14px}"
    ".status{padding:10px 14px;border-radius:8px;margin-bottom:14px;font-size:14px}"
    ".ok{background:#e6f6ea;color:#1d6b32}.bad{background:#fdecea;color:#8a1c1c}"
    ".cards{display:flex;gap:14px;flex-wrap:wrap;margin-bottom:16px}"
    ".card{background:#fff;border-radius:10px;padding:14px 18px;box-shadow:0 1px 4px rgba(0,0,0,.1);min-width:190px}"
    ".card small{color:#666}.card b{display:block;font-size:24px;margin-top:4px}"
    ".box{background:#fff;border-radius:10px;padding:14px;margin:14px 0;box-shadow:0 1px 4px rgba(0,0,0,.1)}"
    ".box img{max-width:100%}"
    "table.tbl{border-collapse:collapse;margin-top:8px;font-size:14px}"
    "table.tbl th,table.tbl td{border:1px solid #ddd;padding:4px 10px;text-align:left}"
)


def make_url(database=None):
    pw = quote_plus(config.DB_PASSWORD)
    path = f"/{database}" if database else ""
    return f"mysql+pymysql://{config.DB_USER}:{pw}@{config.DB_HOST}:{config.DB_PORT}{path}"


def ensure_database():
    root = create_engine(make_url())
    with root.begin() as conn:
        conn.exec_driver_sql(
            f"CREATE DATABASE IF NOT EXISTS {config.DB_NAME} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
        )
    root.dispose()


def sheet_url():
    return (
        f"https://docs.google.com/spreadsheets/d/{config.SHEET_ID}"
        f"/export?format=csv&gid={config.SHEET_GID}"
    )


def fetch_sheet():
    """Google Sheet madhun CSV download karun DataFrame banvte."""
    if config.SHEET_ID.startswith("PASTE"):
        raise ValueError("config.py madhe SHEET_ID takla nahi.")
    resp = requests.get(sheet_url(), timeout=30)
    resp.raise_for_status()
    if "text/html" in resp.headers.get("Content-Type", ""):
        raise ValueError("Sheet public nahi. Sheet madhe Share > Anyone with the link > Viewer kara.")
    df = pd.read_csv(StringIO(resp.text))
    # Column naavanche clean karto: "Student Name" -> "student_name"
    df.columns = [re.sub(r"\W+", "_", str(c).strip().lower()).strip("_") for c in df.columns]
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"Sheet madhe ya column names nahit: {missing}")
    return df


def clean(df):
    """Chuki-chya rows kadhto. Kiti rows vagle te return karto."""
    total = len(df)
    df = df[REQUIRED_COLUMNS].copy()
    # Fakt space asnarya cells NaN mhanun dharto
    df = df.replace(r"^\s*$", pd.NA, regex=True)
    df["marks"] = pd.to_numeric(df["marks"], errors="coerce")
    df["attendance_pct"] = pd.to_numeric(df["attendance_pct"], errors="coerce")
    df = df.dropna(subset=["student_name", "subject", "marks"])
    df = df[df["marks"].between(0, 100)]
    skipped = total - len(df)
    return df, skipped


def load_to_mysql(df):
    engine = create_engine(make_url(config.DB_NAME))
    df.to_sql("results", engine, if_exists="replace", index=False, chunksize=1000)
    engine.dispose()


def get_engine():
    return create_engine(make_url(config.DB_NAME))


def save_fig(fig):
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=100, bbox_inches="tight")
    plt.close(fig)
    return base64.b64encode(buf.getvalue()).decode("ascii")


def bar_fig(df, label, value, title):
    fig, ax = plt.subplots(figsize=(9, 4))
    ax.bar(df[label].astype(str), df[value].astype(float))
    ax.set_title(title)
    ax.tick_params(axis="x", rotation=30)
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    return fig


def scatter_fig(df):
    fig, ax = plt.subplots(figsize=(9, 4))
    if df.empty:
        ax.text(0.5, 0.5, "Attendance data nahi", ha="center", va="center", transform=ax.transAxes)
    else:
        ax.scatter(df["attendance_pct"].astype(float), df["marks"].astype(float), alpha=0.4, s=14)
    ax.set_xlabel("Attendance %")
    ax.set_ylabel("Marks")
    ax.set_title("Attendance vs marks")
    ax.grid(alpha=0.3)
    fig.tight_layout()
    return fig


def fmt(value, suffix=""):
    if value is None or pd.isna(value):
        return "-"
    return f"{float(value):,.1f}{suffix}"


def build_dashboard(status_text, status_ok):
    """MySQL madhun queries chalvun HTML dashboard lihite."""
    engine = get_engine()
    try:
        data = {name: pd.read_sql(q, engine) for name, q in QUERIES.items()}
    except Exception as exc:
        engine.dispose()
        html = _page(
            f"<div class='status bad'>MySQL madhe data nahi: {exc}</div>"
            "<p>Sheet kadhi sync zali ki ha page aapoaap bharel.</p>"
        )
        _write(html)
        return
    engine.dispose()

    kpi = data["kpi"].iloc[0]
    charts = [
        ("Subject-wise average marks", bar_fig(data["subject"], "subject", "avg_marks", "Average marks by subject"),
         data["subject"]),
        ("Subject-wise pass %", bar_fig(data["subject"], "subject", "pass_pct", "Pass % by subject"),
         data["subject"]),
        ("Batch-wise average marks", bar_fig(data["batch"], "batch", "avg_marks", "Average marks by batch"),
         data["batch"]),
        ("City-wise average marks", bar_fig(data["city"], "city", "avg_marks", "Average marks by city"),
         data["city"]),
        ("Grade distribution", bar_fig(data["grade"], "grade", "results", "Results by grade"), data["grade"]),
        ("Attendance vs marks", scatter_fig(data["attendance"]), None),
    ]

    sections = []
    for title, fig, table in charts:
        b64 = save_fig(fig)
        table_html = table.to_html(index=False, border=0, classes="tbl") if table is not None else ""
        sections.append(
            f"<div class='box'><h3>{title}</h3>"
            f"<img src='data:image/png;base64,{b64}' alt='{title}'>{table_html}</div>"
        )

    cards = (
        "<div class='cards'>"
        f"<div class='card'><small>Students</small><b>{fmt(kpi['students'])}</b></div>"
        f"<div class='card'><small>Average marks</small><b>{fmt(kpi['avg_marks'])}</b></div>"
        f"<div class='card'><small>Pass % (40+)</small><b>{fmt(kpi['pass_pct'], '%')}</b></div>"
        f"<div class='card'><small>Average attendance</small><b>{fmt(kpi['avg_attendance'], '%')}</b></div>"
        "</div>"
    )

    status_class = "ok" if status_ok else "bad"
    banner = f"<div class='status {status_class}'>{status_text}</div>"
    _write(_page(banner + cards + "".join(sections)))


def _page(body):
    refresh = int(config.REFRESH_MINUTES * 60)
    return (
        "<!doctype html><html><head><meta charset='utf-8'>"
        f"<meta http-equiv='refresh' content='{refresh}'>"
        "<meta name='viewport' content='width=device-width,initial-scale=1'>"
        "<title>Client Results Dashboard</title>"
        f"<style>{CSS}</style></head><body>"
        "<h1>Client Results Dashboard</h1>"
        f"<div class='sub'>Last updated: {time.strftime('%d-%m-%Y %H:%M:%S')}</div>"
        + body
        + "</body></html>"
    )


def _write(html):
    tmp = OUT_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(html)
    os.replace(tmp, OUT_FILE)


def sync_once():
    """Ek cycle: sheet vachna -> clean -> MySQL -> dashboard."""
    try:
        raw = fetch_sheet()
        df, skipped = clean(raw)
        if df.empty:
            raise ValueError("Sheet not having valid rows.")
        load_to_mysql(df)
        status = (
            f"From sheet {len(df)} valid rows are imported."
        )
        print(status)
        build_dashboard(status, status_ok=True)
    except Exception as exc:
        status = f"Sync fail zala: {exc}. Shevatcha MySQL madhla data dakhavat aahe."
        print(status)
        build_dashboard(status, status_ok=False)


def main():
    ensure_database()
    print("Google Sheet dashboard chalu zala. Band karayche asel tar Ctrl+C dabva.")
    try:
        while True:
            sync_once()
            time.sleep(config.REFRESH_MINUTES * 60)
    except KeyboardInterrupt:
        print("Band zala.")


if __name__ == "__main__":
    main()

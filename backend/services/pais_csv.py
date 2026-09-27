"""Download and parse the official Mifal HaPais Lotto CSV."""

from __future__ import annotations

import csv
import hashlib
import io
import time
from datetime import date

import httpx

from logger import logger
from services.pais_draw_rules import CsvDraw
from services.pais_proxy import PAIS_ARCHIVE_URL, PAIS_CSV_URL, PaisSourceError, open_pais_client

HEADER_DRAW = "הגרלה"
HEADER_DATE = "תאריך"
HEADER_STRONG = "המספר החזק/נוסף"
HEADER_NUMBERS = ("1", "2", "3", "4", "5", "6")


def file_sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def download_official_csv(client: httpx.Client | None = None) -> bytes:
    """Archive page first (sets cookies), then the CSV. A bare CSV GET returns an error page."""
    own_client = client is None
    http = client or open_pais_client()
    body = b""
    try:
        last_error = "Pais CSV URL returned HTML, not the results file"
        for attempt in range(3):
            try:
                archive = http.get(PAIS_ARCHIVE_URL)
                archive.raise_for_status()
                response = http.get(PAIS_CSV_URL, headers={"Referer": PAIS_ARCHIVE_URL})
                response.raise_for_status()
            except httpx.HTTPError as exc:
                last_error = f"Pais CSV download failed: {exc}"
                time.sleep(8)
                continue
            body = response.content
            if body.lstrip().startswith((b"<!DOCTYPE", b"<html", b"<HTML")):
                last_error = "Pais CSV URL returned HTML, not the results file"
                time.sleep(8)
                continue
            if HEADER_DRAW.encode("cp1255") not in body[:200] and HEADER_DRAW.encode("utf-8") not in body[:400]:
                last_error = "Pais CSV header was not the official Lotto columns"
                time.sleep(8)
                continue
            logger.info("Pais CSV downloaded", context={"bytes": len(body), "attempt": attempt + 1})
            return body
        raise PaisSourceError(last_error)
    finally:
        if own_client:
            http.close()


def parse_official_csv(raw: bytes) -> list[CsvDraw]:
    text = raw.decode("cp1255")
    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames or HEADER_DRAW not in reader.fieldnames:
        raise PaisSourceError(f"Unexpected CSV header: {reader.fieldnames}")
    rows: list[CsvDraw] = []
    for record in reader:
        draw_raw = (record.get(HEADER_DRAW) or "").strip()
        date_raw = (record.get(HEADER_DATE) or "").strip()
        if not draw_raw or not date_raw:
            continue
        numbers = [int(record[name]) for name in HEADER_NUMBERS]
        strong = int((record.get(HEADER_STRONG) or "0").strip() or 0)
        day, month, year = (int(part) for part in date_raw.split("/"))
        raw_line = ",".join((record.get(name) or "") for name in reader.fieldnames)
        rows.append(
            CsvDraw(
                draw_number=int(draw_raw),
                draw_date=date(year, month, day),
                numbers=numbers,
                strong=strong,
                raw=raw_line,
            )
        )
    rows.sort(key=lambda row: row.draw_number)
    return rows

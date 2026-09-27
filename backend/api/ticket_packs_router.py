"""Mobile-first ticket pack page and submit actions."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from db.base import SessionLocal
from logger import logger
from services.ticket_pack_service import TicketPackService, pack_lines_copy_block

router = APIRouter(tags=["ticket-packs"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _pack_page_html(pack_id: int, payload: dict) -> str:
    status = payload["status"]
    lines_html = ""
    for idx, ln in enumerate(payload["lines"], start=1):
        labels = ln.get("labels") or []
        label_html = ""
        if labels:
            label_html = f'<p class="labels">{", ".join(labels)}</p>'
        lines_html += f"""
        <li>
          <code>{idx}. {pack_lines_copy_block([ln])}</code>
          {label_html}
        </li>"""

    edge = payload.get("no_edge_label") or ""
    edge_block = f'<p class="edge">{edge}</p>' if edge else ""

    return f"""<!DOCTYPE html>
<html lang="he" dir="rtl">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>חבילת לוטו #{pack_id}</title>
  <style>
    :root {{ font-family: system-ui, sans-serif; font-size: 16px; }}
    body {{ margin: 0; padding: 1rem; max-width: 32rem; margin-inline: auto; }}
    h1 {{ font-size: 1.25rem; }}
    .meta {{ color: #444; font-size: 0.9rem; }}
    ul {{ padding: 0; list-style: none; }}
    li {{ margin: 0.75rem 0; padding: 0.75rem; background: #f4f4f4; border-radius: 8px; }}
    code {{ font-size: 0.95rem; word-break: break-word; }}
    .labels {{ font-size: 0.8rem; color: #a66; margin: 0.25rem 0 0; }}
    .edge {{ background: #fff3cd; padding: 0.5rem; border-radius: 6px; }}
    .actions {{ display: flex; flex-direction: column; gap: 0.5rem; margin-top: 1rem; }}
    button, .btn {{
      padding: 0.85rem 1rem; font-size: 1rem; border: none; border-radius: 8px; cursor: pointer;
    }}
    .primary {{ background: #1a7f37; color: #fff; }}
    .secondary {{ background: #ddd; color: #111; }}
    .copy {{ background: #0b5; color: #fff; width: 100%; }}
    .status {{ font-weight: 600; }}
  </style>
</head>
<body>
  <h1>חבילת 8 שורות ללוטו</h1>
  <p class="meta">מספר הגרלה: {payload.get("target_draw_number")} · תאריך מתוכנן: {payload.get("target_draw_date")}</p>
  <p class="meta">עלות מתוכננת: ₪{payload.get("planned_cost_ils")} · אסטרטגיה: {payload.get("strategy_id")}</p>
  <p class="status">סטטוס: {status}</p>
  {edge_block}
  <ul>{lines_html}</ul>
  <button type="button" class="copy" id="copyBtn">העתק את כל השורות</button>
  <form class="actions" method="post" action="/ticket-packs/{pack_id}/submitted">
    <button type="submit" class="primary">הוגש (קניתי בדלפק)</button>
  </form>
  <form class="actions" method="post" action="/ticket-packs/{pack_id}/not-submitted">
    <button type="submit" class="secondary">לא הוגש</button>
  </form>
  <script>
    const text = `{payload.get("copy_text", "").replace("`", "'")}`;
    document.getElementById("copyBtn").addEventListener("click", () => {{
      navigator.clipboard.writeText(text).then(() => alert("הועתק!"));
    }});
  </script>
</body>
</html>"""


@router.get("/ticket-packs/{pack_id}", response_class=HTMLResponse)
def ticket_pack_page(pack_id: int, db: Session = Depends(get_db)):
    svc = TicketPackService(db)
    pack = svc.get_pack(pack_id)
    if not pack:
        raise HTTPException(status_code=404, detail="Pack not found")
    payload = svc.pack_public_payload(pack)
    return HTMLResponse(_pack_page_html(pack_id, payload))


@router.post("/ticket-packs/{pack_id}/submitted")
def ticket_pack_submitted(pack_id: int, db: Session = Depends(get_db)):
    svc = TicketPackService(db)
    try:
        batch = svc.mark_submitted(pack_id)
        logger.info("Arrr! Pack marked submitted", context={"pack_id": pack_id, "batch_id": batch.id})
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return HTMLResponse(
        f'<html lang="he" dir="rtl"><body><p>הוגש — נרשם ב-real_ticket_batch #{batch.id}. '
        f'<a href="/ticket-packs/{pack_id}">חזרה</a></p></body></html>'
    )


@router.post("/ticket-packs/{pack_id}/not-submitted")
def ticket_pack_not_submitted(pack_id: int, db: Session = Depends(get_db)):
    svc = TicketPackService(db)
    try:
        svc.mark_not_submitted(pack_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return HTMLResponse(
        f'<html lang="he" dir="rtl"><body><p>לא הוגש — אין רשומת כסף אמיתי. '
        f'<a href="/ticket-packs/{pack_id}">חזרה</a></p></body></html>'
    )

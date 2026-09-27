"""Official CSV rules. These do not call the network."""

from datetime import date

from services.pais_csv import parse_official_csv
from services.pais_draw_detail import parse_draw_detail_html
from services.pais_draw_rules import CsvDraw, newest_modern_row, numbers_match, rejection_reason

HEADER = "הגרלה,תאריך,1,2,3,4,5,6,המספר החזק/נוסף,מספר_זוכים_לוטו,מספר_זוכים_דאבל_לוטו,"
ROW_3969 = "3969,26/09/2026,05,07,10,15,27,35,4,0,0,"
OLD_ROW = "2233,01/03/2011,13,20,25,28,33,40,8,,,"


def _csv(*lines: str) -> bytes:
    return "\n".join((HEADER, *lines)).encode("cp1255")


def test_parse_live_3969_row():
    rows = parse_official_csv(_csv(ROW_3969))
    assert len(rows) == 1
    row = rows[0]
    assert row.draw_number == 3969
    assert row.draw_date == date(2026, 9, 26)
    assert row.numbers == [5, 7, 10, 15, 27, 35]
    assert row.strong == 4
    assert rejection_reason(row, previous_number=3968, today=date(2026, 9, 27)) is None


def test_pre_2011_row_is_rejected_not_repaired():
    rows = parse_official_csv(_csv(OLD_ROW))
    reason = rejection_reason(rows[0], previous_number=2232, today=date(2026, 9, 27))
    assert reason == "number_out_of_range"


def test_newest_row_is_by_date_not_the_biggest_number():
    old_series = CsvDraw(9934, date(1999, 8, 24), [1, 2, 3, 4, 5, 6], 1, "")
    current = CsvDraw(3969, date(2026, 9, 26), [5, 7, 10, 15, 27, 35], 4, "")
    newest = newest_modern_row([current, old_series])
    assert newest is not None
    assert newest.draw_number == 3969


def test_numbers_match_ignores_order():
    row = CsvDraw(3969, date(2026, 9, 26), [5, 7, 10, 15, 27, 35], 4, "")
    assert numbers_match([35, 27, 15, 10, 7, 5], 4, row) is True
    assert numbers_match([5, 7, 10, 15, 27, 35], 3, row) is False


def test_draw_page_prizes_from_fixture():
    html = """
    <ol id="regularLottoList">
      <li><div aria-label="רמת פרס 6 + חזק"></div>
          <div aria-label="מספר זוכים 0"></div>
          <div aria-label="סכום זכייה 0 ₪"></div></li>
      <li><div aria-label="רמת פרס 6"></div>
          <div aria-label="מספר זוכים 1"></div>
          <div aria-label="סכום זכייה 375,000 ₪"></div></li>
      <li><div aria-label="רמת פרס 3"></div>
          <div aria-label="מספר זוכים 87,692"></div>
          <div aria-label="סכום זכייה 10 ₪"></div></li>
    </ol>
    <ol id="doubleLottoList">
      <li><div aria-label="רמת פרס 3"></div>
          <div aria-label="מספר זוכים 65,109"></div>
          <div aria-label="סכום זכייה 20 ₪"></div></li>
    </ol>
    <div>סכום הפרס הראשון בהגרלה זו עמד על <strong>22,000,000 ₪</strong> ובדאבל לוטו עד <strong>44,000,000 ₪</strong></div>
    <div>סך כל הפרסים שחולקו בהגרלה זו היה: <strong>6,990,693 ₪</strong></div>
    """
    parsed = parse_draw_detail_html(html)
    assert parsed["prize_6"] == 375000.0
    assert parsed["prize_3"] == 10.0
    assert parsed["jackpot_lotto"] == 22000000.0
    assert parsed["jackpot_double"] == 44000000.0
    assert parsed["total_prizes"] == 6990693.0
    assert parsed["winners_per_tier"]["regular"]["6"]["winners"] == 1.0

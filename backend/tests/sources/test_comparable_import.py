from app.domain.enums import ComparableStatus
from app.sources.imports import parse_comparable_csv


def test_csv_parser_returns_valid_rows_and_precise_errors() -> None:
    content = """product_id,source,status,condition,currency,occurred_at,item_price_cents,shipping_cents,variant_match_confidence_bps,observation_count,sold_through_bps,source_note
00000000-0000-0000-0000-000000000012,EBAY_DE,SOLD,USED,EUR,2026-08-20T10:00:00Z,24900,690,10000,1,7000,authorized export
00000000-0000-0000-0000-000000000012,EBAY_DE,SOLD,USED,EUR,2026-08-21T10:00:00Z,-1,690,10000,1,7000,invalid
"""

    rows, errors = parse_comparable_csv(content)

    assert len(rows) == 1
    assert rows[0].status is ComparableStatus.SOLD
    assert rows[0].item_price_cents == 24900
    assert [(error.row_number, error.field) for error in errors] == [
        (3, "item_price_cents")
    ]

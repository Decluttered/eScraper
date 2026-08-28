import csv
import hashlib
import io
import json

from pydantic import ValidationError

from app.schemas.comparables import ComparableImportRow, ImportRowError


def parse_comparable_csv(
    content: str,
) -> tuple[list[ComparableImportRow], list[ImportRowError]]:
    parsed: list[ComparableImportRow] = []
    errors: list[ImportRowError] = []
    reader = csv.DictReader(io.StringIO(content))
    for row_number, raw_row in enumerate(reader, start=2):
        cleaned = {key: value for key, value in raw_row.items() if key is not None}
        try:
            parsed.append(ComparableImportRow.model_validate(cleaned))
        except ValidationError as exc:
            for detail in exc.errors():
                errors.append(
                    ImportRowError(
                        row_number=row_number,
                        field=".".join(str(part) for part in detail["loc"]),
                        message=str(detail["msg"]),
                    )
                )
    return parsed, errors


def hash_comparable_rows(rows: list[dict[str, object]]) -> str:
    canonical = json.dumps(rows, sort_keys=True, separators=(",", ":"), default=str)
    return "sha256:" + hashlib.sha256(canonical.encode()).hexdigest()

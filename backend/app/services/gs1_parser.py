"""GS1 DataMatrix parser utility."""
import re
from typing import Optional
from app.schemas.schemas import GS1ParsedData


# GS1 Application Identifiers
AI_GTIN = "01"
AI_EXPIRY = "17"
AI_BATCH = "10"
AI_SERIAL = "21"


def parse_gs1_datamatrix(raw: str) -> GS1ParsedData:
    """
    Parse a GS1 DataMatrix string into its component AIs.
    Supports FNC1 separator (\\x1d) and fixed-length AI patterns.
    """
    data = raw.strip()
    # Replace group separator character
    data = data.replace("\x1d", "|")

    result = GS1ParsedData(raw=raw)

    plain = data.replace("|", "")

    # Try structured parsing
    # GTIN (01) is always 14 digits
    gtin_match = re.search(r"(?:^|\|)01(\d{14})", data)
    if gtin_match:
        result.gtin = gtin_match.group(1)

    # Expiry (17) is always 6 digits YYMMDD
    # Match either at separator boundary or anywhere preceded by AI boundary
    expiry_match = re.search(r"(?:^|\||\d)17(\d{6})(?!\d)", data)
    if expiry_match:
        result.expiry = expiry_match.group(1)

    # Batch (10) variable length, terminated by | or next AI
    batch_match = re.search(r"(?:^|\|)10([^|]{1,20})(?:\||$)", data)
    if batch_match:
        result.batch = batch_match.group(1)

    # Serial (21) variable length
    serial_match = re.search(r"(?:^|\|)21([^|]{1,20})(?:\||$)", data)
    if serial_match:
        result.serial = serial_match.group(1)

    # Fallback: simple concatenated string 01{14}17{6}10{var}21{var}
    if not result.gtin and len(plain) >= 20:
        if plain.startswith("01") and len(plain) >= 16:
            result.gtin = plain[2:16]
            remainder = plain[16:]
            if remainder.startswith("17") and len(remainder) >= 8:
                result.expiry = remainder[2:8]
                remainder = remainder[8:]
                if remainder.startswith("10"):
                    remainder = remainder[2:]
                    # batch is up to next AI
                    m = re.match(r"([A-Za-z0-9\-]{1,20})", remainder)
                    if m:
                        result.batch = m.group(1)
    elif result.gtin and not result.expiry:
        # Concatenated without separators: parse positionally after GTIN
        pos = plain.find("01" + result.gtin)
        if pos != -1:
            remainder = plain[pos + 16:]  # skip "01" + 14-digit GTIN
            if remainder.startswith("17") and len(remainder) >= 8:
                result.expiry = remainder[2:8]
                remainder = remainder[8:]
                if remainder.startswith("10"):
                    remainder = remainder[2:]
                    m = re.match(r"([A-Za-z0-9\-]{1,20})", remainder)
                    if m:
                        result.batch = m.group(1)

    return result

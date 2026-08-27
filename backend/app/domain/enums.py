from enum import StrEnum


class Currency(StrEnum):
    EUR = "EUR"


class Marketplace(StrEnum):
    EBAY_DE = "EBAY_DE"
    KLEINANZEIGEN_DE = "KLEINANZEIGEN_DE"
    MANUAL = "MANUAL"


class ProductCategory(StrEnum):
    GPU = "GPU"
    CPU = "CPU"
    MAINBOARD = "MAINBOARD"
    RAM = "RAM"
    SSD = "SSD"
    PSU = "PSU"
    CASE = "CASE"
    COOLER = "COOLER"
    COMPLETE_PC = "COMPLETE_PC"
    OTHER = "OTHER"


class Condition(StrEnum):
    USED = "USED"
    REFURBISHED = "REFURBISHED"
    UNTESTED = "UNTESTED"
    DEFECTIVE = "DEFECTIVE"
    UNKNOWN = "UNKNOWN"


class Recommendation(StrEnum):
    BUY = "BUY"
    NEGOTIATE = "NEGOTIATE"
    WATCH = "WATCH"
    REJECT = "REJECT"


class ConfidenceLevel(StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class ComparableStatus(StrEnum):
    ACTIVE = "ACTIVE"
    SOLD = "SOLD"


class TaxProfileType(StrEnum):
    PRIVATE = "PRIVATE"
    SMALL_BUSINESS = "SMALL_BUSINESS"
    STANDARD_VAT = "STANDARD_VAT"
    MARGIN_SCHEME = "MARGIN_SCHEME"

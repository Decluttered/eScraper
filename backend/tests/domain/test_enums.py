from app.domain.enums import Currency, Marketplace, Recommendation


def test_stable_external_enum_values() -> None:
    assert Currency.EUR.value == "EUR"
    assert Marketplace.EBAY_DE.value == "EBAY_DE"
    assert Recommendation.NEGOTIATE.value == "NEGOTIATE"

"""Smart Trade venue handler."""

from fxfixparser.core.field import FixFieldDefinition
from fxfixparser.venues.base import VenueHandler


class SmartTradeHandler(VenueHandler):
    """Handler for Smart Trade FIX messages."""

    @property
    def name(self) -> str:
        return "Smart Trade"

    @property
    def sender_comp_ids(self) -> list[str]:
        return ["SMARTTRADE", "SMTRADE", "ST", "LFX_CORE", "UAT.ATP.RFS.MKT"]

    @property
    def custom_tags(self) -> list[FixFieldDefinition]:
        """Return Smart Trade-specific custom tag definitions."""
        return [
            # Smart Trade swap pricing tags (1000 range)
            FixFieldDefinition(1065, "BidSwapPoints", "PRICEOFFSET", "Total bid swap points. The combined forward points for the swap (far leg points minus near leg points) on the bid side."),
            FixFieldDefinition(1066, "OfferSwapPoints", "PRICEOFFSET", "Total offer swap points. The combined forward points for the swap (far leg points minus near leg points) on the offer side."),

            # Smart Trade FX Swap tags (8000 range)
            FixFieldDefinition(8004, "FarLegSettlType", "STRING", "Far leg settlement type for FX Swap. Specifies when the second leg of a swap settles (e.g., TOM=Tomorrow, 1M=1 Month).", {
                "TOD": "Today", "TOM": "Tomorrow", "SPOT": "Spot", "SN": "Spot Next",
                "1W": "1 Week", "2W": "2 Weeks", "3W": "3 Weeks",
                "1M": "1 Month", "2M": "2 Months", "3M": "3 Months",
                "4M": "4 Months", "5M": "5 Months", "6M": "6 Months",
                "7M": "7 Months", "8M": "8 Months", "9M": "9 Months",
                "10M": "10 Months", "11M": "11 Months", "1Y": "1 Year",
                "2Y": "2 Years", "3Y": "3 Years", "BD": "Broken Date",
            }),
            FixFieldDefinition(8005, "NearLegSettlType", "STRING", "Near leg settlement type for FX Swap.", {
                "TOD": "Today", "TOM": "Tomorrow", "SPOT": "Spot", "SN": "Spot Next",
            }),
            FixFieldDefinition(8006, "FarLegSettlDate", "LOCALMKTDATE", "Far leg settlement date for FX Swap."),
            FixFieldDefinition(8007, "NearLegSettlDate", "LOCALMKTDATE", "Near leg settlement date for FX Swap."),
            FixFieldDefinition(8011, "NearLegBidAllInRate", "PRICE", "Near leg bid all-in rate. The complete bid exchange rate for the near leg of a swap."),
            FixFieldDefinition(8012, "NearLegOfferAllInRate", "PRICE", "Near leg offer all-in rate. The complete offer exchange rate for the near leg of a swap."),
            FixFieldDefinition(8013, "NearLegBidSize", "QTY", "Near leg bid size. The quantity available at the near leg bid rate."),
            FixFieldDefinition(8014, "NearLegOfferSize", "QTY", "Near leg offer size. The quantity available at the near leg offer rate."),
            FixFieldDefinition(8015, "StreamID", "STRING", "Streaming quote identifier."),
            FixFieldDefinition(8019, "FarLegBidAllInRate", "PRICE", "Far leg bid all-in rate. The complete bid exchange rate for the far leg of a swap."),
            FixFieldDefinition(8020, "FarLegOfferAllInRate", "PRICE", "Far leg offer all-in rate. The complete offer exchange rate for the far leg of a swap."),
            FixFieldDefinition(8021, "DealCurrency", "CURRENCY", "Deal currency. The currency in which the deal quantity is expressed."),
            FixFieldDefinition(8022, "ContraCurrency", "CURRENCY", "Contra currency. The other currency in the pair."),
            FixFieldDefinition(8023, "FarLegBidSize", "QTY", "Far leg bid size."),
            FixFieldDefinition(8024, "FarLegOfferSize", "QTY", "Far leg offer size."),
        ]

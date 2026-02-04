"""Smart Trade (LiquidityFX) venue handler.

Based on smartTrade LiquidityFX Distribution FIX ROE v4.2.78.0-GA specification.
"""

from fxfixparser.core.field import FixFieldDefinition
from fxfixparser.venues.base import VenueHandler
from fxfixparser.tags.fx_tags import LFX_TENOR_VALUES


class SmartTradeHandler(VenueHandler):
    """Handler for Smart Trade LiquidityFX FIX messages."""

    @property
    def name(self) -> str:
        return "Smart Trade (LiquidityFX)"

    @property
    def sender_comp_ids(self) -> list[str]:
        return ["SMARTTRADE", "SMTRADE", "ST", "LFX_CORE", "LFX", "UAT.ATP.RFS.MKT"]

    @property
    def custom_tags(self) -> list[FixFieldDefinition]:
        """Return Smart Trade LiquidityFX-specific custom tag definitions.

        These tags are defined in the LFX FIX ROE specification and are used
        primarily for FX Swap trading.
        """
        return [
            # MassQuote entry identifiers
            FixFieldDefinition(8000, "BidEntryID", "STRING", "Uniquely identifies the bid quote in a MassQuote message."),
            FixFieldDefinition(8001, "OfferEntryID", "STRING", "Uniquely identifies the offer quote in a MassQuote message."),

            # FX Swap settlement type (tenor) for far leg
            FixFieldDefinition(8004, "SettlType2", "STRING", "FX Swap: Far Leg Tenor. See Supported Tenor Codes.", LFX_TENOR_VALUES),

            # FX Swap spot rates for far leg
            FixFieldDefinition(8011, "BidSpotRate2", "PRICE", "FX Swap: Bid entry spot rate of the far leg."),
            FixFieldDefinition(8012, "OfferSpotRate2", "PRICE", "FX Swap: Offer entry spot rate of the far leg."),

            # FX Swap sizes for far leg
            FixFieldDefinition(8013, "BidSize2", "QTY", "FX Swap: Size of the far leg (bid entry/quote)."),
            FixFieldDefinition(8014, "OfferSize2", "QTY", "FX Swap: Size of the far leg (offer entry/quote)."),

            # FX Swap settlement dates (MassQuote)
            FixFieldDefinition(8015, "BidSettlDate", "LOCALMKTDATE", "Settlement date for the bid quote (YYYYMMDD). FX Swap: near leg."),
            FixFieldDefinition(8016, "BidSettlDate2", "LOCALMKTDATE", "FX Swap: Settlement date for the far leg of the bid quote (YYYYMMDD)."),
            FixFieldDefinition(8017, "OfferSettlDate", "LOCALMKTDATE", "Settlement date for the offer quote (YYYYMMDD). FX Swap: near leg."),
            FixFieldDefinition(8018, "OfferSettlDate2", "LOCALMKTDATE", "FX Swap: Settlement date for the far leg of the offer quote (YYYYMMDD)."),

            # FX Swap all-in prices for far leg
            FixFieldDefinition(8019, "BidPx2", "PRICE", "FX Swap: The all-in price of the bid entry's far leg."),
            FixFieldDefinition(8020, "OfferPx2", "PRICE", "FX Swap: The all-in price of the offer entry's far leg."),

            # Quote currencies
            FixFieldDefinition(8021, "BidCurrency", "CURRENCY", "Currency of the bid quote."),
            FixFieldDefinition(8022, "OfferCurrency", "CURRENCY", "Currency of the offer quote."),

            # Swap points (1000 range)
            FixFieldDefinition(1065, "BidSwapPoints", "PRICEOFFSET", "FX Swap: Swap points of the bid entry (far leg - near leg price difference)."),
            FixFieldDefinition(1066, "OfferSwapPoints", "PRICEOFFSET", "FX Swap: Swap points of the offer entry (far leg - near leg price difference)."),

            # Market Data Request size tiers (9000 range)
            FixFieldDefinition(9000, "NoRequestedSize", "NUMINGROUP", "Number of size tiers for tiered market data quotes."),
            FixFieldDefinition(9001, "RequestedSize", "QTY", "The size of the quote tier for tiered market data."),

            # Market Data timestamps
            FixFieldDefinition(9122, "MDEntryOrigTime", "UTCTIMEONLY", "UTC time received from venue (HH:mm:ss.SSS). Only when AggregatedBook=N."),

            # Execution Report - Swap leg prices and quantities
            FixFieldDefinition(9044, "MaturityDate2", "LOCALMKTDATE", "For NDS, fixing date of the far leg (YYYYMMDD)."),
            FixFieldDefinition(9091, "LastPx2", "PRICE", "For Swap, LastPx (fill price) of the far leg."),
            FixFieldDefinition(9092, "LastQty2", "QTY", "For swaps, fill amount of the far leg."),
            FixFieldDefinition(9093, "LeavesQty2", "QTY", "For swap, open quantity of far leg."),
            FixFieldDefinition(9094, "CumQty2", "QTY", "FX Swaps: Cumulative filled quantity of far leg."),
            FixFieldDefinition(9095, "LastSpotRate2", "PRICE", "For Swap, LastSpotRate of the far leg."),

            # Fixing orders
            FixFieldDefinition(9300, "FixingSourceID", "STRING", "ID of the fixing source."),
            FixFieldDefinition(9301, "FixingTime", "UTCTIMESTAMP", "UTC date/time for fixing orders (YYYYMMDD-HH:mm:ss.SSS)."),

            # Regulatory
            FixFieldDefinition(9400, "RegulationType", "STRING", "Type of regulated venue: SEF, MTF, or XOFF.", {
                "SEF": "Swap Execution Facility (US)",
                "MTF": "Multilateral Trading Facility (EU MIFID2)",
                "XOFF": "Off-exchange/Other",
            }),

            # UTI
            FixFieldDefinition(10002, "UTIPrefix", "STRING", "Unique Trade Id prefix."),
            FixFieldDefinition(10003, "UTI", "STRING", "Unique Trade Id."),
            FixFieldDefinition(10011, "IsSEFTrade", "BOOLEAN", "Whether order is traded on SEF or off SEF facility."),

            # Forward Rolls
            FixFieldDefinition(9011, "ClRootOrderID", "STRING", "Forward Rolls: ID of the spot order to roll."),

            # Allocations
            FixFieldDefinition(11001, "RequestType", "CHAR", "Indicates multileg QuoteRequest. M=MULTILEG.", {
                "M": "Multileg",
            }),
            FixFieldDefinition(11003, "AllocationID", "STRING", "Client ID for the pre-allocation group."),
            FixFieldDefinition(11078, "C_NoAllocs", "NUMINGROUP", "Number of pre-allocations."),
            FixFieldDefinition(11079, "C_AllocAccount", "STRING", "Account for this allocation leg."),
            FixFieldDefinition(11467, "C_IndividualAllocID", "STRING", "Client identifier for this allocation leg."),
            FixFieldDefinition(11080, "C_AllocQty", "QTY", "Quantity to be allocated (positive)."),
            FixFieldDefinition(11054, "C_AllocSide", "CHAR", "Side of allocation leg.", {
                "B": "AS_DEFINED (same side)",
                "C": "OPPOSITE (opposite side)",
                "U": "UNDISCLOSED",
            }),
            FixFieldDefinition(11063, "C_AllocSettlType", "STRING", "Swaps: tenor of allocation leg.", LFX_TENOR_VALUES),
            FixFieldDefinition(11064, "C_AllocSettlDate", "LOCALMKTDATE", "Swaps: value date of allocation leg (YYYYMMDD)."),

            # Leg allocations
            FixFieldDefinition(11670, "C_NoLegAllocs", "NUMINGROUP", "Number of allocations for this leg."),
            FixFieldDefinition(11671, "C_LegAllocAccount", "STRING", "Allocation account for this leg."),
            FixFieldDefinition(11672, "C_LegIndividualAllocID", "STRING", "ID of this allocation leg."),
            FixFieldDefinition(11673, "C_LegAllocQty", "QTY", "Quantity to allocate for this leg."),
            FixFieldDefinition(11654, "C_LegAllocSide", "CHAR", "Side of this allocation leg.", {
                "B": "AS_DEFINED (same side as leg)",
                "C": "OPPOSITE (opposite side to leg)",
            }),
        ]

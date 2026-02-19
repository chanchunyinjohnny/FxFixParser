"""Bloomberg DOR (Derivatives Order Routing) venue handler.

Supports Bloomberg's ORP/DOR FIX protocol for FX trading including
Spot, Forward, Swap, NDF, and FX Algo orders.

Bloomberg-specific custom tags are defined in Python below.
Standard FIX tags are already provided by the bundled FIX44.xml spec.
"""

from fxfixparser.core.field import FixFieldDefinition
from fxfixparser.venues.base import VenueHandler

# Bloomberg DOR custom tag definitions for FX-specific fields.
# Standard FIX tags (e.g. 8, 35, 55, 167) are covered by FIX44.xml.
_BLOOMBERG_CUSTOM_TAGS: dict[int, FixFieldDefinition] = {
    22913: FixFieldDefinition(
        tag=22913,
        name="LastMktSpotRate",
        field_type="PRICE",
        description="FX Algo: Prevailing market spot rate at the time of fill.",
    ),
    22914: FixFieldDefinition(
        tag=22914,
        name="AvgMktSpotRate",
        field_type="PRICE",
        description="FX Algo: Average prevailing market spot rate across all fills.",
    ),
    2793: FixFieldDefinition(
        tag=2793,
        name="AvgSpotRate",
        field_type="PRICE",
        description="FX Algo: Average all-in spot rate of all fills.",
    ),
    2794: FixFieldDefinition(
        tag=2794,
        name="AvgForwardPoints",
        field_type="PRICEOFFSET",
        description="FX Algo: Average forward points of all fills.",
    ),
    9032: FixFieldDefinition(
        tag=9032,
        name="AvgCommission",
        field_type="AMT",
        description="FX Algo: Total average commission across all fills.",
    ),
    22858: FixFieldDefinition(
        tag=22858,
        name="AlgoStrategyID",
        field_type="STRING",
        description="FX Algo: Bloomberg internal identifier for the algorithm strategy.",
    ),
    6215: FixFieldDefinition(
        tag=6215,
        name="Tenor",
        field_type="TENOR",
        description="FX tenor code (e.g., SP for Spot, 1W, 1M, 3M, 1Y).",
    ),
    22010: FixFieldDefinition(
        tag=22010,
        name="LegTenor",
        field_type="TENOR",
        description="FX Swap: Tenor code for the individual leg.",
    ),
    22262: FixFieldDefinition(
        tag=22262,
        name="CalculatedCurrency",
        field_type="CURRENCY",
        description="Currency opposite to the dealt currency.",
    ),
    22263: FixFieldDefinition(
        tag=22263,
        name="LegCalculatedCurrency",
        field_type="CURRENCY",
        description="Leg-level currency opposite to the dealt currency.",
    ),
    1071: FixFieldDefinition(
        tag=1071,
        name="LastSwapPoints",
        field_type="PRICEOFFSET",
        description="FX Swap: Swap points differential.",
    ),
    22869: FixFieldDefinition(
        tag=22869,
        name="ForexAccommodationTransaction",
        field_type="BOOLEAN",
        description="Indicates if the trade is an FX accommodation transaction.",
    ),
    9575: FixFieldDefinition(
        tag=9575,
        name="StagedOrderIsInquiry",
        field_type="BOOLEAN",
        description="Distinguishes staged orders from inquiries.",
    ),
    22923: FixFieldDefinition(
        tag=22923,
        name="ManualTicket",
        field_type="INT",
        description="Manual ticket indicator.",
        valid_values={"0": "No", "1": "Before venue", "2": "After venue"},
    ),
    22000: FixFieldDefinition(
        tag=22000,
        name="AutoConfirm",
        field_type="BOOLEAN",
        description="Whether the trade should be auto-confirmed.",
    ),
    1056: FixFieldDefinition(
        tag=1056,
        name="CalculatedCcyLastQty",
        field_type="QTY",
        description="Calculated quantity in the non-dealt currency.",
    ),
    22040: FixFieldDefinition(
        tag=22040,
        name="DV01",
        field_type="PRICE",
        description="Dollar Value of 01: interest rate risk measure.",
    ),
    22041: FixFieldDefinition(
        tag=22041,
        name="LegDV01",
        field_type="PRICE",
        description="Leg-level Dollar Value of 01.",
    ),
    9610: FixFieldDefinition(
        tag=9610,
        name="NoNotes",
        field_type="NUMINGROUP",
        description="Number of note entries in the Bloomberg Notes repeating group.",
    ),
    9612: FixFieldDefinition(
        tag=9612,
        name="NoteLabel",
        field_type="STRING",
        description="Label/title for a Bloomberg note entry.",
    ),
    9613: FixFieldDefinition(
        tag=9613,
        name="NoteText",
        field_type="STRING",
        description="Text content of a Bloomberg note entry.",
    ),
    22941: FixFieldDefinition(
        tag=22941,
        name="SideProtection",
        field_type="INT",
        description="Side intended by taker in RFM request.",
    ),
    9896: FixFieldDefinition(
        tag=9896,
        name="PricingNo",
        field_type="STRING",
        description="Client's TS PX number for quote routing.",
    ),
    2795: FixFieldDefinition(
        tag=2795,
        name="OffshoreIndicator",
        field_type="INT",
        description="Offshore indicator.",
        valid_values={"0": "Regular", "1": "Offshore", "2": "Onshore"},
    ),
}


class BloombergDORHandler(VenueHandler):
    """Handler for Bloomberg DOR (Derivatives Order Routing) FIX messages."""

    @property
    def name(self) -> str:
        return "Bloomberg DOR"

    @property
    def sender_comp_ids(self) -> list[str]:
        return ["BLOOMBERG_DOR", "BBGDOR", "DOR", "FXOM", "ORP"]

    @property
    def custom_tags(self) -> list[FixFieldDefinition]:
        """Return Bloomberg DOR custom tag definitions."""
        return list(_BLOOMBERG_CUSTOM_TAGS.values())

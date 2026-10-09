"""Deterministic, configurable transaction-cost engine for Indian NSE cash equities.

This module provides pure Decimal-based calculations for:
- Individual buy and sell transaction legs.
- Round-trip trades (long and short intraday).
- Statutory taxes (STT, Stamp Duty, GST).
- Regulatory and exchange fees (SEBI turnover fees, NSE transaction charges).
- Brokerage models (flat per order, percentage, capped percentage, zero).
- Execution slippage modeling with explicit double-counting prevention.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import ROUND_HALF_UP, Decimal
from enum import StrEnum

# Standard financial precision constants
_ZERO = Decimal("0")
_ONE_HUNDRED = Decimal("100")
_BPS_DIVISOR = Decimal("10000")
_TWO_PLACES = Decimal("0.01")


class TransactionSide(StrEnum):
    """Direction of an individual transaction leg."""

    BUY = "BUY"
    SELL = "SELL"


class BrokerageType(StrEnum):
    """Supported brokerage tariff structures."""

    FLAT_PER_ORDER = "FLAT_PER_ORDER"
    PERCENT_OF_TURNOVER = "PERCENT_OF_TURNOVER"
    PERCENT_WITH_CAP = "PERCENT_WITH_CAP"
    ZERO = "ZERO"


class RoundingPolicy(StrEnum):
    """Rounding policies for monetary charges and totals."""

    ROUND_EACH_COMPONENT = "ROUND_EACH_COMPONENT"
    ROUND_TOTAL_ONLY = "ROUND_TOTAL_ONLY"
    NO_ROUNDING = "NO_ROUNDING"


def _round_currency(val: Decimal, policy: RoundingPolicy) -> Decimal:
    """Helper to round monetary values to 2 decimal places using ROUND_HALF_UP."""
    if policy == RoundingPolicy.NO_ROUNDING:
        return val
    return val.quantize(_TWO_PLACES, rounding=ROUND_HALF_UP)


@dataclass(frozen=True)
class BrokerageConfig:
    """Configuration for broker commission/brokerage fee.

    Attributes:
        brokerage_type: Tariff model (flat, percent, capped percent, zero).
        rate: Fractional rate on turnover (e.g., Decimal("0.0003") for 0.03%).
        per_order_cap: Maximum fee per executed order in INR (e.g., Decimal("20.00")).
        min_per_order: Minimum fee per executed order in INR (e.g., Decimal("0.00")).
    """

    brokerage_type: BrokerageType = BrokerageType.PERCENT_WITH_CAP
    rate: Decimal = Decimal("0.0003")  # 0.03%
    per_order_cap: Decimal = Decimal("20.00")  # ₹20 cap
    min_per_order: Decimal = Decimal("0.00")

    def __post_init__(self) -> None:
        if self.rate < _ZERO or not self.rate.is_finite():
            raise ValueError(f"Brokerage rate must be non-negative and finite, got {self.rate}")
        if self.per_order_cap < _ZERO or not self.per_order_cap.is_finite():
            raise ValueError(
                f"Brokerage per_order_cap must be non-negative and finite, got {self.per_order_cap}"
            )
        if self.min_per_order < _ZERO or not self.min_per_order.is_finite():
            raise ValueError(
                f"Brokerage min_per_order must be non-negative and finite, got {self.min_per_order}"
            )
        if (
            self.brokerage_type == BrokerageType.PERCENT_WITH_CAP
            and self.min_per_order > self.per_order_cap
        ):
            raise ValueError("min_per_order cannot exceed per_order_cap")


@dataclass(frozen=True)
class CostConfig:
    """Complete, immutable fee and tax schedule for transaction cost calculation.

    Defaults are verified for NSE cash equity intraday post True-to-Label (Oct 1, 2024).

    Attributes:
        schedule_name: Human-readable identifier of the schedule.
        effective_date: Effective date (YYYY-MM-DD) of the verified schedule.
        brokerage: Brokerage calculation parameters.
        stt_rate_sell: Securities Transaction Tax on sell-side turnover (0.025% = 0.00025).
        exchange_txn_rate: NSE cash market transaction charge (₹2.97/lakh = 0.0000297).
        sebi_turnover_rate: SEBI regulatory turnover charge (₹10/crore = 0.000001).
        stamp_duty_rate_buy: Stamp Duty on buy-side turnover (0.003% = 0.00003).
        gst_rate: Goods and Services Tax rate (18% = 0.18).
        gst_on_brokerage: Whether GST applies to brokerage.
        gst_on_exchange_txn: Whether GST applies to exchange transaction charges.
        gst_on_sebi: Whether GST applies to SEBI turnover charges.
        additional_charges_rate: Additional ad-valorem charge (e.g., IPFT if applicable).
        slippage_bps: Default adverse slippage assumption in basis points (1 bps = 0.01%).
        rounding_policy: Financial rounding convention.
        currency: Base currency code (default: INR).
        notes: Contextual notes or circular citations.
    """

    schedule_name: str = "NSE_EQUITY_INTRADAY_OCT_2024"
    effective_date: str = "2024-10-01"
    brokerage: BrokerageConfig = field(default_factory=BrokerageConfig)
    stt_rate_sell: Decimal = Decimal("0.00025")  # 0.025% on sell side
    exchange_txn_rate: Decimal = Decimal("0.0000297")  # 0.00297% (₹2.97 per lakh)
    sebi_turnover_rate: Decimal = Decimal("0.000001")  # 0.0001% (₹10 per crore)
    stamp_duty_rate_buy: Decimal = Decimal("0.00003")  # 0.003% on buy side
    gst_rate: Decimal = Decimal("0.18")  # 18% GST
    gst_on_brokerage: bool = True
    gst_on_exchange_txn: bool = True
    gst_on_sebi: bool = True
    additional_charges_rate: Decimal = Decimal("0.00")
    slippage_bps: Decimal = Decimal("0.00")
    rounding_policy: RoundingPolicy = RoundingPolicy.ROUND_EACH_COMPONENT
    currency: str = "INR"
    notes: str = (
        "Verified statutory & exchange schedule for NSE Cash Equities Intraday "
        "(effective Oct 1, 2024)."
    )

    def __post_init__(self) -> None:
        rates = [
            ("stt_rate_sell", self.stt_rate_sell),
            ("exchange_txn_rate", self.exchange_txn_rate),
            ("sebi_turnover_rate", self.sebi_turnover_rate),
            ("stamp_duty_rate_buy", self.stamp_duty_rate_buy),
            ("gst_rate", self.gst_rate),
            ("additional_charges_rate", self.additional_charges_rate),
            ("slippage_bps", self.slippage_bps),
        ]
        for name, rate in rates:
            if rate < _ZERO or not rate.is_finite():
                raise ValueError(f"{name} must be non-negative and finite, got {rate}")

    @classmethod
    def default_nse_intraday(
        cls,
        slippage_bps: Decimal = Decimal("0.00"),
        brokerage: BrokerageConfig | None = None,
    ) -> CostConfig:
        """Create the verified default NSE cash equity intraday schedule."""
        return cls(
            brokerage=brokerage if brokerage is not None else BrokerageConfig(),
            slippage_bps=slippage_bps,
        )

    @classmethod
    def synthetic_for_testing(
        cls,
        brokerage: BrokerageConfig,
        stt_rate_sell: Decimal = _ZERO,
        exchange_txn_rate: Decimal = _ZERO,
        sebi_turnover_rate: Decimal = _ZERO,
        stamp_duty_rate_buy: Decimal = _ZERO,
        gst_rate: Decimal = _ZERO,
        additional_charges_rate: Decimal = _ZERO,
        slippage_bps: Decimal = _ZERO,
        rounding_policy: RoundingPolicy = RoundingPolicy.ROUND_EACH_COMPONENT,
    ) -> CostConfig:
        """Create a custom synthetic schedule for deterministic arithmetic unit tests."""
        return cls(
            schedule_name="SYNTHETIC_TEST_SCHEDULE",
            effective_date="2026-01-01",
            brokerage=brokerage,
            stt_rate_sell=stt_rate_sell,
            exchange_txn_rate=exchange_txn_rate,
            sebi_turnover_rate=sebi_turnover_rate,
            stamp_duty_rate_buy=stamp_duty_rate_buy,
            gst_rate=gst_rate,
            additional_charges_rate=additional_charges_rate,
            slippage_bps=slippage_bps,
            rounding_policy=rounding_policy,
            notes="Synthetic test configuration with explicit isolated rates.",
        )


@dataclass(frozen=True)
class TransactionLeg:
    """An individual transaction leg (buy or sell).

    Attributes:
        side: BUY or SELL.
        quantity: Positive integer share quantity.
        price: Positive reference price (e.g. signal price or arrival price).
        fill_price: Actual or simulated execution price, if different from reference price.
        notes: Optional reference metadata explaining the calculation.
    """

    side: TransactionSide
    quantity: int
    price: Decimal
    fill_price: Decimal | None = None
    notes: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.quantity, int) or self.quantity <= 0:
            raise ValueError(f"Quantity must be a positive integer, got {self.quantity}")
        if self.price <= _ZERO or not self.price.is_finite():
            raise ValueError(f"Reference price must be positive and finite, got {self.price}")
        if self.fill_price is not None:
            if self.fill_price <= _ZERO or not self.fill_price.is_finite():
                raise ValueError(
                    f"Fill price must be positive and finite when provided, got {self.fill_price}"
                )


@dataclass(frozen=True)
class LegCostBreakdown:
    """Itemized cost breakdown for a single transaction leg.

    Attributes:
        side: BUY or SELL.
        quantity: Executed share quantity.
        price: Benchmark/reference price.
        fill_price: Effective execution price used for calculations.
        turnover: Leg turnover (fill_price * quantity).
        brokerage: Brokerage commission.
        stt: Securities Transaction Tax (levied only on SELL in equity intraday).
        exchange_txn_charge: Stock exchange transaction charge (NSE).
        sebi_turnover_charge: SEBI regulatory turnover charge.
        stamp_duty: Statutory stamp duty (levied only on BUY in equity intraday).
        gst: Goods and Services Tax (18% on eligible charges).
        additional_charges: Any other configured exchange levy.
        explicit_charges: Total explicit fee and tax friction.
        slippage_impact: Adverse execution impact relative to reference price.
        all_in_friction: explicit_charges + slippage_impact.
        config_version: Configuration identifier used.
    """

    side: TransactionSide
    quantity: int
    price: Decimal
    fill_price: Decimal
    turnover: Decimal
    brokerage: Decimal
    stt: Decimal
    exchange_txn_charge: Decimal
    sebi_turnover_charge: Decimal
    stamp_duty: Decimal
    gst: Decimal
    additional_charges: Decimal
    explicit_charges: Decimal
    slippage_impact: Decimal
    all_in_friction: Decimal
    config_version: str


@dataclass(frozen=True)
class RoundTripCostBreakdown:
    """Comprehensive cost and friction breakdown for a completed round-trip trade.

    Attributes:
        entry_leg: Itemized cost breakdown of entry leg.
        exit_leg: Itemized cost breakdown of exit leg.
        quantity: Trade share quantity.
        direction: "LONG" (BUY entry, SELL exit) or "SHORT" (SELL entry, BUY exit).
        buy_turnover: Total turnover of the buy leg.
        sell_turnover: Total turnover of the sell leg.
        total_turnover: Combined buy + sell turnover.
        total_brokerage: Brokerage for entry + exit.
        total_stt: STT for entry + exit (only on sell leg).
        total_exchange_txn_charge: Exchange charges for entry + exit.
        total_sebi_turnover_charge: SEBI charges for entry + exit.
        total_stamp_duty: Stamp duty for entry + exit (only on buy leg).
        total_gst: GST for entry + exit.
        total_additional_charges: Additional charges for entry + exit.
        explicit_charges: Sum of all broker, exchange, and statutory charges.
        slippage_impact: Total adverse execution impact across both legs.
        all_in_friction: Total trading friction (explicit_charges + slippage_impact).
        gross_pnl_at_fill: Gross P&L calculated using effective fill prices.
        gross_pnl_at_ref: Theoretical Gross P&L calculated using reference prices.
        net_pnl: Realized net return after explicit charges (gross_pnl_at_fill - explicit_charges).
        config_version: Configuration identifier used.
    """

    entry_leg: LegCostBreakdown
    exit_leg: LegCostBreakdown
    quantity: int
    direction: str
    buy_turnover: Decimal
    sell_turnover: Decimal
    total_turnover: Decimal
    total_brokerage: Decimal
    total_stt: Decimal
    total_exchange_txn_charge: Decimal
    total_sebi_turnover_charge: Decimal
    total_stamp_duty: Decimal
    total_gst: Decimal
    total_additional_charges: Decimal
    explicit_charges: Decimal
    slippage_impact: Decimal
    all_in_friction: Decimal
    gross_pnl_at_fill: Decimal
    gross_pnl_at_ref: Decimal
    net_pnl: Decimal
    config_version: str


def estimate_slippage(
    side: TransactionSide,
    price: Decimal,
    quantity: int,
    slippage_bps: Decimal,
) -> tuple[Decimal, Decimal]:
    """Calculate the estimated adverse fill price and monetary impact from basis points.

    Convention:
    - BUY: Adverse fill executes higher than reference price (price * (1 + bps/10000)).
    - SELL: Adverse fill executes lower than reference price (price * (1 - bps/10000)).

    Args:
        side: TransactionSide.BUY or TransactionSide.SELL.
        price: Positive reference price.
        quantity: Positive integer quantity.
        slippage_bps: Adverse slippage in basis points (e.g. 5 bps = 0.05%).

    Returns:
        tuple[Decimal, Decimal]: (simulated_fill_price, slippage_monetary_impact)
    """
    if price <= _ZERO or not price.is_finite():
        raise ValueError(f"Price must be positive and finite, got {price}")
    if quantity <= 0:
        raise ValueError(f"Quantity must be a positive integer, got {quantity}")
    if slippage_bps < _ZERO or not slippage_bps.is_finite():
        raise ValueError(f"Slippage BPS must be non-negative, got {slippage_bps}")

    rate = slippage_bps / _BPS_DIVISOR
    qty_dec = Decimal(quantity)

    if side == TransactionSide.BUY:
        simulated_fill = price * (Decimal("1") + rate)
        impact = (simulated_fill - price) * qty_dec
    else:
        simulated_fill = price * (Decimal("1") - rate)
        impact = (price - simulated_fill) * qty_dec

    return simulated_fill, impact


def simulate_fill_with_slippage(
    leg: TransactionLeg,
    slippage_bps: Decimal,
    tick_size: Decimal = Decimal("0.05"),
) -> TransactionLeg:
    """Generate a TransactionLeg with a simulated fill price adjusted for slippage and tick size.

    Args:
        leg: Original transaction leg with reference price.
        slippage_bps: Slippage in basis points.
        tick_size: Minimum price increment (NSE standard is ₹0.05).

    Returns:
        TransactionLeg: Copy of leg with fill_price populated.
    """
    raw_fill, _ = estimate_slippage(leg.side, leg.price, leg.quantity, slippage_bps)
    ticks = (raw_fill / tick_size).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    rounded_fill = ticks * tick_size

    return TransactionLeg(
        side=leg.side,
        quantity=leg.quantity,
        price=leg.price,
        fill_price=rounded_fill,
        notes=f"Simulated fill with {slippage_bps} bps slippage and {tick_size} tick rounding",
    )


def calculate_leg_costs(leg: TransactionLeg, config: CostConfig) -> LegCostBreakdown:
    """Calculate detailed costs, taxes, and slippage for a single transaction leg.

    Args:
        leg: Transaction leg to evaluate.
        config: Cost and fee schedule configuration.

    Returns:
        LegCostBreakdown: Complete itemized breakdown of costs and friction.
    """
    policy = config.rounding_policy
    qty_dec = Decimal(leg.quantity)

    # 1. Determine effective execution price & adverse slippage
    if leg.fill_price is not None:
        effective_fill = leg.fill_price
        if leg.side == TransactionSide.BUY:
            raw_slippage = (effective_fill - leg.price) * qty_dec
        else:
            raw_slippage = (leg.price - effective_fill) * qty_dec
    elif config.slippage_bps > _ZERO:
        effective_fill, raw_slippage = estimate_slippage(
            leg.side, leg.price, leg.quantity, config.slippage_bps
        )
    else:
        effective_fill = leg.price
        raw_slippage = _ZERO

    turnover = effective_fill * qty_dec

    # 2. Brokerage calculation
    b_cfg = config.brokerage
    if b_cfg.brokerage_type == BrokerageType.FLAT_PER_ORDER:
        raw_brokerage = b_cfg.per_order_cap
    elif b_cfg.brokerage_type == BrokerageType.PERCENT_OF_TURNOVER:
        raw_brokerage = turnover * b_cfg.rate
    elif b_cfg.brokerage_type == BrokerageType.PERCENT_WITH_CAP:
        raw_calc = turnover * b_cfg.rate
        capped = min(raw_calc, b_cfg.per_order_cap)
        raw_brokerage = max(capped, b_cfg.min_per_order) if b_cfg.min_per_order > _ZERO else capped
    elif b_cfg.brokerage_type == BrokerageType.ZERO:
        raw_brokerage = _ZERO
    else:
        raise ValueError(f"Unknown brokerage type: {b_cfg.brokerage_type}")

    # 3. Statutory charges
    # STT: Levied ONLY on SELL turnover for equity intraday
    raw_stt = turnover * config.stt_rate_sell if leg.side == TransactionSide.SELL else _ZERO

    # Exchange transaction charge: Levied on BOTH BUY and SELL turnover
    raw_exchange_txn = turnover * config.exchange_txn_rate

    # SEBI turnover charge: Levied on BOTH BUY and SELL turnover
    raw_sebi = turnover * config.sebi_turnover_rate

    # Stamp duty: Levied ONLY on BUY turnover for equity intraday
    raw_stamp_duty = (
        turnover * config.stamp_duty_rate_buy if leg.side == TransactionSide.BUY else _ZERO
    )

    # 4. GST: 18% levied on brokerage + exchange txn charge + SEBI fee
    gst_base = _ZERO
    if config.gst_on_brokerage:
        gst_base += raw_brokerage
    if config.gst_on_exchange_txn:
        gst_base += raw_exchange_txn
    if config.gst_on_sebi:
        gst_base += raw_sebi
    raw_gst = gst_base * config.gst_rate

    # 5. Additional charges (e.g., IPFT if configured)
    raw_additional = turnover * config.additional_charges_rate

    # Apply rounding policy
    if policy == RoundingPolicy.ROUND_EACH_COMPONENT:
        fin_brokerage = _round_currency(raw_brokerage, policy)
        fin_stt = _round_currency(raw_stt, policy)
        fin_exchange_txn = _round_currency(raw_exchange_txn, policy)
        fin_sebi = _round_currency(raw_sebi, policy)
        fin_stamp_duty = _round_currency(raw_stamp_duty, policy)
        fin_gst = _round_currency(raw_gst, policy)
        fin_additional = _round_currency(raw_additional, policy)
        fin_slippage = _round_currency(raw_slippage, policy)
        fin_explicit = (
            fin_brokerage
            + fin_stt
            + fin_exchange_txn
            + fin_sebi
            + fin_stamp_duty
            + fin_gst
            + fin_additional
        )
    elif policy == RoundingPolicy.ROUND_TOTAL_ONLY:
        fin_brokerage = raw_brokerage
        fin_stt = raw_stt
        fin_exchange_txn = raw_exchange_txn
        fin_sebi = raw_sebi
        fin_stamp_duty = raw_stamp_duty
        fin_gst = raw_gst
        fin_additional = raw_additional
        fin_slippage = raw_slippage
        raw_explicit = (
            raw_brokerage
            + raw_stt
            + raw_exchange_txn
            + raw_sebi
            + raw_stamp_duty
            + raw_gst
            + raw_additional
        )
        fin_explicit = _round_currency(raw_explicit, RoundingPolicy.ROUND_TOTAL_ONLY)
    else:  # NO_ROUNDING
        fin_brokerage = raw_brokerage
        fin_stt = raw_stt
        fin_exchange_txn = raw_exchange_txn
        fin_sebi = raw_sebi
        fin_stamp_duty = raw_stamp_duty
        fin_gst = raw_gst
        fin_additional = raw_additional
        fin_slippage = raw_slippage
        fin_explicit = (
            raw_brokerage
            + raw_stt
            + raw_exchange_txn
            + raw_sebi
            + raw_stamp_duty
            + raw_gst
            + raw_additional
        )

    all_in = fin_explicit + fin_slippage
    if policy != RoundingPolicy.NO_ROUNDING:
        turnover = _round_currency(turnover, policy)
        all_in = _round_currency(all_in, policy)

    return LegCostBreakdown(
        side=leg.side,
        quantity=leg.quantity,
        price=leg.price,
        fill_price=effective_fill,
        turnover=turnover,
        brokerage=fin_brokerage,
        stt=fin_stt,
        exchange_txn_charge=fin_exchange_txn,
        sebi_turnover_charge=fin_sebi,
        stamp_duty=fin_stamp_duty,
        gst=fin_gst,
        additional_charges=fin_additional,
        explicit_charges=fin_explicit,
        slippage_impact=fin_slippage,
        all_in_friction=all_in,
        config_version=f"{config.schedule_name}@{config.effective_date}",
    )


def calculate_round_trip_costs(
    entry: TransactionLeg,
    exit: TransactionLeg,
    config: CostConfig,
) -> RoundTripCostBreakdown:
    """Calculate combined round-trip transaction costs, taxes, slippage, and net P&L.

    Validates that:
    1. entry and exit have opposing sides (one BUY, one SELL).
    2. entry and exit quantities match.

    Prevents double-counting of slippage:
    - Gross P&L at fill is calculated from the effective fill prices:
      (exit.fill_price - entry.fill_price) * qty (for LONG).
    - Net P&L = Gross P&L at fill - explicit_charges.
      (Slippage is already captured in the fill price difference and is NOT subtracted twice).

    Args:
        entry: The opening transaction leg.
        exit: The closing transaction leg.
        config: Fee and tax schedule configuration.

    Returns:
        RoundTripCostBreakdown: Comprehensive round-trip accounting.
    """
    if entry.side == exit.side:
        raise ValueError(
            "Round-trip requires opposing transaction legs, "
            f"got entry side {entry.side} and exit side {exit.side}"
        )
    if entry.quantity != exit.quantity:
        raise ValueError(
            "Round-trip leg quantities must match, "
            f"got entry quantity {entry.quantity} and exit quantity {exit.quantity}"
        )

    entry_costs = calculate_leg_costs(entry, config)
    exit_costs = calculate_leg_costs(exit, config)

    qty_dec = Decimal(entry.quantity)
    is_long = entry.side == TransactionSide.BUY
    direction = "LONG" if is_long else "SHORT"

    # Turnovers
    buy_turnover = entry_costs.turnover if is_long else exit_costs.turnover
    sell_turnover = exit_costs.turnover if is_long else entry_costs.turnover
    total_turnover = buy_turnover + sell_turnover

    # Sum components
    total_brokerage = entry_costs.brokerage + exit_costs.brokerage
    total_stt = entry_costs.stt + exit_costs.stt
    total_exchange_txn = entry_costs.exchange_txn_charge + exit_costs.exchange_txn_charge
    total_sebi = entry_costs.sebi_turnover_charge + exit_costs.sebi_turnover_charge
    total_stamp_duty = entry_costs.stamp_duty + exit_costs.stamp_duty
    total_gst = entry_costs.gst + exit_costs.gst
    total_additional = entry_costs.additional_charges + exit_costs.additional_charges

    explicit_charges = entry_costs.explicit_charges + exit_costs.explicit_charges
    total_slippage = entry_costs.slippage_impact + exit_costs.slippage_impact
    all_in_friction = explicit_charges + total_slippage

    # Gross P&L at effective fill prices
    if is_long:
        gross_pnl_at_fill = (exit_costs.fill_price - entry_costs.fill_price) * qty_dec
        gross_pnl_at_ref = (exit.price - entry.price) * qty_dec
    else:
        gross_pnl_at_fill = (entry_costs.fill_price - exit_costs.fill_price) * qty_dec
        gross_pnl_at_ref = (entry.price - exit.price) * qty_dec

    policy = config.rounding_policy
    if policy != RoundingPolicy.NO_ROUNDING:
        gross_pnl_at_fill = _round_currency(gross_pnl_at_fill, policy)
        gross_pnl_at_ref = _round_currency(gross_pnl_at_ref, policy)

    # Net P&L: Deduct explicit charges from fill-based gross P&L.
    # Slippage is already embedded in fill prices; subtracting total_slippage here
    # would double-count adverse execution.
    net_pnl = gross_pnl_at_fill - explicit_charges
    if policy != RoundingPolicy.NO_ROUNDING:
        net_pnl = _round_currency(net_pnl, policy)

    return RoundTripCostBreakdown(
        entry_leg=entry_costs,
        exit_leg=exit_costs,
        quantity=entry.quantity,
        direction=direction,
        buy_turnover=buy_turnover,
        sell_turnover=sell_turnover,
        total_turnover=total_turnover,
        total_brokerage=total_brokerage,
        total_stt=total_stt,
        total_exchange_txn_charge=total_exchange_txn,
        total_sebi_turnover_charge=total_sebi,
        total_stamp_duty=total_stamp_duty,
        total_gst=total_gst,
        total_additional_charges=total_additional,
        explicit_charges=explicit_charges,
        slippage_impact=total_slippage,
        all_in_friction=all_in_friction,
        gross_pnl_at_fill=gross_pnl_at_fill,
        gross_pnl_at_ref=gross_pnl_at_ref,
        net_pnl=net_pnl,
        config_version=f"{config.schedule_name}@{config.effective_date}",
    )

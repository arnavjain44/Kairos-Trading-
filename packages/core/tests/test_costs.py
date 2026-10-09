"""Comprehensive unit tests for kairos_core.costs transaction-cost engine."""

from decimal import Decimal

import pytest
from kairos_core.costs import (
    BrokerageConfig,
    BrokerageType,
    CostConfig,
    RoundingPolicy,
    TransactionLeg,
    TransactionSide,
    calculate_leg_costs,
    calculate_round_trip_costs,
    estimate_slippage,
    simulate_fill_with_slippage,
)


# ------------------------------------------------------------------------------
# Synthetic Fixtures for Independent Arithmetic Verification
# ------------------------------------------------------------------------------
@pytest.fixture
def synthetic_flat_config() -> CostConfig:
    """Deterministic synthetic config with flat ₹20 brokerage, exact predictable taxes."""
    return CostConfig.synthetic_for_testing(
        brokerage=BrokerageConfig(
            brokerage_type=BrokerageType.FLAT_PER_ORDER,
            per_order_cap=Decimal("20.00"),
        ),
        stt_rate_sell=Decimal("0.00025"),  # 0.025%
        exchange_txn_rate=Decimal("0.00003"),  # 0.003%
        sebi_turnover_rate=Decimal("0.000001"),  # 0.0001%
        stamp_duty_rate_buy=Decimal("0.00003"),  # 0.003%
        gst_rate=Decimal("0.18"),  # 18%
        slippage_bps=Decimal("0.00"),
        rounding_policy=RoundingPolicy.ROUND_EACH_COMPONENT,
    )


@pytest.fixture
def synthetic_pct_capped_config() -> CostConfig:
    """Deterministic synthetic config with 0.03% capped at ₹20 brokerage."""
    return CostConfig.synthetic_for_testing(
        brokerage=BrokerageConfig(
            brokerage_type=BrokerageType.PERCENT_WITH_CAP,
            rate=Decimal("0.0003"),
            per_order_cap=Decimal("20.00"),
            min_per_order=Decimal("0.00"),
        ),
        stt_rate_sell=Decimal("0.00025"),
        exchange_txn_rate=Decimal("0.00003"),
        sebi_turnover_rate=Decimal("0.000001"),
        stamp_duty_rate_buy=Decimal("0.00003"),
        gst_rate=Decimal("0.18"),
        slippage_bps=Decimal("0.00"),
        rounding_policy=RoundingPolicy.ROUND_EACH_COMPONENT,
    )


# ------------------------------------------------------------------------------
# 1. Turnover Calculations
# ------------------------------------------------------------------------------
def test_buy_and_sell_turnover_calculation(synthetic_flat_config: CostConfig) -> None:
    """Buy and sell turnover must equal fill_price * quantity exactly."""
    buy_leg = TransactionLeg(side=TransactionSide.BUY, quantity=15, price=Decimal("1234.50"))
    sell_leg = TransactionLeg(side=TransactionSide.SELL, quantity=20, price=Decimal("500.25"))

    buy_costs = calculate_leg_costs(buy_leg, synthetic_flat_config)
    sell_costs = calculate_leg_costs(sell_leg, synthetic_flat_config)

    assert buy_costs.turnover == Decimal("18517.50")  # 15 * 1234.50
    assert sell_costs.turnover == Decimal("10005.00")  # 20 * 500.25


# ------------------------------------------------------------------------------
# 2. Breakeven Gross Trade (No Price Movement)
# ------------------------------------------------------------------------------
def test_round_trip_no_price_movement(synthetic_flat_config: CostConfig) -> None:
    """A round trip with no price change has zero gross P&L and negative net P&L."""
    entry = TransactionLeg(side=TransactionSide.BUY, quantity=10, price=Decimal("1000.00"))
    exit_leg = TransactionLeg(side=TransactionSide.SELL, quantity=10, price=Decimal("1000.00"))

    rt = calculate_round_trip_costs(entry, exit_leg, synthetic_flat_config)

    assert rt.gross_pnl_at_fill == Decimal("0.00")
    assert rt.gross_pnl_at_ref == Decimal("0.00")
    assert rt.explicit_charges > Decimal("0.00")
    assert rt.net_pnl == -rt.explicit_charges


# ------------------------------------------------------------------------------
# 3. Profitable Gross Trade
# ------------------------------------------------------------------------------
def test_round_trip_profitable_trade(synthetic_flat_config: CostConfig) -> None:
    """A profitable gross trade has positive gross P&L, reduced by costs to net P&L."""
    entry = TransactionLeg(side=TransactionSide.BUY, quantity=10, price=Decimal("1000.00"))
    exit_leg = TransactionLeg(side=TransactionSide.SELL, quantity=10, price=Decimal("1020.00"))

    rt = calculate_round_trip_costs(entry, exit_leg, synthetic_flat_config)

    assert rt.gross_pnl_at_fill == Decimal("200.00")
    assert rt.net_pnl == Decimal("200.00") - rt.explicit_charges
    assert Decimal("0.00") < rt.net_pnl < rt.gross_pnl_at_fill


# ------------------------------------------------------------------------------
# 4. Losing Gross Trade
# ------------------------------------------------------------------------------
def test_round_trip_losing_trade(synthetic_flat_config: CostConfig) -> None:
    """A losing trade has negative gross P&L, amplified to greater net loss by friction."""
    entry = TransactionLeg(side=TransactionSide.BUY, quantity=10, price=Decimal("1000.00"))
    exit_leg = TransactionLeg(side=TransactionSide.SELL, quantity=10, price=Decimal("980.00"))

    rt = calculate_round_trip_costs(entry, exit_leg, synthetic_flat_config)

    assert rt.gross_pnl_at_fill == Decimal("-200.00")
    assert rt.net_pnl == Decimal("-200.00") - rt.explicit_charges
    assert rt.net_pnl < rt.gross_pnl_at_fill


# ------------------------------------------------------------------------------
# 5. Flat Brokerage Per Executed Order
# ------------------------------------------------------------------------------
def test_flat_brokerage_calculation() -> None:
    """Flat brokerage should apply the exact per-order fee regardless of turnover."""
    cfg = CostConfig.synthetic_for_testing(
        brokerage=BrokerageConfig(
            brokerage_type=BrokerageType.FLAT_PER_ORDER,
            per_order_cap=Decimal("20.00"),
        )
    )
    leg = TransactionLeg(side=TransactionSide.BUY, quantity=100, price=Decimal("50.00"))
    costs = calculate_leg_costs(leg, cfg)
    assert costs.brokerage == Decimal("20.00")


# ------------------------------------------------------------------------------
# 6. Percentage-Based Brokerage
# ------------------------------------------------------------------------------
def test_percentage_brokerage_without_cap() -> None:
    """Percentage brokerage should scale linearly with turnover."""
    cfg = CostConfig.synthetic_for_testing(
        brokerage=BrokerageConfig(
            brokerage_type=BrokerageType.PERCENT_OF_TURNOVER,
            rate=Decimal("0.0003"),  # 0.03%
        )
    )
    # Turnover = 10 * 1000 = 10,000 -> 10,000 * 0.0003 = 3.00
    leg1 = TransactionLeg(side=TransactionSide.BUY, quantity=10, price=Decimal("1000.00"))
    assert calculate_leg_costs(leg1, cfg).brokerage == Decimal("3.00")

    # Turnover = 100 * 1000 = 100,000 -> 100,000 * 0.0003 = 30.00
    leg2 = TransactionLeg(side=TransactionSide.BUY, quantity=100, price=Decimal("1000.00"))
    assert calculate_leg_costs(leg2, cfg).brokerage == Decimal("30.00")


# ------------------------------------------------------------------------------
# 7. Brokerage Caps and Minimums
# ------------------------------------------------------------------------------
def test_percentage_brokerage_with_cap_and_min() -> None:
    """PERCENT_WITH_CAP respects per-order maximum and optional minimum floor."""
    cfg = CostConfig.synthetic_for_testing(
        brokerage=BrokerageConfig(
            brokerage_type=BrokerageType.PERCENT_WITH_CAP,
            rate=Decimal("0.0003"),  # 0.03%
            per_order_cap=Decimal("20.00"),
            min_per_order=Decimal("5.00"),
        )
    )
    # Turnover = 5,000 -> raw = 1.50 -> clamped up to min_per_order = 5.00
    leg_small = TransactionLeg(side=TransactionSide.BUY, quantity=5, price=Decimal("1000.00"))
    assert calculate_leg_costs(leg_small, cfg).brokerage == Decimal("5.00")

    # Turnover = 30,000 -> raw = 9.00 -> between min and max = 9.00
    leg_mid = TransactionLeg(side=TransactionSide.BUY, quantity=30, price=Decimal("1000.00"))
    assert calculate_leg_costs(leg_mid, cfg).brokerage == Decimal("9.00")

    # Turnover = 100,000 -> raw = 30.00 -> clamped down to cap = 20.00
    leg_large = TransactionLeg(side=TransactionSide.BUY, quantity=100, price=Decimal("1000.00"))
    assert calculate_leg_costs(leg_large, cfg).brokerage == Decimal("20.00")


# ------------------------------------------------------------------------------
# 8. STT Applied Only on Sell Side
# ------------------------------------------------------------------------------
def test_stt_levied_strictly_on_sell_side(synthetic_flat_config: CostConfig) -> None:
    """STT must be strictly zero on BUY leg and exactly rate * turnover on SELL leg."""
    buy_leg = TransactionLeg(side=TransactionSide.BUY, quantity=10, price=Decimal("1000.00"))
    sell_leg = TransactionLeg(side=TransactionSide.SELL, quantity=10, price=Decimal("1000.00"))

    buy_costs = calculate_leg_costs(buy_leg, synthetic_flat_config)
    sell_costs = calculate_leg_costs(sell_leg, synthetic_flat_config)

    # 10,000 * 0.00025 = 2.50
    assert buy_costs.stt == Decimal("0.00")
    assert sell_costs.stt == Decimal("2.50")


# ------------------------------------------------------------------------------
# 9. Stamp Duty Applied Only on Buy Side
# ------------------------------------------------------------------------------
def test_stamp_duty_levied_strictly_on_buy_side(synthetic_flat_config: CostConfig) -> None:
    """Stamp duty must be strictly rate * turnover on BUY leg and zero on SELL leg."""
    buy_leg = TransactionLeg(side=TransactionSide.BUY, quantity=10, price=Decimal("1000.00"))
    sell_leg = TransactionSide.SELL
    sell_leg_obj = TransactionLeg(side=sell_leg, quantity=10, price=Decimal("1000.00"))

    buy_costs = calculate_leg_costs(buy_leg, synthetic_flat_config)
    sell_costs = calculate_leg_costs(sell_leg_obj, synthetic_flat_config)

    # 10,000 * 0.00003 = 0.30
    assert buy_costs.stamp_duty == Decimal("0.30")
    assert sell_costs.stamp_duty == Decimal("0.00")


# ------------------------------------------------------------------------------
# 10. Exchange and SEBI Charges on Both Legs
# ------------------------------------------------------------------------------
def test_exchange_and_sebi_charges_on_both_legs(synthetic_flat_config: CostConfig) -> None:
    """Exchange and SEBI turnover charges apply to both BUY and SELL turnover."""
    buy_leg = TransactionLeg(side=TransactionSide.BUY, quantity=10, price=Decimal("1000.00"))
    sell_leg = TransactionLeg(side=TransactionSide.SELL, quantity=10, price=Decimal("1000.00"))

    buy_costs = calculate_leg_costs(buy_leg, synthetic_flat_config)
    sell_costs = calculate_leg_costs(sell_leg, synthetic_flat_config)

    # 10,000 * 0.00003 = 0.30
    assert buy_costs.exchange_txn_charge == Decimal("0.30")
    assert sell_costs.exchange_txn_charge == Decimal("0.30")

    # 10,000 * 0.000001 = 0.01
    assert buy_costs.sebi_turnover_charge == Decimal("0.01")
    assert sell_costs.sebi_turnover_charge == Decimal("0.01")


# ------------------------------------------------------------------------------
# 11. GST Taxable Base Calculation
# ------------------------------------------------------------------------------
def test_gst_taxable_base_and_exclusion_of_statutory_taxes() -> None:
    """GST is 18% of (Brokerage + Exchange Txn + SEBI). STT and Stamp Duty are excluded."""
    # Custom config: brokerage=10, exch=2, sebi=1, stt=5, stamp=3
    cfg = CostConfig.synthetic_for_testing(
        brokerage=BrokerageConfig(
            brokerage_type=BrokerageType.FLAT_PER_ORDER,
            per_order_cap=Decimal("10.00"),
        ),
        stt_rate_sell=Decimal("0.001"),  # 10 on 10,000
        exchange_txn_rate=Decimal("0.0002"),  # 2 on 10,000
        sebi_turnover_rate=Decimal("0.0001"),  # 1 on 10,000
        stamp_duty_rate_buy=Decimal("0.0003"),  # 3 on 10,000
        gst_rate=Decimal("0.18"),
    )
    leg_buy = TransactionLeg(side=TransactionSide.BUY, quantity=10, price=Decimal("1000.00"))
    costs = calculate_leg_costs(leg_buy, cfg)

    # Brokerage = 10.00, Exchange = 2.00, SEBI = 1.00
    # Taxable base = 10 + 2 + 1 = 13.00
    # GST = 13.00 * 0.18 = 2.34
    assert costs.brokerage == Decimal("10.00")
    assert costs.exchange_txn_charge == Decimal("2.00")
    assert costs.sebi_turnover_charge == Decimal("1.00")
    assert costs.stamp_duty == Decimal("3.00")  # Not in GST base!
    assert costs.gst == Decimal("2.34")


# ------------------------------------------------------------------------------
# 12. Configurable Rates and Schedule Versions
# ------------------------------------------------------------------------------
def test_configurable_schedule_versions() -> None:
    """Config version and metadata must be accurately stamped on output breakdowns."""
    cfg = CostConfig(
        schedule_name="CUSTOM_SCHEDULE_V2",
        effective_date="2027-01-01",
        brokerage=BrokerageConfig(brokerage_type=BrokerageType.ZERO),
    )
    leg = TransactionLeg(side=TransactionSide.BUY, quantity=10, price=Decimal("100.00"))
    costs = calculate_leg_costs(leg, cfg)

    assert costs.config_version == "CUSTOM_SCHEDULE_V2@2027-01-01"


# ------------------------------------------------------------------------------
# 13. Trade Quantities and Price Variations
# ------------------------------------------------------------------------------
@pytest.mark.parametrize(
    ("qty", "price", "expected_turnover"),
    [
        (1, Decimal("10.00"), Decimal("10.00")),
        (10, Decimal("250.50"), Decimal("2505.00")),
        (100, Decimal("999.95"), Decimal("99995.00")),
        (1000, Decimal("2850.00"), Decimal("2850000.00")),
    ],
)
def test_different_quantities_and_prices(
    synthetic_flat_config: CostConfig,
    qty: int,
    price: Decimal,
    expected_turnover: Decimal,
) -> None:
    """Accurately calculates turnover across multiple share price and quantity scales."""
    leg = TransactionLeg(side=TransactionSide.BUY, quantity=qty, price=price)
    costs = calculate_leg_costs(leg, synthetic_flat_config)
    assert costs.turnover == expected_turnover


# ------------------------------------------------------------------------------
# 14. Decimal Precision and Rounding Boundaries
# ------------------------------------------------------------------------------
def test_rounding_policies() -> None:
    """Verify ROUND_EACH_COMPONENT, ROUND_TOTAL_ONLY, and NO_ROUNDING policies."""
    # Use fractional fees that produce recurring digits
    b_cfg = BrokerageConfig(
        brokerage_type=BrokerageType.PERCENT_OF_TURNOVER,
        rate=Decimal("0.0003333"),
    )
    # Turnover = 100 * 33.33 = 3333.00
    # Brokerage = 3333.00 * 0.0003333 = 1.1108889
    leg = TransactionLeg(side=TransactionSide.BUY, quantity=100, price=Decimal("33.33"))

    cfg_each = CostConfig.synthetic_for_testing(
        brokerage=b_cfg, rounding_policy=RoundingPolicy.ROUND_EACH_COMPONENT
    )
    costs_each = calculate_leg_costs(leg, cfg_each)
    assert costs_each.brokerage == Decimal("1.11")

    cfg_none = CostConfig.synthetic_for_testing(
        brokerage=b_cfg, rounding_policy=RoundingPolicy.NO_ROUNDING
    )
    costs_none = calculate_leg_costs(leg, cfg_none)
    assert costs_none.brokerage == Decimal("1.1108889")


# ------------------------------------------------------------------------------
# 15. Slippage for BUY and SELL Legs
# ------------------------------------------------------------------------------
def test_slippage_estimation() -> None:
    """estimate_slippage correctly moves BUY price up and SELL price down."""
    ref_price = Decimal("1000.00")
    qty = 10
    bps = Decimal("5.00")  # 5 bps = 0.05%

    # BUY: 1000 * 1.0005 = 1000.50. Impact = 0.50 * 10 = 5.00
    buy_fill, buy_impact = estimate_slippage(TransactionSide.BUY, ref_price, qty, bps)
    assert buy_fill == Decimal("1000.50")
    assert buy_impact == Decimal("5.00")

    # SELL: 1000 * 0.9995 = 999.50. Impact = 0.50 * 10 = 5.00
    sell_fill, sell_impact = estimate_slippage(TransactionSide.SELL, ref_price, qty, bps)
    assert sell_fill == Decimal("999.50")
    assert sell_impact == Decimal("5.00")


def test_simulate_fill_with_tick_size() -> None:
    """simulate_fill_with_slippage rounds fill price to nearest tick size (₹0.05)."""
    leg = TransactionLeg(side=TransactionSide.BUY, quantity=10, price=Decimal("123.40"))
    # 5 bps on 123.40 is 123.40 * 1.0005 = 123.4617 -> rounds to 123.45 on ₹0.05 tick
    sim_leg = simulate_fill_with_slippage(leg, slippage_bps=Decimal("5.00"))
    assert sim_leg.fill_price == Decimal("123.45")
    assert sim_leg.price == Decimal("123.40")


# ------------------------------------------------------------------------------
# 16. Slippage Accounting & Preventing Double Counting
# ------------------------------------------------------------------------------
def test_no_double_counting_of_slippage(synthetic_flat_config: CostConfig) -> None:
    """Gross P&L at fill embeds slippage; net_pnl = gross_pnl_at_fill - explicit_charges."""
    # Long trade: Ref entry 1000, Ref exit 1050 (Ref Gross P&L = +500)
    # Fill entry = 1001 (+1 adverse slippage on buy), Fill exit = 1048 (-2 adverse slippage on sell)
    # Total slippage impact = (1 * 10) + (2 * 10) = 30.00
    entry = TransactionLeg(
        side=TransactionSide.BUY,
        quantity=10,
        price=Decimal("1000.00"),
        fill_price=Decimal("1001.00"),
    )
    exit_leg = TransactionLeg(
        side=TransactionSide.SELL,
        quantity=10,
        price=Decimal("1050.00"),
        fill_price=Decimal("1048.00"),
    )

    rt = calculate_round_trip_costs(entry, exit_leg, synthetic_flat_config)

    # 1. Check Gross P&L at fill vs reference
    # Gross P&L at fill = (1048 - 1001) * 10 = 470.00
    # Gross P&L at ref = (1050 - 1000) * 10 = 500.00
    assert rt.gross_pnl_at_ref == Decimal("500.00")
    assert rt.gross_pnl_at_fill == Decimal("470.00")
    assert rt.slippage_impact == Decimal("30.00")

    # 2. Net P&L MUST be gross_pnl_at_fill - explicit_charges
    # It must NOT subtract slippage again (which would have yielded 440 - explicit_charges)
    assert rt.net_pnl == rt.gross_pnl_at_fill - rt.explicit_charges

    # 3. Reconcile with all_in_friction:
    # gross_pnl_at_ref - all_in_friction == gross_pnl_at_fill - explicit_charges
    assert rt.gross_pnl_at_ref - rt.all_in_friction == rt.net_pnl


# ------------------------------------------------------------------------------
# 17. Validation of Invalid Inputs
# ------------------------------------------------------------------------------
def test_invalid_transaction_leg_inputs() -> None:
    """Invalid quantities, non-positive or non-finite prices must raise ValueError."""
    with pytest.raises(ValueError, match="Quantity must be a positive integer"):
        TransactionLeg(side=TransactionSide.BUY, quantity=0, price=Decimal("100.00"))

    with pytest.raises(ValueError, match="Quantity must be a positive integer"):
        TransactionLeg(side=TransactionSide.BUY, quantity=-5, price=Decimal("100.00"))

    with pytest.raises(ValueError, match="Reference price must be positive"):
        TransactionLeg(side=TransactionSide.BUY, quantity=10, price=Decimal("0.00"))

    with pytest.raises(ValueError, match="Reference price must be positive"):
        TransactionLeg(side=TransactionSide.BUY, quantity=10, price=Decimal("-10.00"))

    with pytest.raises(ValueError, match="Fill price must be positive"):
        TransactionLeg(
            side=TransactionSide.BUY,
            quantity=10,
            price=Decimal("100.00"),
            fill_price=Decimal("-5.00"),
        )


def test_invalid_cost_config_rates() -> None:
    """Negative fee or tax rates in configuration must raise ValueError."""
    with pytest.raises(ValueError, match="stt_rate_sell must be non-negative"):
        CostConfig(stt_rate_sell=Decimal("-0.01"))

    with pytest.raises(ValueError, match="Brokerage rate must be non-negative"):
        BrokerageConfig(rate=Decimal("-0.001"))

    with pytest.raises(ValueError, match="min_per_order cannot exceed per_order_cap"):
        BrokerageConfig(
            brokerage_type=BrokerageType.PERCENT_WITH_CAP,
            per_order_cap=Decimal("10.00"),
            min_per_order=Decimal("20.00"),
        )


# ------------------------------------------------------------------------------
# 18. Invalid Round-Trip Legs
# ------------------------------------------------------------------------------
def test_invalid_round_trip_legs() -> None:
    """Round-trip must reject matching sides or mismatched quantities."""
    leg_buy_1 = TransactionLeg(side=TransactionSide.BUY, quantity=10, price=Decimal("100.00"))
    leg_buy_2 = TransactionLeg(side=TransactionSide.BUY, quantity=10, price=Decimal("110.00"))
    leg_sell_5 = TransactionLeg(side=TransactionSide.SELL, quantity=5, price=Decimal("110.00"))

    # Both legs BUY
    with pytest.raises(ValueError, match="opposing transaction legs"):
        calculate_round_trip_costs(leg_buy_1, leg_buy_2, CostConfig())

    # Quantity mismatch: 10 vs 5
    with pytest.raises(ValueError, match="quantities must match"):
        calculate_round_trip_costs(leg_buy_1, leg_sell_5, CostConfig())


# ------------------------------------------------------------------------------
# 19. Determinism and Reproducibility
# ------------------------------------------------------------------------------
def test_calculation_determinism(synthetic_pct_capped_config: CostConfig) -> None:
    """Repeated calls with identical inputs must produce identical outputs."""
    entry = TransactionLeg(side=TransactionSide.BUY, quantity=25, price=Decimal("456.75"))
    exit_leg = TransactionLeg(side=TransactionSide.SELL, quantity=25, price=Decimal("465.25"))

    res1 = calculate_round_trip_costs(entry, exit_leg, synthetic_pct_capped_config)
    res2 = calculate_round_trip_costs(entry, exit_leg, synthetic_pct_capped_config)

    assert res1 == res2
    assert res1.net_pnl == res2.net_pnl
    assert res1.explicit_charges == res2.explicit_charges


# ------------------------------------------------------------------------------
# 20. Full Breakdown Hand-Calculated Reconciliation
# ------------------------------------------------------------------------------
def test_full_synthetic_reconciliation() -> None:
    """Fully reconciles every component against an independent hand calculation.

    Scenario:
    - Long trade: Buy 100 shares @ ₹100.00, Sell 100 shares @ ₹102.00
    - Buy Turnover: 10,000.00
    - Sell Turnover: 10,200.00
    - Brokerage: Flat ₹15.00 per order -> Buy: 15.00, Sell: 15.00 -> Total: 30.00
    - STT: 0.025% on Sell only -> 10,200 * 0.00025 = 2.55 -> Total: 2.55
    - Exchange txn: 0.003% on both -> Buy: 0.30, Sell: 0.31 -> Total: 0.61
    - SEBI: 0.0001% on both -> Buy: 0.01, Sell: 0.01 -> Total: 0.02
    - Stamp duty: 0.003% on Buy only -> 10,000 * 0.00003 = 0.30 -> Total: 0.30
    - GST (18% on Brokerage + Exch + SEBI):
      Buy GST base: 15.00 + 0.30 + 0.01 = 15.31 -> 15.31 * 0.18 = 2.7558 -> 2.76
      Sell GST base: 15.00 + 0.31 + 0.01 = 15.32 -> 15.32 * 0.18 = 2.7576 -> 2.76
      Total GST: 2.76 + 2.76 = 5.52
    - Explicit Charges:
      Buy leg: 15.00 + 0.00 + 0.30 + 0.01 + 0.30 + 2.76 = 18.37
      Sell leg: 15.00 + 2.55 + 0.31 + 0.01 + 0.00 + 2.76 = 20.63
      Total Explicit: 18.37 + 20.63 = 39.00
    - Gross P&L: (102.00 - 100.00) * 100 = 200.00
    - Net P&L: 200.00 - 39.00 = 161.00
    """
    cfg = CostConfig.synthetic_for_testing(
        brokerage=BrokerageConfig(
            brokerage_type=BrokerageType.FLAT_PER_ORDER,
            per_order_cap=Decimal("15.00"),
        ),
        stt_rate_sell=Decimal("0.00025"),
        exchange_txn_rate=Decimal("0.00003"),
        sebi_turnover_rate=Decimal("0.000001"),
        stamp_duty_rate_buy=Decimal("0.00003"),
        gst_rate=Decimal("0.18"),
        rounding_policy=RoundingPolicy.ROUND_EACH_COMPONENT,
    )

    entry = TransactionLeg(side=TransactionSide.BUY, quantity=100, price=Decimal("100.00"))
    exit_leg = TransactionLeg(side=TransactionSide.SELL, quantity=100, price=Decimal("102.00"))

    rt = calculate_round_trip_costs(entry, exit_leg, cfg)

    # Component-by-component checks
    assert rt.entry_leg.brokerage == Decimal("15.00")
    assert rt.entry_leg.stt == Decimal("0.00")
    assert rt.entry_leg.exchange_txn_charge == Decimal("0.30")
    assert rt.entry_leg.sebi_turnover_charge == Decimal("0.01")
    assert rt.entry_leg.stamp_duty == Decimal("0.30")
    assert rt.entry_leg.gst == Decimal("2.76")
    assert rt.entry_leg.explicit_charges == Decimal("18.37")

    assert rt.exit_leg.brokerage == Decimal("15.00")
    assert rt.exit_leg.stt == Decimal("2.55")
    assert rt.exit_leg.exchange_txn_charge == Decimal("0.31")
    assert rt.exit_leg.sebi_turnover_charge == Decimal("0.01")
    assert rt.exit_leg.stamp_duty == Decimal("0.00")
    assert rt.exit_leg.gst == Decimal("2.76")
    assert rt.exit_leg.explicit_charges == Decimal("20.63")

    assert rt.explicit_charges == Decimal("39.00")
    assert rt.gross_pnl_at_fill == Decimal("200.00")
    assert rt.net_pnl == Decimal("161.00")


# ------------------------------------------------------------------------------
# 21. Short Trade Support (SELL Entry, BUY Exit)
# ------------------------------------------------------------------------------
def test_short_trade_round_trip(synthetic_flat_config: CostConfig) -> None:
    """Verify short trade where entry is SELL and exit is BUY."""
    # Short profitable trade: Short sell at 500, cover buy at 480 (Profit = +20/share)
    entry = TransactionLeg(side=TransactionSide.SELL, quantity=10, price=Decimal("500.00"))
    exit_leg = TransactionLeg(side=TransactionSide.BUY, quantity=10, price=Decimal("480.00"))

    rt = calculate_round_trip_costs(entry, exit_leg, synthetic_flat_config)

    assert rt.direction == "SHORT"
    assert rt.gross_pnl_at_fill == Decimal("200.00")  # (500 - 480) * 10
    assert rt.sell_turnover == Decimal("5000.00")
    assert rt.buy_turnover == Decimal("4800.00")

    # STT on entry (SELL) only
    assert rt.entry_leg.stt == Decimal("1.25")  # 5000 * 0.00025
    assert rt.exit_leg.stt == Decimal("0.00")

    # Stamp duty on exit (BUY) only
    assert rt.entry_leg.stamp_duty == Decimal("0.00")
    assert rt.exit_leg.stamp_duty == Decimal("0.14")  # 4800 * 0.00003 = 0.144 -> 0.14

    assert rt.net_pnl == Decimal("200.00") - rt.explicit_charges


# ------------------------------------------------------------------------------
# 22. Verified NSE Default Schedule Reference Test
# ------------------------------------------------------------------------------
def test_verified_default_nse_intraday_schedule() -> None:
    """Tests the verified default NSE schedule on a ₹10,000 capital typical intraday trade.

    Scenario:
    - 20 shares of a ₹500 stock (Turnover ~ ₹10,000 per leg).
    - Entry BUY @ 500.00, Exit SELL @ 505.00 (+1% move).
    - Buy Turnover: 10,000.00
    - Sell Turnover: 10,100.00
    """
    cfg = CostConfig.default_nse_intraday()
    assert cfg.schedule_name == "NSE_EQUITY_INTRADAY_OCT_2024"
    assert cfg.effective_date == "2024-10-01"

    entry = TransactionLeg(side=TransactionSide.BUY, quantity=20, price=Decimal("500.00"))
    exit_leg = TransactionLeg(side=TransactionSide.SELL, quantity=20, price=Decimal("505.00"))

    rt = calculate_round_trip_costs(entry, exit_leg, cfg)

    # Buy brokerage: 0.03% on 10,000 = ₹3.00 (below ₹20 cap)
    assert rt.entry_leg.brokerage == Decimal("3.00")
    # Sell brokerage: 0.03% on 10,100 = ₹3.03 (below ₹20 cap)
    assert rt.exit_leg.brokerage == Decimal("3.03")

    # Exchange charge: ₹2.97 per lakh = 0.0000297
    # Buy: 10,000 * 0.0000297 = 0.297 -> 0.30
    assert rt.entry_leg.exchange_txn_charge == Decimal("0.30")
    # Sell: 10,100 * 0.0000297 = 0.29997 -> 0.30
    assert rt.exit_leg.exchange_txn_charge == Decimal("0.30")

    # SEBI turnover fee: ₹10 per crore = 0.000001
    # Buy: 10,000 * 0.000001 = 0.01
    assert rt.entry_leg.sebi_turnover_charge == Decimal("0.01")
    # Sell: 10,100 * 0.000001 = 0.0101 -> 0.01
    assert rt.exit_leg.sebi_turnover_charge == Decimal("0.01")

    # STT: 0 on Buy, 0.025% on Sell -> 10,100 * 0.00025 = 2.525 -> 2.53
    assert rt.entry_leg.stt == Decimal("0.00")
    assert rt.exit_leg.stt == Decimal("2.53")

    # Stamp duty: 0.003% on Buy -> 10,000 * 0.00003 = 0.30, 0 on Sell
    assert rt.entry_leg.stamp_duty == Decimal("0.30")
    assert rt.exit_leg.stamp_duty == Decimal("0.00")

    # GST (18% on brokerage + exchange + sebi):
    # Buy: (3.00 + 0.30 + 0.01) * 0.18 = 3.31 * 0.18 = 0.5958 -> 0.60
    assert rt.entry_leg.gst == Decimal("0.60")
    # Sell: (3.03 + 0.30 + 0.01) * 0.18 = 3.34 * 0.18 = 0.6012 -> 0.60
    assert rt.exit_leg.gst == Decimal("0.60")

    # Explicit totals:
    # Buy leg: 3.00 + 0.00 + 0.30 + 0.01 + 0.30 + 0.60 = 4.21
    assert rt.entry_leg.explicit_charges == Decimal("4.21")
    # Sell leg: 3.03 + 2.53 + 0.30 + 0.01 + 0.00 + 0.60 = 6.47
    assert rt.exit_leg.explicit_charges == Decimal("6.47")
    # Combined explicit charges = 4.21 + 6.47 = 10.68
    assert rt.explicit_charges == Decimal("10.68")

    # Gross P&L: (505 - 500) * 20 = 100.00
    assert rt.gross_pnl_at_fill == Decimal("100.00")
    # Net P&L: 100.00 - 10.68 = 89.32
    assert rt.net_pnl == Decimal("89.32")

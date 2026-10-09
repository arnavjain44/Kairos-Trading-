"""Kairos Core Package.

Provides shared quantitative trading logic, risk engine rules,
and transaction cost models for research, backtesting, and recommendations.
"""

from kairos_core.costs import (
    BrokerageConfig,
    BrokerageType,
    CostConfig,
    LegCostBreakdown,
    RoundingPolicy,
    RoundTripCostBreakdown,
    TransactionLeg,
    TransactionSide,
    calculate_leg_costs,
    calculate_round_trip_costs,
    estimate_slippage,
    simulate_fill_with_slippage,
)

__version__ = "0.1.0"

__all__ = [
    "__version__",
    "BrokerageConfig",
    "BrokerageType",
    "CostConfig",
    "LegCostBreakdown",
    "RoundingPolicy",
    "RoundTripCostBreakdown",
    "TransactionLeg",
    "TransactionSide",
    "calculate_leg_costs",
    "calculate_round_trip_costs",
    "estimate_slippage",
    "simulate_fill_with_slippage",
]

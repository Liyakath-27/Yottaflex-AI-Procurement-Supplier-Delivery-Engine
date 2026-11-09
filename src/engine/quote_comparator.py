"""
Quote Comparison and Supplier Selection Engine.
"""
from typing import List, Tuple, Dict, Any
from src.models.entities import SupplierQuote, Supplier


def calculate_landed_cost(
    base_amount: float,
    discount_amount: float,
    freight_cost: float,
    tax_duty_amount: float,
    exchange_rate_to_usd: float,
) -> float:
    """Calculate normalized Landed Cost in USD."""
    subtotal = max(0.0, base_amount - discount_amount)
    total_quote_curr = subtotal + freight_cost + tax_duty_amount
    return round(total_quote_curr * exchange_rate_to_usd, 2)


def rank_and_score_quotes(
    quotes: List[SupplierQuote],
    suppliers_by_id: Dict[str, Supplier],
) -> List[SupplierQuote]:
    """
    Ranks quotes by total landed cost and computes a multi-attribute selection score (0-100).
    Cost: 50% weight
    Lead time: 25% weight
    Supplier quality/rating: 25% weight
    """
    if not quotes:
        return []

    # Sort primarily by landed cost
    sorted_by_cost = sorted(quotes, key=lambda q: q.total_landed_cost_usd)
    min_cost = sorted_by_cost[0].total_landed_cost_usd if sorted_by_cost[0].total_landed_cost_usd > 0 else 1.0

    scored_quotes: List[SupplierQuote] = []
    for rank, quote in enumerate(sorted_by_cost, start=1):
        quote.landed_cost_rank = rank
        supplier = suppliers_by_id.get(quote.supplier_id)

        # 1. Cost Score (max 50)
        # Closer to min_cost gives up to 50 pts
        cost_ratio = min_cost / max(quote.total_landed_cost_usd, 1.0)
        cost_score = 50.0 * cost_ratio

        # 2. Lead Time Score (max 25)
        # Baseline ideal lead time is 7 days, max penalty at 45 days
        lead_time = max(1, quote.promised_lead_time_days)
        lead_score = 25.0 * max(0.0, (45.0 - lead_time) / 45.0)

        # 3. Supplier Score (max 25)
        if supplier:
            perf_pts = (supplier.performance_rating / 5.0) * 15.0
            qual_pts = supplier.quality_score * 10.0
            supp_score = perf_pts + qual_pts
        else:
            supp_score = 15.0

        total_score = round(cost_score + lead_score + supp_score, 2)
        quote.selection_score = total_score
        scored_quotes.append(quote)

    return scored_quotes


def generate_award_rationale(
    selected_quote: SupplierQuote,
    cheapest_quote: SupplierQuote,
    supplier: Supplier,
) -> str:
    """Generate auditable rationale for quote selection."""
    if selected_quote.quote_id == cheapest_quote.quote_id:
        return (
            f"Awarded to {supplier.name} as lowest evaluated total landed cost "
            f"(${selected_quote.total_landed_cost_usd:,.2f}) with promised lead time "
            f"of {selected_quote.promised_lead_time_days} days."
        )
    else:
        cost_diff = selected_quote.total_landed_cost_usd - cheapest_quote.total_landed_cost_usd
        diff_pct = (cost_diff / cheapest_quote.total_landed_cost_usd) * 100.0 if cheapest_quote.total_landed_cost_usd > 0 else 0.0
        lead_diff = cheapest_quote.promised_lead_time_days - selected_quote.promised_lead_time_days
        return (
            f"Awarded to {supplier.name} (Selection Score: {selected_quote.selection_score:.1f}) "
            f"over lower bidder due to critical lead time advantage ({lead_diff} days faster) "
            f"and superior quality score ({supplier.quality_score * 100:.1f}%), "
            f"justifying the +{diff_pct:.1f}% landed cost variance."
        )


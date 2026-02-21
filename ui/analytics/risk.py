import math

def risk_score(transactions, wage):
    """
    Behavioral volatility index.
    Higher discretionary ratio + duplicates + negatives increases score.
    """

    total_spend = sum(abs(t["amount"]) for t in transactions)
    discretionary_ratio = total_spend / wage if wage else 0

    negatives = len([t for t in transactions if t["amount"] < 0])
    duplicates = len(transactions) - len(set((t["date"], t["amount"]) for t in transactions))

    score = (
        discretionary_ratio * 40
        + negatives * 15
        + duplicates * 10
    )

    return min(round(score, 2), 100)
def detect_high_risk_behavior(transactions):
    flags = []

    negatives = [t for t in transactions if t["amount"] < 0]
    duplicates = len(transactions) != len(set((t["date"], t["amount"]) for t in transactions))

    if negatives:
        flags.append("Negative transactions detected")
    if duplicates:
        flags.append("Duplicate transaction behavior detected")
    if sum(t["amount"] for t in transactions if t["amount"] > 500) > 2000:
        flags.append("High-value discretionary spending pattern")

    return flags
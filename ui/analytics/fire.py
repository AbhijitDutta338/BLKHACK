def fire_score(corpus, annual_expense):
    """
    FIRE rule: 25x annual expense.
    Returns % progress toward financial independence.
    """
    required = annual_expense * 25
    score = min((corpus / required) * 100, 100)
    return round(score, 2)
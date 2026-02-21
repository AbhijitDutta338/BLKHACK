def retirement_gap(current_age, target_age):
    return target_age - current_age

def early_retirement_estimate(current_age, corpus, annual_expense, rate=0.10):
    required = annual_expense * 25
    if corpus >= required:
        return current_age
    years = 0
    while corpus < required:
        corpus *= (1 + rate)
        years += 1
    return current_age + years
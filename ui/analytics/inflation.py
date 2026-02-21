def inflation_adjust(value, inflation, years):
    return value / ((1 + inflation/100) ** years)
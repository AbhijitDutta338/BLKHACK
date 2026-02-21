from config import RETIREMENT_AGE_DEFAULT

def future_value(amount, current_age, rate, retirement_age=RETIREMENT_AGE_DEFAULT):
    years = retirement_age - current_age
    return amount * ((1 + rate) ** years)
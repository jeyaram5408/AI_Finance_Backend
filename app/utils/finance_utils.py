def compute_health(income: float, savings: float):
    if income <= 0:
        return 0, "No Data"

    savings_rate = (savings / income) * 100
    score = int(max(0, min(100, round(savings_rate))))

    if score >= 85:
        label = "Excellent"
    elif score >= 70:
        label = "Good"
    elif score >= 55:
        label = "Fair"
    elif score >= 35:
        label = "Poor"
    else:
        label = "Critical"

    return score, label

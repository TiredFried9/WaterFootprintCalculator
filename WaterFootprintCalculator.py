
from flask import Flask, render_template, request

app = Flask(__name__)


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/calculate", methods=["POST"])
def calculate():

    try:
        # Read activity amounts
        toilet_flushes = int(request.form["toilet_flushes"])
        shower_minutes = float(request.form["shower_minutes"])
        brushing_minutes = float(request.form["brushing_minutes"])
        laundry_loads = int(request.form["laundry_loads"])
        cooking_times = int(request.form["cooking_times"])
        drinking_refills = int(request.form["drinking_refills"])

        # Read selected water consumption rates
        toilet_rate = float(request.form["toilet_rate"])
        shower_rate = float(request.form["shower_rate"])
        brushing_rate = float(request.form["brushing_rate"])
        laundry_rate = float(request.form["laundry_rate"])
        cooking_rate = float(request.form["cooking_rate"])
        drinking_rate = float(request.form["drinking_rate"])

    except (KeyError, ValueError, OverflowError):
        return "Invalid input. Please return to the calculator.", 400

    # Validate activity amounts
    amounts = [
        toilet_flushes,
        shower_minutes,
        brushing_minutes,
        laundry_loads,
        cooking_times,
        drinking_refills
    ]

    if any(value < 0 or value != value or value == float("inf")
           for value in amounts):
        return "Water usage must be a valid non-negative number.", 400

    # Allowed dropdown values
    allowed_rates = {
        "toilet": [4.8, 6.0, 6.5, 7.5],
        "shower": [6.0, 7.5, 9.5, 12.0],
        "brushing": [0.5, 2.0, 6.0, 10.0],
        "laundry": [40.0, 57.0, 75.0, 100.0],
        "cooking": [15.0, 20.0, 30.0, 40.0],
        "drinking": [0.5, 1.0, 1.5, 2.0]
    }

    selected_rates = {
        "toilet": toilet_rate,
        "shower": shower_rate,
        "brushing": brushing_rate,
        "laundry": laundry_rate,
        "cooking": cooking_rate,
        "drinking": drinking_rate
    }

    for category, rate in selected_rates.items():
        if rate not in allowed_rates[category]:
            return "Invalid water consumption rate selected.", 400

    # Daily calculations
    toilet_daily = toilet_flushes * toilet_rate
    shower_daily = shower_minutes * shower_rate
    brushing_daily = brushing_minutes * brushing_rate

    shower_brushing_daily = shower_daily + brushing_daily

    cooking_daily = cooking_times * cooking_rate
    drinking_daily = drinking_refills * drinking_rate

    # Weekly calculations
    toilet_weekly = toilet_daily * 7
    shower_brushing_weekly = shower_brushing_daily * 7
    laundry_weekly = laundry_loads * laundry_rate
    cooking_weekly = cooking_daily * 7
    drinking_weekly = drinking_daily * 7

    # Total weekly water consumption
    weekly_total = (
        toilet_weekly
        + shower_brushing_weekly
        + laundry_weekly
        + cooking_weekly
        + drinking_weekly
    )

    # Average daily water consumption
    daily_average = weekly_total / 7

    # Metro Vancouver benchmark used in this project
    METRO_AVERAGE = 380

    difference = abs(daily_average - METRO_AVERAGE)

    percentage_difference = (
        difference / METRO_AVERAGE
    ) * 100

    if daily_average < METRO_AVERAGE:
        comparison = "less"

    elif daily_average > METRO_AVERAGE:
        comparison = "more"

    else:
        comparison = "equal"

    # Send results to results.html
    return render_template(
        "results.html",

        toilet=round(toilet_weekly, 1),
        shower_brushing=round(shower_brushing_weekly, 1),
        laundry=round(laundry_weekly, 1),
        cooking=round(cooking_weekly, 1),
        drinking=round(drinking_weekly, 1),

        weekly_total=round(weekly_total, 1),
        daily_average=round(daily_average, 1),

        metro_average=METRO_AVERAGE,
        comparison=comparison,
        difference=round(difference, 1),
        percentage_difference=round(percentage_difference, 1)
    )


if __name__ == "__main__":
    app.run(debug=True)


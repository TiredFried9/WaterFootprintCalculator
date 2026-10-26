
from flask import Flask, render_template, request, send_file
from io import BytesIO
from datetime import date
import math

from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer,
    Table, TableStyle, Image
)
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.utils import ImageReader

app = Flask(__name__)

METRO_AVERAGE = 380

RATES = {
    "toilet": [4.8, 6.0, 6.5, 7.5],
    "shower": [6.0, 7.5, 9.5, 12.0],
    "brushing": [0.5, 2.0, 6.0, 10.0],
    "laundry": [40, 57, 75, 100],
    "cooking": [15, 20, 30, 40],
    "drinking": [0.5, 1.0, 1.5, 2.0]
}

ACTIVITIES = {
    "toilet": ("toilet_flushes", "toilet_rate", 7),
    "shower": ("shower_minutes", "shower_rate", 7),
    "brushing": ("brushing_minutes", "brushing_rate", 7),
    "laundry": ("laundry_loads", "laundry_rate", 1),
    "cooking": ("cooking_times", "cooking_rate", 7),
    "drinking": ("drinking_refills", "drinking_rate", 7)
}

TIPS = [
    "Take shorter showers and use a water-efficient showerhead.",
    "Turn off taps while brushing your teeth or shaving.",
    "Use low-flow or dual-flush toilets.",
    "Wash full loads of laundry.",
    "Run full dishwashers or wash dishes in a filled sink.",
    "Repair leaking faucets, toilets and pipes.",
    "Collect rainwater for gardening where permitted.",
    "Reduce outdoor watering and follow local restrictions."
]


@app.route("/")
def home():
    return render_template("index.html", rates=RATES)


@app.route("/calculate", methods=["POST"])
def calculate():
    try:
        usage = {}

        for category, (count_field, rate_field, days) in ACTIVITIES.items():
            count = float(request.form[count_field])
            rate = float(request.form[rate_field])

            if not math.isfinite(count) or count < 0 or count > 10000:
                raise ValueError("Invalid usage")

            if rate not in RATES[category]:
                raise ValueError("Invalid rate")

            usage[category] = round(count * rate * days, 2)

        shower_brushing = round(
            usage["shower"] + usage["brushing"], 2
        )

        weekly_total = round(sum(usage.values()), 2)
        daily_average = round(weekly_total / 7, 2)

        difference = round(abs(daily_average - METRO_AVERAGE), 2)

        percentage_difference = round(
            difference / METRO_AVERAGE * 100, 1
        )

        if daily_average < METRO_AVERAGE:
            comparison = "less"
        elif daily_average > METRO_AVERAGE:
            comparison = "more"
        else:
            comparison = "equal"

        return render_template(
            "results.html",
            toilet=usage["toilet"],
            shower_brushing=shower_brushing,
            laundry=usage["laundry"],
            cooking=usage["cooking"],
            drinking=usage["drinking"],
            weekly_total=weekly_total,
            daily_average=daily_average,
            metro_average=METRO_AVERAGE,
            difference=difference,
            percentage_difference=percentage_difference,
            comparison=comparison,
            tips=TIPS
        )

    except (KeyError, ValueError, TypeError, OverflowError):
        return "Please enter valid, non-negative water usage values.", 400


@app.route("/download-report", methods=["POST"])
def download_report():
    try:
        data = request.get_json()
        if not isinstance(data, dict):
            raise ValueError("Invalid report")

        latest = data.get("latest", {})
        history = data.get("history", [])

        if not isinstance(latest, dict):
            raise ValueError("Invalid results")

        if not isinstance(history, list) or len(history) > 260:
            raise ValueError("Invalid history")

        category_names = [
            ("toilet", "Toilet"),
            ("shower_brushing", "Shower and Brushing"),
            ("laundry", "Laundry"),
            ("cooking", "Cooking and Dishwashing"),
            ("drinking", "Drinking")
        ]

        breakdown = []

        for key, label in category_names:
            amount = float(latest[key])
            if not math.isfinite(amount) or not 0 <= amount <= 1000000:
                raise ValueError("Invalid amount")
            breakdown.append((label, amount))

        weekly_total = round(
            sum(amount for _, amount in breakdown), 2
        )
        daily_average = weekly_total / 7

        cleaned_history = []

        for entry in history:
            week = str(entry["week"])
            date.fromisoformat(week)

            total = float(entry["total"])

            if not math.isfinite(total) or not 0 <= total <= 1000000:
                raise ValueError("Invalid weekly total")

            cleaned_history.append((week, total))

        cleaned_history.sort()

    except (KeyError, ValueError, TypeError, OverflowError):
        return {"error": "Invalid report data"}, 400

    buffer = BytesIO()

    document = SimpleDocTemplate(
        buffer,
        pagesize=(612, 792),
        leftMargin=45,
        rightMargin=45,
        topMargin=45,
        bottomMargin=45
    )

    styles = getSampleStyleSheet()
    elements = []

    elements.append(
        Paragraph("H2O OH NO! Water Usage Report", styles["Title"])
    )
    elements.append(Spacer(1, 15))

    elements.append(
        Paragraph(
            f"Report generated: {date.today().isoformat()}",
            styles["Normal"]
        )
    )

    elements.append(Spacer(1, 20))

    elements.append(
        Paragraph("Your Water Consumption", styles["Heading2"])
    )

    elements.append(
        Paragraph(
            f"Weekly water usage: {weekly_total:,.2f} L",
            styles["Normal"]
        )
    )

    elements.append(
        Paragraph(
            f"Daily average: {daily_average:,.2f} L/day",
            styles["Normal"]
        )
    )

    elements.append(
        Paragraph(
            f"Project comparison benchmark: {METRO_AVERAGE} L/person/day",
            styles["Normal"]
        )
    )

    elements.append(Spacer(1, 15))

    table_data = [["Activity", "Litres per week"]]

    for label, amount in breakdown:
        table_data.append([label, f"{amount:,.2f}"])

    table = Table(table_data, colWidths=[320, 190], repeatRows=1)

    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#dceff5")),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("PADDING", (0, 0), (-1, -1), 8)
    ]))

    elements.append(table)
    elements.append(Spacer(1, 20))

    elements.append(
        Paragraph("Weekly Water Usage History", styles["Heading2"])
    )

    if cleaned_history:
        history_data = [
            ["Week Starting", "Water Usage (L)"]
        ]

        for week, total in cleaned_history:
            history_data.append([week, f"{total:,.2f}"])

        history_table = Table(
            history_data,
            colWidths=[320, 190],
            repeatRows=1
        )

        history_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#dceff5")),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("PADDING", (0, 0), (-1, -1), 8)
        ]))

        elements.append(history_table)

        if len(cleaned_history) >= 2:
            first = cleaned_history[0][1]
            last = cleaned_history[-1][1]

            saved = first - last
            percentage = saved / first * 100 if first > 0 else 0

            elements.append(Spacer(1, 12))

            elements.append(
                Paragraph(
                    f"Change from first to latest week: "
                    f"{saved:+,.2f} L saved ({percentage:+.1f}%). "
                    "Positive savings indicate reduced consumption.",
                    styles["Normal"]
                )
            )

    else:
        elements.append(
            Paragraph(
                "No weekly usage history has been saved.",
                styles["Normal"]
            )
        )

    elements.append(Spacer(1, 20))

    elements.append(
        Paragraph("Water Conservation Recommendations", styles["Heading2"])
    )

    for number, tip in enumerate(TIPS, start=1):
        elements.append(
            Paragraph(f"{number}. {tip}", styles["Normal"])
        )
        elements.append(Spacer(1, 7))

    elements.append(Spacer(1, 15))

    elements.append(
        Paragraph(
            "Note: These calculations estimate selected household "
            "activities and do not represent a complete household "
            "or indirect water footprint.",
            styles["Italic"]
        )
    )

    document.build(elements)

    buffer.seek(0)

    return send_file(
        buffer,
        mimetype="application/pdf",
        as_attachment=True,
        download_name="H2O_OH_NO_Water_Report.pdf"
    )


if __name__ == "__main__":
    app.run(debug=True)


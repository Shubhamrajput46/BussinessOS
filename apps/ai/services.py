from datetime import timedelta
from decimal import Decimal
from apps.ai.models import SalesForecast
import pandas as pd
from django.db.models import Sum
from sklearn.linear_model import LinearRegression

from apps.orders.models import Order


def get_historical_sales(organisation):
    sales = (
        Order.objects
        .filter(organisation=organisation)
        .exclude(status=Order.Status.CANCELLED)
        .values("created_at__date")
        .annotate(total_sales=Sum("total_amount"))
        .order_by("created_at__date")
    )

    data = [
        {
            "date": item["created_at__date"],
            "sales": item["total_sales"] or Decimal("0.00"),
        }
        for item in sales
    ]

    return pd.DataFrame(data)


def prepare_sales_data(organisation):
    df = get_historical_sales(organisation)

    if df.empty:
        return df

    df["date"] = pd.to_datetime(df["date"])
    df["sales"] = df["sales"].astype(float)

    return df


def predict_next_day_sales(organisation):
    df = prepare_sales_data(organisation)

    if len(df) < 2:
        return None

    df["day_number"] = range(len(df))

    X = df[["day_number"]]
    y = df["sales"]

    model = LinearRegression()
    model.fit(X, y)

    next_day_number = len(df)

    prediction = model.predict(
        pd.DataFrame({"day_number": [next_day_number]})
    )[0]

    return max(0, round(float(prediction), 2))

def generate_forecast(organisation, days=7):
    """Predict daily sales for the next `days` days and store them as SalesForecast rows.

    Uses a simple linear-regression trend over the organisation's daily
    sales history. Returns the list of created SalesForecast objects
    (empty when there is not enough history yet).
    """
    from datetime import date

    df = prepare_sales_data(organisation)
    if len(df) < 2:
        return []

    days = max(1, min(int(days), 30))
    df = df.sort_values("date").reset_index(drop=True)
    df["day_number"] = range(len(df))

    model = LinearRegression().fit(df[["day_number"]], df["sales"])
    last_date = max(df["date"].max().date(), date.today())

    # Replace future forecasts instead of piling up duplicates.
    SalesForecast.objects.filter(organisation=organisation, forecast_date__gt=date.today()).delete()
    SalesForecast.objects.filter(organisation=organisation, forecast_date=last_date + timedelta(days=1)).delete()

    created = []
    for offset in range(1, days + 1):
        forecast_date = last_date + timedelta(days=offset)
        value = float(model.predict(pd.DataFrame({"day_number": [len(df) - 1 + offset]}))[0])
        created.append(
            SalesForecast.objects.create(
                organisation=organisation,
                forecast_date=forecast_date,
                predicted_sales=Decimal(str(max(0, round(value, 2)))),
            )
        )
    return created

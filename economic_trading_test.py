from datetime import date, timedelta
import tradingeconomics as te

def get_calendar_with_actuals(api_key, days=30):
    """
    Fetches TradingEconomics calendar events with Actual values.
    
    Args:
        api_key (str): Your TE API key in format 'username:password'.
        days (int): Number of past days to fetch events for (default 30).

    Returns:
        List[dict]: Calendar events with Actuals, sorted by importance.
    """
    # Login to TradingEconomics
    te.login(api_key)

    # Define date range
    today = date.today()
    past_date = today - timedelta(days=days)

    # Fetch all calendar events
    all_events = te.getCalendarData()

    # Filter for events with Actual reported and within the date range
    past_events_with_actuals = [
        e for e in all_events
        if e['Actual'] and past_date.isoformat() <= e['Date'][:10] <= today.isoformat()
    ]

    # Sort by Importance (1 = low, 3 = high)
    past_events_with_actuals.sort(key=lambda x: x.get('Importance', 1), reverse=True)

    return past_events_with_actuals


# ------------------------
# Example usage
# ------------------------
if __name__ == "__main__":
    api_key = 'f7a1befaf5b9488:4gdhg1lwll38gqh'  # Replace with your TE key
    events = get_calendar_with_actuals(api_key, days=90)

    for e in events[:50]:  # Limit to top 50 events
        print(f"{e['Date']}: {e['Country']} - {e['Event']} (Actual: {e['Actual']}, Forecast: {e.get('Forecast')})")

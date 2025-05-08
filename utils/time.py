from datetime import datetime, timedelta

def keepa_minutes_to_utc(minutes_since_2011):
    base_date = datetime(2011, 1, 1)
    return base_date + timedelta(minutes=minutes_since_2011)

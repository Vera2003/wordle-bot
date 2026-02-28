from datetime import datetime, time, timedelta, timezone

#TODO уточнить правильно ли время получаем
def get_seconds_until_midnight() -> int:
    """Получить количество секунд до следующей полуночи (UTC)"""
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    midnight = datetime.combine(now.date(), time.min) + timedelta(days=1)
    return int((midnight - now).total_seconds())


def get_today_str() -> str:
    """Получить сегодняшнюю дату в формате YYYY-MM-DD"""
    return datetime.now(timezone.utc).replace(tzinfo=None).strftime("%Y-%m-%d")


def get_today_date():
    """Получить сегодняшнюю дату как date объект"""
    return datetime.now(timezone.utc).replace(tzinfo=None).date()
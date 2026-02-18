from datetime import datetime, time, timedelta


def get_seconds_until_midnight() -> int:
    """Получить количество секунд до следующей полуночи (UTC)"""
    now = datetime.utcnow()
    midnight = datetime.combine(now.date(), time.min) + timedelta(days=1)
    return int((midnight - now).total_seconds())


def get_today_str() -> str:
    """Получить сегодняшнюю дату в формате YYYY-MM-DD"""
    return datetime.utcnow().strftime("%Y-%m-%d")


def get_today_date():
    """Получить сегодняшнюю дату как date объект"""
    return datetime.utcnow().date()
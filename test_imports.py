
print("🔍 Проверка импортов...")

try:
    import sys
    print(f"✅ Python version: {sys.version}")
except Exception as e:
    print(f"❌ Python: {e}")
    sys.exit(1)

try:
    from pathlib import Path
    print(f"✅ pathlib работает")
except Exception as e:
    print(f"❌ pathlib: {e}")

try:
    # Добавляем путь к приложению
    sys.path.insert(0, str(Path(__file__).parent))
    print(f"✅ Path настроен: {sys.path[0]}")
except Exception as e:
    print(f"❌ Path: {e}")

try:
    from src.core.config import get_settings
    get_settings.cache_clear()
    # from pytest import MonkeyPatch
    # monkeypatch.setenv("POSTGRES_DB", "test_db")
    settings = get_settings()
    print(f"✅ Config загружен")
    print(f"   BOT_TOKEN: {settings.bot_token[:10]}...")
    print(f"   POSTGRES_DB: {settings.postgres_db}")
except Exception as e:
    print(f"❌ Config: {e}")
    import traceback
    traceback.print_exc()

print("\n🎯 Проверка завершена")

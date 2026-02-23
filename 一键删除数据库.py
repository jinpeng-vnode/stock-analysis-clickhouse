import clickhouse_connect
import os

# =============================
# One-click Drop ClickHouse DB
# =============================
# Safe defaults:
DB_HOST = os.getenv('CH_HOST', 'localhost')
DB_PORT = int(os.getenv('CH_PORT', '8123'))
DB_USER = os.getenv('CH_USER', 'default')
DB_PASS = os.getenv('CH_PASS', '')
DB_NAME = os.getenv('CH_DB', 'stock_analysis')

# Whether to drop the database itself after dropping objects
DROP_DATABASE = False  # set to False to only drop objects inside the DB


def drop_objects(client, db: str) -> None:
    print(f"\n📋 Target database: {db}")

    # Switch DB (CREATE if not exists is not required here)
    client.command(f"CREATE DATABASE IF NOT EXISTS {db}")
    client.command(f"USE {db}")

    # 1) Drop materialized views first (they depend on tables/views)
    mviews = [
        'stock_daily_k_i_from_k_mv',
        'stock_daily_k_i_from_i_mv',
        'stock_daily_k_dedup_mv',
        'stock_daily_i_dedup_mv',
    ]
    for mv in mviews:
        try:
            client.command(f"DROP MATERIALIZED VIEW IF EXISTS {mv}")
            print(f"✅ Dropped MV: {mv}")
        except Exception as e:
            print(f"⚠️ Skip MV {mv}: {e}")

    # 2) Drop normal views
    views = [
        'version_conflict_check',
        'stock_daily_k_read',
        'stock_daily_i_read',
    ]
    for v in views:
        try:
            client.command(f"DROP VIEW IF EXISTS {v}")
            print(f"✅ Dropped VIEW: {v}")
        except Exception as e:
            print(f"⚠️ Skip VIEW {v}: {e}")

    # 3) Drop tables (children first)
    tables = [
        'stock_daily_k_i_read',
        'stock_daily_k_agg',
        'stock_daily_i_agg',
        'stock_daily_k_write',
        'stock_daily_i_write',
        'stock_info',
    ]
    for t in tables:
        try:
            client.command(f"DROP TABLE IF EXISTS {t} SYNC")
            print(f"✅ Dropped TABLE: {t}")
        except Exception as e:
            print(f"⚠️ Skip TABLE {t}: {e}")


def main():
    print("🚨 One-click Drop ClickHouse Database Script")
    print(f"Connecting to {DB_HOST}:{DB_PORT} as {DB_USER} ...")

    client = clickhouse_connect.get_client(
        host=DB_HOST,
        port=DB_PORT,
        username=DB_USER,
        password=DB_PASS,
        database='default',  # start from default
    )

    print("✅ Connected")

    # Drop objects first
    drop_objects(client, DB_NAME)

    # Optionally drop the database itself
    if DROP_DATABASE:
        try:
            client.command(f"DROP DATABASE IF EXISTS {DB_NAME} SYNC")
            print(f"🗑️ Dropped DATABASE: {DB_NAME}")
        except Exception as e:
            print(f"⚠️ Could not drop database {DB_NAME}: {e}")

    client.close()
    print("\n🎉 Done.")


if __name__ == '__main__':
    main()

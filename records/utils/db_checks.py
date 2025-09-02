from django.db import connection

def has_table(table_name: str) -> bool:
    try:
        with connection.cursor() as c:
            c.execute(
                "SELECT 1 FROM information_schema.tables WHERE table_name=%s OR table_name=%s",
                [table_name, table_name.split(".")[-1]],
            )
            return c.fetchone() is not None
    except Exception:
        return False

def has_field(table_name: str, column: str) -> bool:
    try:
        with connection.cursor() as c:
            c.execute(
                "SELECT 1 FROM information_schema.columns WHERE table_name=%s AND column_name=%s",
                [table_name, column],
            )
            return c.fetchone() is not None
    except Exception:
        return False

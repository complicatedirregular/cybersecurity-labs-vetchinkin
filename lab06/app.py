import sqlite3

from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Generator, Optional
from flask import Flask, render_template, request, url_for

# ─────────────────────────────────────────────────────────────
# Конфігурація
# ─────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class StudentInfo:
    """Інформація про студента."""

    name: str = "Тарас Шевченко"
    birth_date: str = "09.03.1814"
    ticket: str = "FF00000000"


STUDENT = StudentInfo()
DB_PATH = Path(__file__).parent / "lab.db"
PAYLOAD_HINT = "' OR '1'='1"

app = Flask(__name__)


# ─────────────────────────────────────────────────────────────
# База даних
# ─────────────────────────────────────────────────────────────


@contextmanager
def get_db() -> Generator[sqlite3.Connection, None, None]:
    """Контекстний менеджер для з'єднання з БД."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def init_db() -> None:
    """Ініціалізує БД: створює таблицю та додає тестові дані."""
    with get_db() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                birth_date TEXT,
                student_ticket TEXT,
                email TEXT
            )
            """
        )

        if conn.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0:
            test_data = [
                (STUDENT.name, STUDENT.birth_date, STUDENT.ticket, "student@example.com"),
                ("Андрій Коваленко", "01.01.1995", "AA0000001", "andrii@example.com"),
                ("Оксана Мельник", "02.02.1992", "BB0000002", "oksana@example.com"),
                ("Тарас Ткачук", "03.03.1993", "CC0000003", "taras@example.com"),
            ]
            conn.executemany(
                "INSERT INTO users (name, birth_date, student_ticket, email) VALUES (?, ?, ?, ?)",
                test_data,
            )
            conn.commit()


def execute_query(sql: str, params: Optional[tuple] = None) -> list[tuple]:
    """Виконує SQL-запит та повертає результати."""
    with get_db() as conn:
        cursor = conn.execute(sql, params or ())
        return [tuple(row) for row in cursor.fetchall()]


# ─────────────────────────────────────────────────────────────
# Допоміжні функції
# ─────────────────────────────────────────────────────────────


def get_base_context(**extras) -> dict:
    """Базовий контекст для всіх шаблонів."""
    return {
        "student_name": STUDENT.name,
        "birth_date": STUDENT.birth_date,
        "student_ticket": STUDENT.ticket,
        "payload_hint": PAYLOAD_HINT,
        **extras,
    }


# ─────────────────────────────────────────────────────────────
# Маршрути
# ─────────────────────────────────────────────────────────────


@app.route("/")
def home():
    """Головна сторінка з вибором демонстрації."""
    return render_template("home.html", **get_base_context(page_title="SQL-ін'єкція: полігон"))


@app.route("/vulnerable", methods=["GET", "POST"])
def vulnerable():
    """
    Уразливий пошук — демонстрація SQL-ін'єкції.

    ⚠️ УВАГА: Цей код навмисно вразливий для освітніх цілей!
    Ніколи не використовуйте конкатенацію рядків у реальних проектах.
    """
    query = request.form.get("query", "") if request.method == "POST" else ""
    results: Optional[list[tuple]] = None
    sql_template = "SELECT id, name, birth_date, student_ticket, email FROM users WHERE name LIKE '%{q}%' OR student_ticket LIKE '%{q}%'"

    executed_sql = sql_template.format(q="...")

    if request.method == "POST" and query:
        # ⚠️ НЕБЕЗПЕЧНО: пряма підстановка без екранування
        executed_sql = sql_template.format(q=query)
        try:
            results = execute_query(executed_sql)
        except sqlite3.Error as e:
            results = []
            executed_sql += f"  -- ПОМИЛКА: {e}"

    return render_template(
        "search.html",
        **get_base_context(
            page_title="Небезпечний пошук",
            variant="danger",
            heading="Уразливий пошук",
            subtitle="Конкатенація рядків",
            description="Запит формується через пряме вставлення даних користувача. Це дозволяє змінити логіку SQL.",
            action_url=url_for("vulnerable"),
            query=query,
            results=results,
            executed_sql=executed_sql,
        ),
    )


@app.route("/secure", methods=["GET", "POST"])
def secure():
    """
    Безпечний пошук — демонстрація параметризованих запитів.

    ✅ Правильний підхід: параметри передаються окремо від SQL-коду.
    """
    query = request.form.get("query", "") if request.method == "POST" else ""
    results: Optional[list[tuple]] = None

    sql = "SELECT id, name, birth_date, student_ticket, email FROM users WHERE name LIKE ? OR student_ticket LIKE ?"
    executed_sql = f"{sql}  -- params: ('%...%', '%...%')"

    if request.method == "POST" and query:
        params = (f"%{query}%", f"%{query}%")
        executed_sql = f"{sql}  -- params: {params}"
        results = execute_query(sql, params)

    return render_template(
        "search.html",
        **get_base_context(
            page_title="Безпечний пошук",
            variant="safe",
            heading="Безпечний пошук",
            subtitle="Параметризовані запити",
            description="Параметри ізольовані від SQL-коду, тому ін'єкція неможлива.",
            action_url=url_for("secure"),
            query=query,
            results=results,
            executed_sql=executed_sql,
        ),
    )


# ─────────────────────────────────────────────────────────────
# Запуск
# ─────────────────────────────────────────────────────────────

init_db()

if __name__ == "__main__":
    app.run(debug=False)

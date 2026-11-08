"""SQL generation prompts scored by EXECUTION, not pattern matching.

This is the most objective family in the skill: the generated query is run against a
fresh in-memory SQLite database seeded with known rows, and the result set is compared
to the pinned expected answer. No keyword guessing — the query is either right or it
is not.

Safety: each call gets its own :memory: database that is discarded immediately. Only a
single leading SELECT/WITH statement is executed (via execute(), not executescript(), so
stacked statements fail), and an authorizer denies ATTACH so nothing can reach the disk.

Scoring gives partial credit so a near-miss is distinguishable from nonsense:
  parsed as SELECT / executes / right column count / right row count / exact match.
"""
import re
import sqlite3

SCHEMA = """CREATE TABLE employees (
  id INTEGER PRIMARY KEY, name TEXT, dept TEXT,
  salary INTEGER, manager_id INTEGER, hired TEXT
);
CREATE TABLE sales (
  id INTEGER PRIMARY KEY, employee_id INTEGER, amount REAL, closed_on TEXT
);
INSERT INTO employees VALUES
  (1,'Ada','Eng',150000,NULL,'2019-01-15'),
  (2,'Grace','Eng',120000,1,'2020-03-01'),
  (3,'Linus','Eng',130000,1,'2021-07-20'),
  (4,'Barbara','Sales',90000,NULL,'2018-05-10'),
  (5,'Alan','Sales',95000,4,'2022-02-01'),
  (6,'Katherine','Ops',85000,NULL,'2020-11-30');
INSERT INTO sales VALUES
  (1,5,5000.0,'2026-01-10'),
  (2,5,7500.0,'2026-02-11'),
  (3,4,3000.0,'2026-01-22'),
  (4,2,1000.0,'2026-03-05');"""

_SCHEMA_FOR_PROMPT = """employees(id, name, dept, salary, manager_id, hired)
sales(id, employee_id, amount, closed_on)

manager_id references employees.id and is NULL for people with no manager.
sales.employee_id references employees.id."""

_ASK = "Return only the SQL query. No explanation, no markdown fences."

PROMPTS = [
    ("group_by_order",
     f"Given this SQLite schema:\n\n{_SCHEMA_FOR_PROMPT}\n\n"
     f"Write a query returning each department and its total salary, highest total "
     f"first. Return exactly two columns: dept, total. {_ASK}"),
    ("left_join_zero",
     f"Given this SQLite schema:\n\n{_SCHEMA_FOR_PROMPT}\n\n"
     f"Write a query returning every employee's name and their total sales amount. "
     f"Employees with no sales must appear with 0, not be omitted. Return exactly two "
     f"columns: name, total_sales. {_ASK}"),
    ("self_join",
     f"Given this SQLite schema:\n\n{_SCHEMA_FOR_PROMPT}\n\n"
     f"Write a query returning the names of employees who earn more than their own "
     f"manager. Return exactly one column: name. {_ASK}"),
    ("top_per_group",
     f"Given this SQLite schema:\n\n{_SCHEMA_FOR_PROMPT}\n\n"
     f"Write a query returning the highest-paid employee in each department. Return "
     f"exactly three columns: dept, name, salary. {_ASK}"),
]

# Pinned expected result sets. ordered=True only where the prompt demands a sort.
EXPECTED = {
    "group_by_order": ([("Eng", 400000), ("Sales", 185000), ("Ops", 85000)], True),
    "left_join_zero": ([("Ada", 0), ("Grace", 1000), ("Linus", 0),
                        ("Barbara", 3000), ("Alan", 12500), ("Katherine", 0)], False),
    "self_join": ([("Alan",)], False),
    "top_per_group": ([("Eng", "Ada", 150000), ("Sales", "Alan", 95000),
                       ("Ops", "Katherine", 85000)], False),
}


def extract_sql(text):
    """Pull the query out of a fenced block, or fall back to the first SELECT/WITH."""
    m = re.search(r'```(?:sql)?\s*(.*?)```', text, re.DOTALL | re.IGNORECASE)
    body = m.group(1) if m else text
    m = re.search(r'\b(WITH|SELECT)\b.*', body, re.DOTALL | re.IGNORECASE)
    if not m:
        return None
    sql = m.group(0).strip()
    sql = sql.split(";")[0].strip()          # single statement only
    return sql or None


def _deny_attach(action, *_):
    return sqlite3.DENY if action == sqlite3.SQLITE_ATTACH else sqlite3.SQLITE_OK


def run_query(sql):
    """Execute against a throwaway in-memory DB. Returns (rows, error)."""
    conn = sqlite3.connect(":memory:")
    try:
        conn.executescript(SCHEMA)
        conn.set_authorizer(_deny_attach)
        return conn.execute(sql).fetchall(), None
    except Exception as e:                    # any sqlite error is a scoring signal
        return None, str(e)
    finally:
        conn.close()


def _norm(rows):
    """Compare by value, not by type or column name: 1000 == 1000.0, whitespace ignored."""
    out = []
    for r in rows:
        out.append(tuple(
            round(float(v), 2) if isinstance(v, (int, float)) and not isinstance(v, bool)
            else (v.strip() if isinstance(v, str) else v)
            for v in r))
    return out


def _score_sql(text, key):
    expected, ordered = EXPECTED[key]
    sql = extract_sql(text)
    if not sql:
        return 0.0, ["no SELECT found in response"]

    rows, err = run_query(sql)
    if rows is None:
        return 0.2, [f"ok: parsed as SELECT", f"no: executes ({err[:60]})"]

    got, want = _norm(rows), _norm(expected)
    if not ordered:
        got, want = sorted(got, key=repr), sorted(want, key=repr)

    checks = [
        ("parsed as SELECT", True),
        ("executes", True),
        ("column count", bool(rows) and len(rows[0]) == len(expected[0])),
        ("row count", len(rows) == len(expected)),
        ("exact result match", got == want),
    ]
    score = sum(0.2 for _, p in checks if p)
    return min(round(score, 2), 1.0), [f"{'ok' if p else 'no'}: {n}" for n, p in checks]


SCORERS = {k: (lambda t, _k=k: _score_sql(t, _k)) for k in EXPECTED}

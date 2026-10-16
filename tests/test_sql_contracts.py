from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SQL_ROOT = PROJECT_ROOT / "include" / "sql"


def test_sql_files_do_not_use_select_star():
    offenders = []
    for sql_file in SQL_ROOT.glob("**/*.sql"):
        normalized_sql = " ".join(sql_file.read_text().lower().split())
        if "select *" in normalized_sql:
            offenders.append(str(sql_file.relative_to(PROJECT_ROOT)))

    assert offenders == []


def test_all_medallion_layers_have_sql_files():
    for layer_name in ("bronze", "silver", "gold"):
        sql_files = list((SQL_ROOT / layer_name).glob("*.sql"))
        assert sql_files, f"{layer_name} has no SQL files"

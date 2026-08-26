from backend.db import DB


def test_database_round_trip(tmp_path):
    path = tmp_path / "db.json"
    database = DB(filename=path)
    database["answer"] = 42
    database.save()

    restored = DB(filename=path)
    restored.load()

    assert restored["answer"] == 42

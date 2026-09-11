"""
Unit tests for postgres-lite database.
"""
import unittest
from postgres import (
    Database, Table, Column, BPlusTree, BPlusTreeNode,
    Row, IsolationLevel
)


class TestBPlusTree(unittest.TestCase):
    def setUp(self):
        self.tree = BPlusTree(order=4)

    def test_insert_and_search(self):
        self.tree.insert(10, "a")
        self.tree.insert(20, "b")
        self.tree.insert(5, "c")
        self.assertEqual(self.tree.search(10), "a")
        self.assertEqual(self.tree.search(20), "b")
        self.assertEqual(self.tree.search(5), "c")
        self.assertIsNone(self.tree.search(999))

    def test_range_search(self):
        for i in range(1, 11):
            self.tree.insert(i, f"val{i}")
        results = self.tree.range_search(3, 7)
        keys = [k for k, v in results]
        self.assertIn(3, keys)
        self.assertIn(7, keys)
        self.assertNotIn(2, keys)
        self.assertNotIn(8, keys)

    def test_tree_split(self):
        for i in range(20):
            self.tree.insert(i, f"val{i}")
        for i in range(20):
            self.assertEqual(self.tree.search(i), f"val{i}")


class TestColumn(unittest.TestCase):
    def test_column_creation(self):
        col = Column("id", "INT", primary_key=True)
        self.assertEqual(col.name, "id")
        self.assertEqual(col.col_type, "INT")
        self.assertTrue(col.primary_key)

    def test_column_with_default(self):
        col = Column("status", "TEXT", default="active")
        self.assertEqual(col.default, "active")


class TestTable(unittest.TestCase):
    def setUp(self):
        self.table = Table("users", [
            Column("id", "INT", primary_key=True),
            Column("name", "TEXT", nullable=False),
            Column("age", "INT", nullable=True, default=0),
        ])

    def test_insert(self):
        row_id = self.table.insert({"id": 1, "name": "Alice", "age": 30})
        self.assertEqual(row_id, 0)
        self.assertEqual(len(self.table.rows), 1)
        self.assertEqual(self.table.rows[0].values["name"], "Alice")

    def test_insert_with_defaults(self):
        row_id = self.table.insert({"id": 2, "name": "Bob"})
        self.assertEqual(self.table.rows[row_id].values["age"], 0)

    def test_update(self):
        row_id = self.table.insert({"id": 1, "name": "Alice", "age": 30})
        self.table.update(row_id, {"age": 31})
        self.assertEqual(self.table.rows[row_id].values["age"], 31)
        self.assertEqual(self.table.rows[row_id].version, 1)

    def test_delete(self):
        row_id = self.table.insert({"id": 1, "name": "Alice", "age": 30})
        self.table.delete(row_id)
        self.assertTrue(self.table.rows[row_id].deleted)
        self.assertEqual(len(self.table.scan()), 0)

    def test_scan(self):
        self.table.insert({"id": 1, "name": "Alice"})
        self.table.insert({"id": 2, "name": "Bob"})
        self.table.insert({"id": 3, "name": "Charlie"})
        results = self.table.scan()
        self.assertEqual(len(results), 3)

    def test_scan_skips_deleted(self):
        row_id = self.table.insert({"id": 1, "name": "Alice"})
        self.table.insert({"id": 2, "name": "Bob"})
        self.table.delete(row_id)
        results = self.table.scan()
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0][1].values["name"], "Bob")

    def test_create_index(self):
        self.table.insert({"id": 1, "name": "Alice", "age": 30})
        self.table.insert({"id": 2, "name": "Bob", "age": 25})
        self.table.create_index("name")
        self.assertIn("name", self.table.indexes)


class TestDatabase(unittest.TestCase):
    def setUp(self):
        self.db = Database()
        self.db.create_table("users", [
            Column("id", "INT", primary_key=True),
            Column("name", "TEXT", nullable=False),
            Column("age", "INT", nullable=True, default=0),
        ])

    def test_create_table(self):
        self.assertIn("users", self.db.tables)

    def test_insert(self):
        row_id = self.db.insert("users", {"id": 1, "name": "Alice", "age": 30})
        self.assertIsNotNone(row_id)

    def test_select_all(self):
        self.db.insert("users", {"id": 1, "name": "Alice", "age": 30})
        self.db.insert("users", {"id": 2, "name": "Bob", "age": 25})
        results = self.db.select("users")
        self.assertEqual(len(results), 2)

    def test_select_with_where(self):
        self.db.insert("users", {"id": 1, "name": "Alice", "age": 30})
        self.db.insert("users", {"id": 2, "name": "Bob", "age": 25})
        results = self.db.select("users", where={"name": "Alice"})
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["age"], 30)

    def test_update(self):
        self.db.insert("users", {"id": 1, "name": "Alice", "age": 30})
        self.db.update("users", {"age": 31}, {"name": "Alice"})
        results = self.db.select("users", where={"name": "Alice"})
        self.assertEqual(results[0]["age"], 31)

    def test_delete(self):
        self.db.insert("users", {"id": 1, "name": "Alice"})
        self.db.insert("users", {"id": 2, "name": "Bob"})
        self.db.delete("users", {"name": "Alice"})
        results = self.db.select("users")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["name"], "Bob")

    def test_transaction(self):
        tx = self.db.begin_transaction()
        self.db.insert("users", {"id": 1, "name": "Alice"})
        self.db.commit(tx)
        results = self.db.select("users")
        self.assertEqual(len(results), 1)

    def test_multiple_tables(self):
        self.db.create_table("posts", [
            Column("id", "INT", primary_key=True),
            Column("title", "TEXT"),
        ])
        self.db.insert("users", {"id": 1, "name": "Alice"})
        self.db.insert("posts", {"id": 1, "title": "Hello"})
        users = self.db.select("users")
        posts = self.db.select("posts")
        self.assertEqual(len(users), 1)
        self.assertEqual(len(posts), 1)


class TestIsolationLevels(unittest.TestCase):
    def setUp(self):
        self.db = Database()

    def test_isolation_level_read_committed(self):
        tx = self.db.begin_transaction(IsolationLevel.READ_COMMITTED)
        self.assertEqual(self.db.transactions[tx]["isolation"], IsolationLevel.READ_COMMITTED)

    def test_isolation_level_serializable(self):
        tx = self.db.begin_transaction(IsolationLevel.SERIALIZABLE)
        self.assertEqual(self.db.transactions[tx]["isolation"], IsolationLevel.SERIALIZABLE)


if __name__ == "__main__":
    unittest.main()

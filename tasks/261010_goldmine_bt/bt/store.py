"""全取引をSQLite (trades.db) に記録する。将来の較正ラベルの燃料。"""
import json
import sqlite3

SCHEMA = """
CREATE TABLE IF NOT EXISTS trades (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  entry_date TEXT, exit_date TEXT, symbol TEXT, side TEXT, qty REAL,
  entry_px REAL, exit_px REAL, gross REAL, cost REAL, net REAL,
  exit_reason TEXT, features_json TEXT
);
"""


def connect(path):
    con = sqlite3.connect(path)
    con.execute(SCHEMA)
    con.commit()
    return con


def record_all(con, trades, symbol=""):
    rows = [(t["entry_date"], t["exit_date"], symbol, t["side"], t["qty"],
             t["entry_px"], t["exit_px"], t["gross"], t["cost"], t["net"],
             t["exit_reason"], t.get("features_json", "{}")) for t in trades]
    con.executemany(
        "INSERT INTO trades (entry_date,exit_date,symbol,side,qty,entry_px,exit_px,"
        "gross,cost,net,exit_reason,features_json) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", rows)
    con.commit()
    return len(rows)


def count(con):
    return con.execute("SELECT COUNT(*) FROM trades").fetchone()[0]

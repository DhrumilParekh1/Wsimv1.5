"""SQLite transactional save storage and queryable indexes for the local single-player game.

The canonical state remains the GameState dataclass: no match rules depend on SQL.
One transaction stores the complete save and refreshed searchable roster, storyline,
show, and memory indexes. Existing JSON exports remain supported for backwards use.
"""
from __future__ import annotations
import json
import sqlite3
from dataclasses import asdict
from contextlib import closing
from pathlib import Path
from .storage import restore_game

SCHEMA_VERSION = 1


def connect(db_path):
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(str(path), timeout=10)
    connection.execute('PRAGMA busy_timeout=10000')
    connection.execute('PRAGMA foreign_keys=ON')
    connection.executescript('''
        CREATE TABLE IF NOT EXISTS metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS snapshot (
            id INTEGER PRIMARY KEY CHECK(id=1), state_json TEXT NOT NULL,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
        CREATE TABLE IF NOT EXISTS wrestlers (
            id TEXT PRIMARY KEY, name TEXT NOT NULL, company_id TEXT,
            division TEXT, card_tier TEXT, morale REAL, weekly_salary INTEGER);
        CREATE INDEX IF NOT EXISTS wrestlers_by_company ON wrestlers(company_id,division);
        CREATE TABLE IF NOT EXISTS storylines (
            id TEXT PRIMARY KEY, title TEXT NOT NULL, stage TEXT,
            hype REAL, fan_investment REAL);
        CREATE TABLE IF NOT EXISTS shows (
            id TEXT PRIMARY KEY, name TEXT NOT NULL, year INTEGER,
            week INTEGER, simulated INTEGER NOT NULL);
        CREATE INDEX IF NOT EXISTS shows_calendar ON shows(year,week);
        CREATE TABLE IF NOT EXISTS memories (
            id TEXT PRIMARY KEY, year INTEGER, week INTEGER, kind TEXT,
            description TEXT NOT NULL);
        CREATE INDEX IF NOT EXISTS memories_date ON memories(year,week);
        CREATE TABLE IF NOT EXISTS enquiries (
            key TEXT PRIMARY KEY, wrestler_id TEXT NOT NULL,
            status TEXT NOT NULL, due_ordinal INTEGER);
    ''')
    connection.execute('INSERT OR REPLACE INTO metadata(key,value) VALUES (?,?)', ('schema_version',str(SCHEMA_VERSION)))
    connection.commit()
    return connection


def save_database(state, path):
    """Commit state + read indexes together; failed writes roll back entirely."""
    with closing(connect(path)) as db:
        with db:
            db.execute('INSERT OR REPLACE INTO snapshot(id,state_json) VALUES (1,?)',
                       (json.dumps(asdict(state),ensure_ascii=False),))
            for table in ('wrestlers','storylines','shows','memories','enquiries'):
                db.execute(f'DELETE FROM {table}')
            db.executemany('INSERT INTO wrestlers VALUES (?,?,?,?,?,?,?)', [
                (w.id,w.name,w.company_id,w.division,w.card_tier,w.morale,w.salary_weekly)
                for w in state.wrestlers.values()])
            db.executemany('INSERT INTO storylines VALUES (?,?,?,?,?)', [
                (s.id,s.title,s.stage,s.hype,s.fan_investment)
                for s in state.storylines.values()])
            db.executemany('INSERT INTO shows VALUES (?,?,?,?,?)', [
                (s.id,s.name,s.result.get('year',state.year) if s.result else state.year,
                 s.week,int(s.simulated)) for s in state.shows.values()])
            db.executemany('INSERT INTO memories VALUES (?,?,?,?,?)', [
                (m['id'],m.get('year'),m.get('week'),m.get('type'),m.get('description',''))
                for m in state.memories])
            db.executemany('INSERT INTO enquiries VALUES (?,?,?,?)', [
                (e['key'],e['wrestler_id'],e.get('status','pending'),e.get('due_ordinal'))
                for e in state.recruitment_interest])


def load_database(path):
    with closing(connect(path)) as db:
        item=db.execute('SELECT state_json FROM snapshot WHERE id=1').fetchone()
        if item is None:
            raise ValueError('No saved campaign in database')
        return restore_game(json.loads(item[0]))


def has_save(path):
    if not Path(path).exists():return False
    with closing(connect(path)) as db:
        return db.execute('SELECT EXISTS(SELECT 1 FROM snapshot WHERE id=1)').fetchone()[0]==1

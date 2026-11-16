"""Export local learner progress/flags for the dedicated production D1 database."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sqlite3

from tooling.discover import PRIVATE, ROOT, save

DEFAULT_DB = PRIVATE / 'local-mvp/learning.sqlite'
PUBLIC = ROOT / 'experiments/phase-three-learner-export.json'
PRIVATE = PRIVATE / 'production/learner-export'


def quote(value):
    if value is None:
        return 'NULL'
    if isinstance(value, (int, float)):
        return str(value)
    return "'" + str(value).replace("'", "''") + "'"


def export(database=DEFAULT_DB, *, output=None, sql_output=None):
    database = Path(database)
    if not database.exists():
        attempts, flags, sessions = [], [], []
    else:
        connection = sqlite3.connect(f'file:{database}?mode=ro', uri=True)
        connection.row_factory = sqlite3.Row
        try:
            attempts = [dict(r) for r in connection.execute('SELECT * FROM attempts ORDER BY at')]
            flags = [dict(r) for r in connection.execute('SELECT * FROM flags ORDER BY at')]
            sessions = [dict(r) for r in connection.execute('SELECT * FROM sessions ORDER BY started')]
        finally:
            connection.close()
    # Only progress and reports are needed for a new production session history.
    statements = []
    for row in attempts:
        statements.append('INSERT OR IGNORE INTO attempts(id,session_id,question_id,profile_id,asset_id,species_code,kind,mode,choice,outcome,at) VALUES(' + ','.join(quote(row.get(key)) for key in ['id','session_id','question_id','profile_id','asset_id','species_code','kind','mode','choice','outcome','at']) + ');')
    for row in flags:
        statements.append('INSERT OR IGNORE INTO flags(id,profile_id,asset_id,release_id,session_id,reason,suggested_species,at) VALUES(' + ','.join(quote(row.get(key)) for key in ['id','profile_id','asset_id','release_id','session_id','reason','suggested_species','at']) + ');')
    sql = '\n'.join(statements) + ('\n' if statements else '')
    private = Path(output) if output else PRIVATE / 'learner-progress.sql'
    private.parent.mkdir(parents=True, exist_ok=True)
    private.write_text(sql)
    summary = {'schema': 'birdahead-learner-export-v1', 'source_database': str(database.name),
               'attempts': len(attempts), 'flags': len(flags), 'sessions_available': len(sessions),
               'import_sql_private': str(private), 'import_statement': 'wrangler d1 execute DB --remote --file <private-sql>',
               'note': 'Profiles are seeded by migration. Only idempotent attempts/flags are imported; active local sessions are not resumed.'}
    save(PUBLIC, summary)
    if sql_output:
        Path(sql_output).write_text(sql)
    print(json.dumps({key: summary[key] for key in ['attempts','flags','sessions_available','import_sql_private']}, indent=2))
    return summary


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--database', type=Path, default=DEFAULT_DB)
    parser.add_argument('--sql', type=Path, default=None)
    args = parser.parse_args()
    export(args.database, sql_output=args.sql)

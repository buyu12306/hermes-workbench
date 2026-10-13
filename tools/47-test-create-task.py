# Validate the exact kanban_db path the /task endpoint will use.
import sys
from pathlib import Path

REPO = Path(r'C:/Users/<用户名>/Desktop/hermes-agent-main')
sys.path.insert(0, str(REPO))

from hermes_cli import kanban_db as kb
from hermes_cli import kanban_db_connect as kbc

with kbc.connect_closing() as conn:
    tid = kb.create_task(
        conn,
        title='__api-path-test__（可删）',
        body='endpoint path validation',
        assignee='deepseek-harness',
        created_by='workbench-ui',
    )
    try:
        conn.commit()
    except Exception as e:
        print('commit warn:', e)
print('created:', tid)

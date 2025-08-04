import json
import logging
import os                                    # ← NEW
import psycopg2                              # ← NEW
from psycopg2.extras import RealDictCursor   # ← NEW

# -------------------------------------------------------------------
# Build a portable Postgres DSN from environment variables (no AWS SDK)
# -------------------------------------------------------------------
DSN = (
    f"host={os.environ['DB_HOST']} "
    f"port={os.getenv('DB_PORT', '5432')} "
    f"user={os.environ['DB_USER']} "
    f"password={os.environ['DB_PASS']} "
    f"dbname={os.getenv('DB_NAME', 'postgres')}"
)

# -------------------------------------------------------------------
# Helper that ensures the table exists and inserts one greeting row
# -------------------------------------------------------------------
def insert_greeting(message: str) -> dict:
    """
    Ensures 'greetings' table exists and inserts one row.
    Returns dict with inserted id and timestamp and current total rows.
    """
    with psycopg2.connect(DSN) as conn, conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS greetings (
                id  SERIAL PRIMARY KEY,
                msg TEXT NOT NULL,
                ts  TIMESTAMPTZ DEFAULT now()
            )
        """)
        cur.execute(
            "INSERT INTO greetings (msg) VALUES (%s) RETURNING id, ts",
            (message,)
        )
        inserted = cur.fetchone()

        cur.execute("SELECT COUNT(*) AS total FROM greetings")
        total_rows = cur.fetchone()["total"]

    return {
        "inserted_id": inserted["id"],
        "inserted_at": inserted["ts"].isoformat(),
        "total_rows": total_rows
    }

# -------------------------------------------------------------------
# Configure logging (unchanged)
# -------------------------------------------------------------------
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# -------------------------------------------------------------------
# Lambda handler (original logic + DB insert)
# -------------------------------------------------------------------
def lambda_handler(event, context):
    """
    AWS Lambda function handler for RedCouch project
    Adds a row to the 'greetings' table on each request.
    """
    try:
        # Log the incoming event
        logger.info(f"Received event: {json.dumps(event)}")

        # Parse the event
        http_method = event.get('httpMethod', 'GET')
        path = event.get('path', '/')

        # INSERT one greeting row for EVERY invocation ----------------
        db_result = insert_greeting(f"Path {path} via {http_method}")

        # Handle different HTTP methods
        if http_method == 'GET':
            if path == '/':
                body = {
                    'message': 'Welcome to RedCouch API',
                    'status': 'success',
                    **db_result                          # ← include DB info
                }
                status_code = 200

            elif path == '/health':
                body = {
                    'status': 'healthy',
                    'service': 'redcouch',
                    **db_result
                }
                status_code = 200

            else:
                body = {
                    'error': 'Not Found',
                    'message': f'Path {path} not found',
                    **db_result
                }
                status_code = 404

        elif http_method == 'POST':
            # Handle POST requests
            raw_body = event.get('body', '{}')
            try:
                body_data = json.loads(raw_body) if raw_body else {}
            except json.JSONDecodeError:
                body_data = {}

            body = {
                'message': 'POST request received',
                'data': body_data,
                'status': 'success',
                **db_result
            }
            status_code = 200

        else:
            body = {
                'error': 'Method Not Allowed',
                'message': f'HTTP method {http_method} not supported',
                **db_result
            }
            status_code = 405

        return {
            'statusCode': status_code,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps(body)
        }

    except Exception as e:
        logger.error(f"Error processing request: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'error': 'Internal Server Error',
                'message': 'An unexpected error occurred'
            })
        }

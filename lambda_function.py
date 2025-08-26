import json
import logging
import os
import pg8000
from pg8000.native import Connection

# -------------------------------------------------------------------
# Build a portable Postgres DSN from environment variables (no AWS SDK)
# -------------------------------------------------------------------
DB_CONFIG = {
    'host': os.environ['DB_HOST'],
    'port': int(os.getenv('DB_PORT', '5432')),
    'user': os.environ['DB_USER'],
    'password': os.environ['DB_PASS'],
    'database': os.getenv('DB_NAME', 'postgres')
}

# -------------------------------------------------------------------
# Helper that ensures the table exists and inserts one greeting row
# -------------------------------------------------------------------
def insert_greeting(message: str) -> dict:
    """
    Ensures 'greetings' table exists and inserts one row.
    Returns dict with inserted id and timestamp and current total rows.
    """
    conn = Connection(**DB_CONFIG)
    try:
        # Create table if it doesn't exist
        conn.run("""
            CREATE TABLE IF NOT EXISTS greetings (
                id  SERIAL PRIMARY KEY,
                msg TEXT NOT NULL,
                ts  TIMESTAMPTZ DEFAULT now()
            )
        """)
        
        # Insert greeting
        result = conn.run(
            "INSERT INTO greetings (msg) VALUES (:msg) RETURNING id, ts",
            msg=message
        )
        inserted_id = result[0][0]
        inserted_ts = result[0][1]

        # Get total count
        count_result = conn.run("SELECT COUNT(*) FROM greetings")
        total_rows = count_result[0][0]

        return {
            "inserted_id": inserted_id,
            "inserted_at": inserted_ts.isoformat(),
            "total_rows": total_rows
        }
    finally:
        conn.close()

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

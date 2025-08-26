import json
import logging
import os
import boto3
import pg8000
from pg8000.native import Connection

# -------------------------------------------------------------------
# Get database credentials from AWS Secrets Manager
# -------------------------------------------------------------------
def get_db_credentials():
    """Get database credentials from AWS Secrets Manager"""
    secret_name = "rds-db-credentials/redcouchdb/firstuser/1756179484889-Tz16wN"
    region_name = "us-east-2"
    
    session = boto3.session.Session()
    client = session.client(
        service_name='secretsmanager',
        region_name=region_name
    )
    
    try:
        get_secret_value_response = client.get_secret_value(
            SecretId=secret_name
        )
    except Exception as e:
        logging.error(f"Error getting secret: {e}")
        raise
    
    if 'SecretString' in get_secret_value_response:
        secret = json.loads(get_secret_value_response['SecretString'])
        return secret
    else:
        raise ValueError("Secret not found in expected format")

# -------------------------------------------------------------------
# Build database connection using RDS Proxy
# -------------------------------------------------------------------
def get_db_connection():
    """Get database connection using RDS Proxy"""
    try:
        credentials = get_db_credentials()
        
        # Use RDS Proxy endpoint (you'll need to get this from AWS Console)
        # Go to RDS Console → Proxies → proxy-1756179484889-redcouchdb → Endpoint
        proxy_endpoint = os.environ.get('DB_PROXY_ENDPOINT', 'your-proxy-endpoint-here')
        
        conn = Connection(
            host=proxy_endpoint,
            port=5432,
            user=credentials['username'],
            password=credentials['password'],
            database=credentials['dbname'],
            ssl_context=False,
            timeout=10
        )
        return conn
    except Exception as e:
        logging.error(f"Error creating database connection: {e}")
        raise

# -------------------------------------------------------------------
# Helper that ensures the table exists and inserts one greeting row
# -------------------------------------------------------------------
def insert_greeting(message: str) -> dict:
    """
    Ensures 'greetings' table exists and inserts one row.
    Returns dict with inserted id and timestamp and current total rows.
    """
    conn = get_db_connection()
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

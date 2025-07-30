# lambda_function.py
import json
from datetime import datetime
import os


def lambda_handler(event, context):
    """
    Basic smoke-test Lambda handler.

    • Accepts any event (JSON-serializable).
    • Returns HTTP-style dict so it works behind API Gateway too.
    """
    return {
        "statusCode": 200,
        "body": json.dumps({
            "message": "Hello from Lambda this is Julian👋",
            "utc_time": datetime.utcnow().isoformat() + "Z",
            "function_version": os.environ.get("AWS_LAMBDA_FUNCTION_VERSION"),
            "echo_event": event           # helpful when you test in the console
        })
    }

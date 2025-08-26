Python API for AWS Lambda (Deployed via GitHub Actions)
========================================================

This project is a minimal Flask-based Python API designed to be deployed to AWS Lambda using GitHub Actions and OIDC authentication. All dependencies are bundled into a deployment zipfile, pushed to Lambda via the AWS CLI, and configured with runtime environment variables.

--------------------------------------------------------------------------------
Project Structure
--------------------------------------------------------------------------------

.
├── main.py                     # Flask API server
├── lambda_function.py          # Optional Lambda entrypoint
├── requirements.txt            # Python dependencies
├── Dockerfile                  # Optional (not used for Lambda ZIP deploy)
├── .github/
│   └── workflows/
│       └── deploy.yml          # GitHub Actions workflow (CI/CD)
├── build/                      # Auto-generated folder for staging code + deps
├── function.zip                # Lambda deployment package (build artifact)
└── README.txt                  # This file

--------------------------------------------------------------------------------
File Explanations
--------------------------------------------------------------------------------

main.py
    Your main Flask API file. Defines routes such as /api, /ping, /echo.

lambda_function.py
    Optional. Can define lambda_handler(event, context) if not using API Gateway proxy.

requirements.txt
    Python dependencies:
        flask
        psycopg2-binary>=2.9.7,<2.10

Dockerfile
    Optional. Unused unless switching to Docker-based Lambda deployment.

.github/workflows/deploy.yml
    GitHub Actions CI/CD workflow. Handles packaging, deployment, and environment config.

build/
    Temporary folder used to collect source code and dependencies for zipping.

function.zip
    Deployment artifact uploaded to AWS Lambda. Created by zipping build/.

--------------------------------------------------------------------------------
How Deployment Works (via deploy.yml)
--------------------------------------------------------------------------------

1. Triggered on every push to the master branch.
2. Uses GitHub OIDC to assume AWS IAM role (`AWS_ROLE_ARN`).
3. Copies all .py files into a build/ folder.
4. Installs dependencies into build/ with:
       pip install -r requirements.txt \
           --platform manylinux_2_17_x86_64 \
           --implementation cp \
           --python-version 3.11 \
           --only-binary=:all: \
           --no-deps \
           --upgrade -t build
5. Zips everything in build/ into function.zip.
6. Updates Lambda code with:
       aws lambda update-function-code --function-name redCouch_LamdaFunction --zip-file fileb://function.zip
7. Waits for Lambda deployment to complete.
8. Updates Lambda environment variables using:
       aws lambda update-function-configuration --environment "Variables={DB_HOST=..., DB_USER=..., ...}"

--------------------------------------------------------------------------------
GitHub Secrets Required
--------------------------------------------------------------------------------

Set the following secrets under GitHub → Settings → Secrets and Variables → Actions:

    AWS_ROLE_ARN      IAM role ARN for OIDC
    DB_HOST           Database hostname
    DB_PORT           Database port (e.g. 5432)
    DB_USER           Database user
    DB_PASS           Database password
    DB_NAME           Database name

--------------------------------------------------------------------------------
API Endpoints
--------------------------------------------------------------------------------

Deployed API routes (accessible via API Gateway endpoint):

    GET  /api         → Returns a greeting message
    GET  /api/ping    → Returns {"status": "ok"}
    POST /api/echo    → Echoes the incoming JSON payload

Example:
    curl https://<api-url>/api/ping
    → {"status":"ok"}

    curl -X POST https://<api-url>/api/echo -H "Content-Type: application/json" -d '{"hello":"world"}'
    → {"you_sent":{"hello":"world"}}

--------------------------------------------------------------------------------
Local Development
--------------------------------------------------------------------------------

To run locally:

    pip install -r requirements.txt
    python main.py

Then open:
    http://localhost:80/api

--------------------------------------------------------------------------------
Lambda Compatibility Notes
--------------------------------------------------------------------------------

• Target runtime: Python 3.11 (avoid 3.12 for now)
• Lambda runs on Amazon Linux 2 (x86_64)
• Use manylinux_2_17_x86_64 platform when installing packages for Lambda
• psycopg2-binary must be installed using precompiled wheels only
• Always use --only-binary=:all: and --no-deps when cross-compiling with pip

--------------------------------------------------------------------------------
Summary
--------------------------------------------------------------------

import os

os.environ["APP_ENV"] = "test"
os.environ["AUTH_MODE"] = "api_key"
os.environ["REQUIRE_ADMIN_AUTH"] = "false"
os.environ["ADMIN_API_KEY"] = ""
os.environ["FIREBASE_AUTH_ENABLED"] = "false"

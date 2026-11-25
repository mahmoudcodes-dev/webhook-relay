import os

# Module-level `app = create_app()` in app.main requires the secret at import time.
os.environ.setdefault("WEBHOOK_SECRET", "test-secret")

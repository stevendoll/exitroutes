import sys
import os
from pathlib import Path

# Add app/ to path so test files can import parser, cleaner, mapper, packager
sys.path.insert(0, str(Path(__file__).parent.parent / "app"))

# Add api/ to path for webhook tests
sys.path.insert(0, str(Path(__file__).parent.parent / "api"))

# Set required env vars for modules that read them at import time
os.environ.setdefault("STRIPE_WEBHOOK_SECRET", "whsec_test_secret")
os.environ.setdefault("SLACKMAIL_URL", "https://example.com")
os.environ.setdefault("SLACKMAIL_API_KEY", "test-api-key")
os.environ.setdefault("FROM_EMAIL", "test@example.com")
os.environ.setdefault("TYPEFORM_LINK", "https://typeform.com/test")

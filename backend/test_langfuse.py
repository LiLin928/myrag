"""测试 Langfuse 数据发送"""

import sys
sys.path.insert(0, '.')

from app.config import get_settings
from langfuse import Langfuse

settings = get_settings()

print(f"Host: {settings.LANGFUSE_HOST}")
print(f"Enabled: {settings.LANGFUSE_ENABLED}")

if not settings.langfuse_available:
    print("Langfuse not available!")
    sys.exit(1)

print("\nCreating observation...")
client = Langfuse(
    public_key=settings.LANGFUSE_PUBLIC_KEY,
    secret_key=settings.LANGFUSE_SECRET_KEY,
    host=settings.LANGFUSE_HOST,
    timeout=60,
)

print(f"Auth check: {client.auth_check()}")

obs = client.start_observation(
    name="TEST-DATA-123",
    input={"test": True},
    metadata={"source": "test"},
)
print(f"Observation ID: {obs.id}")

obs.update(output={"result": "success"})
obs.end()

print("Flushing...")
client.flush()
print("Done!")

print(f"\nCheck: {settings.LANGFUSE_HOST}")
print("Look for 'TEST-DATA-123' in Observations")
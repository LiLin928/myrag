"""完整验证 Langfuse 数据写入"""

import sys
import time
import httpx
import base64
sys.path.insert(0, '.')

from app.config import get_settings
from langfuse import Langfuse

settings = get_settings()

pk = settings.LANGFUSE_PUBLIC_KEY
sk = settings.LANGFUSE_SECRET_KEY
host = settings.LANGFUSE_HOST

print("=" * 60)
print("Langfuse 完整验证测试")
print(f"Host: {host}")
print(f"Public Key: {pk}")
print(f"Secret Key: {sk}")
print("=" * 60)

auth = base64.b64encode(f'{pk}:{sk}'.encode()).decode()
headers = {'Authorization': f'Basic {auth}', 'Content-Type': 'application/json'}

# 1. 检查服务健康状态
print("\n[1] 检查 Langfuse 服务状态...")
try:
    r = httpx.get(f"{host}/api/public/traces", headers=headers, params={'limit': 1}, timeout=10)
    print(f"    Status: {r.status_code}")
    if r.status_code == 200:
        data = r.json()
        print(f"    Response: {data}")
    else:
        print(f"    Error: {r.text[:200]}")
except Exception as e:
    print(f"    连接失败: {e}")

# 2. 使用 SDK 创建数据
print("\n[2] 使用 SDK 创建 Observation...")
try:
    client = Langfuse(public_key=pk, secret_key=sk, host=host, timeout=30)
    print(f"    Auth check: {client.auth_check()}")

    obs_name = f"VERIFY-TEST-{int(time.time())}"
    obs = client.start_observation(
        name=obs_name,
        input={"test": True, "timestamp": time.time()},
        metadata={"source": "verify_script"},
    )
    obs_id = obs.id
    print(f"    Observation ID: {obs_id}")
    print(f"    Observation Name: {obs_name}")

    obs.update(output={"result": "success"})
    obs.end()

    print("    Flushing...")
    client.flush()
    print("    SDK Done!")
except Exception as e:
    print(f"    SDK Error: {e}")
    sys.exit(1)

# 3. 等待数据写入
print("\n[3] 等待 5 秒...")
time.sleep(5)

# 4. 查询数据是否存在
print("\n[4] 查询刚创建的数据...")
try:
    # 查询 observations
    r = httpx.get(
        f"{host}/api/public/observations",
        headers=headers,
        params={'name': obs_name},
        timeout=10
    )
    print(f"    Observations API Status: {r.status_code}")
    if r.status_code == 200:
        data = r.json()
        print(f"    Found: {len(data.get('data', data))} records")
        print(f"    Data: {str(data)[:500]}")
    else:
        print(f"    Error: {r.text[:200]}")

    # 查询 traces
    r = httpx.get(
        f"{host}/api/public/traces",
        headers=headers,
        params={'limit': 5},
        timeout=10
    )
    print(f"    Traces API Status: {r.status_code}")
    if r.status_code == 200:
        data = r.json()
        print(f"    Traces count: {len(data.get('data', data))}")
    else:
        print(f"    Error: {r.text[:200]}")
except Exception as e:
    print(f"    查询失败: {e}")

# 5. 直接 POST 测试
print("\n[5] 直接 HTTP POST 测试...")
try:
    r = httpx.post(
        f"{host}/api/public/ingestion",
        headers=headers,
        json={'batch': [{'id': 'direct-test', 'type': 'span', 'body': {'name': 'HTTP-DIRECT-TEST'}}]},
        timeout=10
    )
    print(f"    Ingestion Status: {r.status_code}")
    print(f"    Response: {r.text[:300]}")
except Exception as e:
    print(f"    POST 失败: {e}")

print("\n" + "=" * 60)
print("验证完成")
print("=" * 60)
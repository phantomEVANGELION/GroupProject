"""通过 Gradio API 调用工作流，测试 generator 是否正常"""
import requests
import json
import time

BASE = "http://127.0.0.1:7860"

# 1. 检查有哪些 API 端点
r = requests.get(f"{BASE}/gradio_api/api_info")
if r.status_code == 200:
    data = r.json()
    named = data.get("named_endpoints", {})
    print(f"命名端点: {list(named.keys())}")
else:
    print(f"api_info 返回: {r.status_code}")

# 2. 检查配置
r2 = requests.get(f"{BASE}/gradio_api/config")
if r2.status_code == 200:
    cfg = r2.json()
    deps = cfg.get("dependencies", [])
    for d in deps:
        tid = d.get("targets", [None])[0]
        if tid:
            # 找到对应组件
            for c in cfg.get("components", []):
                if c["id"] == tid:
                    props = c.get("props", {})
                    if "开始全面分析" in str(props):
                        fn_index = d.get("id")
                        print(f"  函数 index: {fn_index} (按钮: 开始全面分析)")

# 3. 直接调用未命名端点
# 在 Gradio 5.x 中，fn_index 方式: POST /gradio_api/call/{fn_index}
# 或者通过 unset 端点
print("\n尝试直接调用函数...")

# 尝试通过 api_info 找到未命名端点
r3 = requests.get(f"{BASE}/gradio_api/api_info")
if r3.status_code == 200:
    info = r3.json()
    unnamed = info.get("unnamed_endpoints", {})
    print(f"未命名端点数量: {len(unnamed)}")
    if unnamed:
        for k, v in list(unnamed.items())[:5]:
            print(f"  {k}: {v}")

print("\n尝试 predict API...")
# Gradio 4.x 方式
for endpoint in ["/gradio_api/predict", "/gradio_api/call/predict"]:
    try:
        r = requests.post(
            f"{BASE}{endpoint}",
            json={"data": ["X100 智能运动手表", "IP68防水 7天续航 AMOLED屏幕", None]},
            timeout=5
        )
        print(f"  {endpoint}: {r.status_code}")
    except Exception as e:
        print(f"  {endpoint}: 超时/错误 ({e})")

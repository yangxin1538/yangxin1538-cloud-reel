"""Example plugin: 盘搜 (PanSou) search stub.

Wire a real search API / key in run() to make it live. Until then it
returns a clear not-configured result instead of fake links.
"""
PLUGIN = {"name": "pansou", "description": "盘搜：网盘资源搜索（示例，需接真实接口）", "version": "0.1.0"}


def run(query, settings):
    return {"query": query, "configured": False, "results": [], "note": "接盘搜接口后返回真实结果"}

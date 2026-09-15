#!/usr/bin/env python3
"""Исполняет обязательные проверки API, описанные в DATA-API.yaml.

Файл DATA-API.yaml — не декларация, а исполняемый список: этот скрипт
читает его и вызывает каждый метод, сверяя статус-код, обязательные поля
и ожидаемые значения.

Запуск (сервисы подняты):
    python3 tools/api_contract_check.py [--base http://localhost:8080]
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import requests
import yaml

ROOT = Path(__file__).resolve().parents[1]
REF = re.compile(r"\{\{([a-z_]+)\.([a-z_]+)\}\}")
SELECT = re.compile(r"^([a-z_]+)\[\?([a-z_]+)=='([^']+)'\]\.([a-z_]+)$")


def resolve(value, memory: dict):
    """Подставляет {{check_id.field}} из ответов предыдущих проверок."""
    if isinstance(value, str):
        def sub(m):
            return str(memory.get(m.group(1), {}).get(m.group(2), ""))
        return REF.sub(sub, value)
    if isinstance(value, dict):
        return {k: resolve(v, memory) for k, v in value.items()}
    if isinstance(value, list):
        return [resolve(v, memory) for v in value]
    return value


def read_path(data, path: str):
    """Поддерживает `a.b.c` и `items[?key=='v'].field`."""
    m = SELECT.match(path)
    if m:
        coll, key, val, field = m.groups()
        for item in data.get(coll, []):
            if str(item.get(key)) == val:
                return item.get(field)
        return None
    cur = data
    for part in path.split("."):
        if not isinstance(cur, dict):
            return None
        cur = cur.get(part)
    return cur


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default=None, help="Базовый адрес API (переопределяет base_url из файла)")
    ap.add_argument("--spec", default=str(ROOT / "DATA-API.yaml"))
    args = ap.parse_args()

    spec = yaml.safe_load(open(args.spec, encoding="utf-8"))
    base = (args.base or spec["base_url"]).rstrip("/")
    print(f"\nПроверки API по {args.spec}\nБазовый адрес: {base}\n")

    memory: dict[str, dict] = {}
    ok = bad = 0

    for check in spec["checks"]:
        req = resolve(check.get("request") or {}, memory)
        path = check["path"]
        for name, value in (req.get("path_params") or {}).items():
            path = path.replace("{" + name + "}", str(value))
        try:
            resp = requests.request(check["method"], base + path,
                                    headers=req.get("headers") or {},
                                    params=req.get("query_params") or None,
                                    json=req.get("body"), timeout=15)
        except requests.RequestException as exc:
            print(f"  ✗ {check['id']}: сервис недоступен — {exc}")
            bad += 1
            continue

        problems: list[str] = []
        expected = check["expected_status"]
        if resp.status_code not in expected:
            problems.append(f"статус {resp.status_code}, ожидался один из {expected}: {resp.text[:160]}")

        data = {}
        try:
            data = resp.json()
        except ValueError:
            problems.append("ответ не JSON")

        rs = check.get("response") or {}
        ctype = resp.headers.get("content-type", "")
        if rs.get("content_type") and rs["content_type"] not in ctype:
            problems.append(f"content-type {ctype!r}, ожидался {rs['content_type']!r}")
        for field in rs.get("required_fields") or []:
            if isinstance(data, dict) and field not in data:
                problems.append(f"нет обязательного поля {field!r}")
        for field in rs.get("forbidden_fields") or []:
            if field in str(data):
                problems.append(f"в ответе есть запрещённое поле {field!r}")
        if rs.get("min_items") and isinstance(data.get("items"), list):
            if len(data["items"]) < rs["min_items"]:
                problems.append(f"элементов {len(data['items'])}, минимум {rs['min_items']}")
        for path_expr, want in (rs.get("expect") or {}).items():
            got = read_path(data, path_expr)
            if got != want:
                problems.append(f"{path_expr}: получено {got!r}, ожидалось {want!r}")

        if isinstance(data, dict):
            memory[check["id"]] = data
        if problems:
            bad += 1
            print(f"  ✗ {check['id']} — {check['title']}")
            for p in problems:
                print(f"      {p}")
        else:
            ok += 1
            print(f"  ✓ {check['id']} — {check['title']}")

    print(f"\nИтог: пройдено {ok}, не пройдено {bad}\n")
    return 0 if bad == 0 else 1


if __name__ == "__main__":
    sys.exit(main())

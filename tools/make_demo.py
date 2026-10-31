#!/usr/bin/env python3
"""Оставлено для совместимости: теперь всё делает tools/sync_clients.py (список папок в tools/clients.json)."""
import os, runpy
runpy.run_path(os.path.join(os.path.dirname(os.path.abspath(__file__)), "sync_clients.py"), run_name="__main__")

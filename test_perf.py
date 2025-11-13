#!/usr/bin/env python3
import sys

sys.path.append(".")

from db.analytics_performance_tools import performance_monitor

print("Testing performance monitor...")
result = performance_monitor()
print("Result:")
print(result)
print("Done.")

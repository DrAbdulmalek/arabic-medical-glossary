#!/usr/bin/env python3
"""Entry point for ICD-11 collection."""

from collectors.icd11 import ICD11Collector

if __name__ == "__main__":
    collector = ICD11Collector()
    result = collector.run()
    print(f"ICD-11: {result}")

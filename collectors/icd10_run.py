#!/usr/bin/env python3
"""Entry point for ICD-10-CM collection."""

from collectors.icd10 import ICD10Collector

if __name__ == "__main__":
    collector = ICD10Collector()
    result = collector.run()
    print(f"ICD-10-CM: {result}")

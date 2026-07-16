#!/usr/bin/env python3
"""Entry point for LOINC collection."""

from collectors.loinc import LOINCCollector

if __name__ == "__main__":
    collector = LOINCCollector()
    result = collector.run()
    print(f"LOINC: {result}")

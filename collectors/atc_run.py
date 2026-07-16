#!/usr/bin/env python3
"""Entry point for ATC collection."""

from collectors.atc import ATCCollector

if __name__ == "__main__":
    collector = ATCCollector()
    result = collector.run()
    print(f"ATC: {result}")

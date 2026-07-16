#!/usr/bin/env python3
"""Entry point for ICHI collection."""

from collectors.ichi import ICHICollector

if __name__ == "__main__":
    collector = ICHICollector()
    result = collector.run()
    print(f"ICHI: {result}")

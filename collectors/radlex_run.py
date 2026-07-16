#!/usr/bin/env python3
"""Entry point for RadLex collection (placeholder)."""

from collectors.radlex import RadLexCollector

if __name__ == "__main__":
    collector = RadLexCollector()
    result = collector.run()
    print(f"RadLex: {result}")

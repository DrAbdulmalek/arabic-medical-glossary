#!/usr/bin/env python3
"""Entry point for MedDRA collection (placeholder)."""

from collectors.meddra import MedDRACollector

if __name__ == "__main__":
    collector = MedDRACollector()
    result = collector.run()
    print(f"MedDRA: {result}")

#!/usr/bin/env python3
"""Entry point for CPT collection (placeholder)."""

from collectors.cpt import CPTCollector

if __name__ == "__main__":
    collector = CPTCollector()
    result = collector.run()
    print(f"CPT: {result}")

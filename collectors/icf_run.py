#!/usr/bin/env python3
"""Entry point for ICF collection."""

from collectors.icf import ICFCollector

if __name__ == "__main__":
    collector = ICFCollector()
    result = collector.run()
    print(f"ICF: {result}")

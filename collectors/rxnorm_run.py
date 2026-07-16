#!/usr/bin/env python3
"""Entry point for RxNorm collection."""

from collectors.rxnorm import RxNormCollector

if __name__ == "__main__":
    collector = RxNormCollector()
    result = collector.run()
    print(f"RxNorm: {result}")

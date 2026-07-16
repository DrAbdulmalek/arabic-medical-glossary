#!/usr/bin/env python3
"""Entry point for HCPCS collection."""

from collectors.hcpcs import HCPCSCollector

if __name__ == "__main__":
    collector = HCPCSCollector()
    result = collector.run()
    print(f"HCPCS: {result}")

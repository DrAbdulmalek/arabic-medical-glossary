#!/usr/bin/env python3
"""Entry point for MeSH collection."""

from collectors.mesh import MeSHCollector

if __name__ == "__main__":
    collector = MeSHCollector()
    result = collector.run()
    print(f"MeSH: {result}")

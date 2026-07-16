#!/usr/bin/env python3
"""Entry point for UMLS collection."""

from collectors.umls import UMLSCollector

if __name__ == "__main__":
    collector = UMLSCollector()
    result = collector.run()
    print(f"UMLS: {result}")

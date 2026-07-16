#!/usr/bin/env python3
"""Entry point for SNOMED CT collection."""

from collectors.snomed_ct import SNOMEDCTCollector

if __name__ == "__main__":
    collector = SNOMEDCTCollector()
    result = collector.run()
    print(f"SNOMED CT: {result}")

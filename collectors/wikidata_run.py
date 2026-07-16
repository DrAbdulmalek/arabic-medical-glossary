#!/usr/bin/env python3
"""Entry point for Wikidata collection."""

from collectors.wikidata import WikidataCollector

if __name__ == "__main__":
    collector = WikidataCollector()
    result = collector.run()
    print(f"Wikidata: {result}")

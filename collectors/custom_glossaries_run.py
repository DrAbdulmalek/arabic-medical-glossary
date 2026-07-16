#!/usr/bin/env python3
"""Entry point for custom glossaries collection."""

from collectors.custom_glossaries import CustomGlossariesCollector

if __name__ == "__main__":
    collector = CustomGlossariesCollector()
    result = collector.run()
    print(f"CustomGlossaries: {result}")
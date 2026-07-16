#!/usr/bin/env python3
"""Entry point for Telegram collection."""

from collectors.telegram_mtproto import TelegramCollector

if __name__ == "__main__":
    collector = TelegramCollector()
    result = collector.run()
    print(f"Telegram: {result}")

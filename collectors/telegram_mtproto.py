"""
Telegram collector using Telethon (MTProto) for private channel access.
Bypasses 20MB Bot API limit and can read full channel history.
"""

import os
import json
import asyncio
from datetime import datetime
from telethon import TelegramClient

from collectors.base import BaseCollector, TermEntry
from processors.text_extractor import extract_text_from_file
from processors.glossary_parser import parse_glossary_from_text


class TelegramCollector(BaseCollector):
    """
    مجمع مصطلحات من قناة تيليجرام خاصة
    يستخدم Telethon للوصول الكامل
    """

    def __init__(self, config: dict = None):
        super().__init__("Telegram_Channel", "telegram", config)

        self.api_id = int(os.getenv("TELEGRAM_API_ID", "0"))
        self.api_hash = os.getenv("TELEGRAM_API_HASH", "")
        self.phone = os.getenv("TELEGRAM_PHONE", "")
        self.channel_id = os.getenv("TELEGRAM_CHANNEL_ID", "")
        self.session_name = os.getenv("TELEGRAM_SESSION", "glossary_session")

        self.download_dir = os.path.join("data", "telegram_files")
        os.makedirs(self.download_dir, exist_ok=True)

        self.processed_log = os.path.join(
            self.progress_dir, "telegram_processed.json"
        )

    def load_processed(self) -> set:
        try:
            with open(self.processed_log, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return set(data.get("file_ids", []))
        except FileNotFoundError:
            return set()

    def save_processed(self, file_ids: set):
        with open(self.processed_log, 'w', encoding='utf-8') as f:
            json.dump({
                "file_ids": list(file_ids),
                "last_update": datetime.now().isoformat()
            }, f, ensure_ascii=False, indent=2)

    async def _process_message(self, client, message, processed: set) -> int:
        new_terms = 0

        if message.document or (message.media and hasattr(message.media, 'document')):
            doc = message.document or message.media.document

            if doc.size > 100 * 1024 * 1024:
                self.logger.warning(f"⚠️ ملف كبير جداً متجاهل: {doc.id}")
                return 0

            file_id = str(doc.id)

            if file_id not in processed:
                try:
                    file_path = await client.download_media(
                        message,
                        file=os.path.join(self.download_dir, file_id)
                    )

                    if file_path:
                        self.logger.info(
                            f"📥 تم التحميل: {os.path.basename(file_path)}"
                        )

                        text = extract_text_from_file(file_path)

                        if text:
                            entries = parse_glossary_from_text(
                                text, 
                                source=f"telegram:{file_id}"
                            )

                            for entry in entries:
                                if self.add_term(entry):
                                    new_terms += 1

                        os.remove(file_path)
                        processed.add(file_id)

                except Exception as e:
                    self.logger.error(
                        f"❌ خطأ في معالجة الملف {file_id}: {e}"
                    )

        elif message.text:
            entries = parse_glossary_from_text(
                message.text,
                source=f"telegram:message:{message.id}"
            )
            for entry in entries:
                if self.add_term(entry):
                    new_terms += 1

        return new_terms

    async def _collect_async(self) -> int:
        total_new = 0
        processed = self.load_processed()

        async with TelegramClient(
            self.session_name, self.api_id, self.api_hash
        ) as client:

            if not await client.is_user_authorized():
                await client.send_code_request(self.phone)
                self.logger.error("⚠️ يجب تسجيل الدخول يدوياً أول مرة!")
                return 0

            entity = await client.get_entity(int(self.channel_id))
            self.logger.info(f"📡 متصل بالقناة: {entity.title}")

            async for message in client.iter_messages(entity, reverse=True):
                new = await self._process_message(client, message, processed)
                total_new += new

                if len(processed) % 10 == 0:
                    self.save_processed(processed)

            self.save_processed(processed)

        return total_new

    def collect(self) -> int:
        return asyncio.run(self._collect_async())

"""
Collect medical terms from ICD-11 via WHO ICD-API.
Requires free WHO account + OAuth2 Client ID/Secret.

API Docs: https://icd.who.int/docs/icd-api/APIDoc-Version2/
Register: https://icd.who.int/icdapi
"""

import os
import time
from collectors.base import BaseCollector, TermEntry


class ICD11Collector(BaseCollector):
    """
    مجمع مصطلحات من ICD-11 (WHO)
    يتطلب حساب WHO + OAuth2 Client ID/Secret
    """

    def __init__(self, config: dict = None):
        super().__init__(
            "ICD-11",
            "https://icd.who.int/",
            config
        )
        self.api_base = "https://id.who.int/icd"
        self.auth_url = "https://icdaccessmanagement.who.int/connect/token"
        self.client_id = os.getenv("ICD11_CLIENT_ID", "")
        self.client_secret = os.getenv("ICD11_CLIENT_SECRET", "")
        self.access_token = None
        self.token_expiry = 0

        if not self.client_id or not self.client_secret:
            self.logger.warning(
                "⚠️ ICD11_CLIENT_ID/ICD11_CLIENT_SECRET غير موجود. "
                "سجّل مجاناً في https://icd.who.int/icdapi"
            )

    def _get_access_token(self) -> str:
        """الحصول على Access Token عبر OAuth2"""
        if self.access_token and time.time() < self.token_expiry:
            return self.access_token

        data = {
            "grant_type": "client_credentials",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "scope": "icdapi_access"
        }

        response = self.session.post(
            self.auth_url,
            data=data,
            timeout=30
        )
        response.raise_for_status()

        token_data = response.json()
        self.access_token = token_data.get("access_token", "")
        expires_in = token_data.get("expires_in", 3600)
        self.token_expiry = time.time() + expires_in - 60  # buffer

        self.logger.info("✅ تم الحصول على ICD-11 Access Token")
        return self.access_token

    def _make_authenticated_request(self, url: str, params: dict = None) -> dict:
        """طلب مع مصادقة OAuth2"""
        token = self._get_access_token()

        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
            "Accept-Language": "en",
            "API-Version": "v2"
        }

        response = self.session.get(url, params=params, headers=headers, timeout=30)

        if response.status_code == 401:
            self.access_token = None
            token = self._get_access_token()
            headers["Authorization"] = f"Bearer {token}"
            response = self.session.get(url, params=params, headers=headers, timeout=30)

        response.raise_for_status()
        return response.json()

    def collect(self) -> int:
        if not self.client_id or not self.client_secret:
            self.logger.warning("⏭️ بيانات ICD-11 غير موجودة. يتم التخطي.")
            return 0

        new_count = 0

        # استعلامات بحث ICD-11
        search_terms = [
            "diabetes", "hypertension", "pneumonia", "heart disease",
            "asthma", "stroke", "cancer", "fracture",
            "anemia", "hepatitis", "tuberculosis", "depression"
        ]

        for term in search_terms:
            try:
                # البحث في ICD-11
                search_url = f"{self.api_base}/release/11/2025-01/mms/search"
                params = {
                    "q": term,
                    "useFlexisearch": "true",
                    "flatResults": "true"
                }

                data = self._make_authenticated_request(search_url, params)

                for result in data.get("destinationEntities", []):
                    code = result.get("theCode", "")
                    title = result.get("title", "").get("@value", "") if isinstance(result.get("title"), dict) else result.get("title", "")
                    definition = result.get("definition", "").get("@value", "") if isinstance(result.get("definition"), dict) else ""

                    if not code or not title:
                        continue

                    entry = TermEntry(
                        term=title,
                        definition=definition or f"ICD-11 MMS Code: {code}",
                        source="ICD-11",
                        language="en",
                        confidence=0.94,
                        tags=["icd11", code, "mms"]
                    )

                    if self.add_term(entry):
                        new_count += 1

                self.rate_limit(0.5)

            except Exception as e:
                self.logger.error(f"خطأ في البحث عن '{term}': {e}")
                continue

        self.logger.info(f"✅ ICD-11: {new_count} مصطلح جديد")
        return new_count

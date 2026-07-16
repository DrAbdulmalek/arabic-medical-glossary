"""
Collect medical terms from UMLS (Unified Medical Language System) via UTS API.
Requires UMLS API Key (free for academic/research use).

To get API Key:
1. Register at https://uts.nlm.nih.gov/
2. Request UMLS license (free for individuals)
3. Get API Key from your UTS profile
"""

import os
import time
import requests
from urllib.parse import urlencode

from collectors.base import BaseCollector, TermEntry


class UMLSCollector(BaseCollector):
    """
    مجمع مصطلحات من UMLS Metathesaurus
    يتطلب API Key (مجاني للأكاديميين)
    """

    def __init__(self, config: dict = None):
        super().__init__("UMLS", "https://uts.nlm.nih.gov/", config)
        self.api_key = os.getenv("UMLS_API_KEY", "")
        self.auth_endpoint = "https://utslogin.nlm.nih.gov/cas/v1/api-key"
        self.rest_endpoint = "https://uts-ws.nlm.nih.gov/rest"
        self.tgt = None  # Ticket Granting Ticket

        if not self.api_key:
            self.logger.warning("⚠️ UMLS_API_KEY غير موجود. سيتم تخطي UMLS.")

    def _get_tgt(self) -> str:
        """الحصول على Ticket Granting Ticket"""
        if self.tgt:
            return self.tgt

        headers = {"Content-type": "application/x-www-form-urlencoded"}
        data = {"apikey": self.api_key}

        response = self.session.post(
            self.auth_endpoint,
            data=data,
            headers=headers,
            timeout=30
        )
        response.raise_for_status()

        # استخراج TGT من الـ Location header
        self.tgt = response.headers.get("Location")
        if not self.tgt:
            # fallback: استخراج من الـ HTML
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(response.text, 'html.parser')
            form = soup.find('form')
            if form:
                self.tgt = form.get('action')

        self.logger.info("✅ تم الحصول على TGT")
        return self.tgt

    def _get_service_ticket(self) -> str:
        """الحصول على Service Ticket"""
        tgt = self._get_tgt()

        headers = {"Content-type": "application/x-www-form-urlencoded"}
        data = {"service": "http://umlsks.nlm.nih.gov"}

        response = self.session.post(
            tgt,
            data=data,
            headers=headers,
            timeout=30
        )
        response.raise_for_status()

        return response.text

    def _make_authenticated_request(self, url: str, params: dict = None) -> dict:
        """طلب مع مصادقة UMLS"""
        ticket = self._get_service_ticket()

        if params is None:
            params = {}
        params["ticket"] = ticket

        response = self.session.get(url, params=params, timeout=30)

        # إذا انتهت صلاحية الـ TGT
        if response.status_code == 401:
            self.tgt = None
            ticket = self._get_service_ticket()
            params["ticket"] = ticket
            response = self.session.get(url, params=params, timeout=30)

        response.raise_for_status()
        return response.json()

    def collect(self) -> int:
        if not self.api_key:
            self.logger.warning("⏭️ UMLS_API_KEY غير موجود. يتم التخطي.")
            return 0

        new_count = 0

        try:
            # البحث عن مصطلحات طبية شائعة
            search_terms = [
                "diabetes", "hypertension", "pneumonia", "cancer",
                "heart disease", "stroke", "asthma", "arthritis",
                "depression", "alzheimer", "hepatitis", "tuberculosis"
            ]

            for search_term in search_terms:
                try:
                    # البحث في UMLS
                    search_url = f"{self.rest_endpoint}/search/current"
                    params = {
                        "string": search_term,
                        "searchType": "words",
                        "pageSize": 25,
                        "pageNumber": 1
                    }

                    data = self._make_authenticated_request(search_url, params)
                    results = data.get("result", {}).get("results", [])

                    for result in results:
                        ui = result.get("ui", "")
                        name = result.get("name", "")
                        root_source = result.get("rootSource", "UMLS")

                        if not name or ui == "NONE":
                            continue

                        # جلب التعريف التفصيلي
                        definition = self._get_concept_definition(ui)

                        entry = TermEntry(
                            term=name,
                            definition=definition or f"UMLS Concept: {name}",
                            source=f"UMLS:{root_source}",
                            language="en",
                            confidence=0.9,
                            tags=["umls", root_source.lower(), ui]
                        )

                        if self.add_term(entry):
                            new_count += 1

                    self.rate_limit(0.5)

                except Exception as e:
                    self.logger.error(f"خطأ في البحث عن '{search_term}': {e}")
                    continue

            self.logger.info(f"✅ UMLS: {new_count} مصطلح جديد")

        except Exception as e:
            self.logger.error(f"❌ فشل UMLS: {e}")
            raise

        return new_count

    def _get_concept_definition(self, cui: str) -> str:
        """جلب تعريف مفصل للمفهوم"""
        try:
            concept_url = f"{self.rest_endpoint}/content/current/CUI/{cui}"
            data = self._make_authenticated_request(concept_url)

            result = data.get("result", {})

            # محاولة الحصول على التعريف من المصادر المختلفة
            definitions = result.get("definitions", [])
            if definitions:
                return definitions[0].get("value", "")

            # fallback: استخدام الاسم المفضل
            return result.get("name", "")

        except Exception:
            return ""

"""
Collect medical terms from SNOMED CT via Snowstorm Public API.

⚠️ ملاحظة هامة:
Snowstorm Public API هو للاستخدام المرجعي فقط (reference only).
لا يجب استخدامه في أنظمة الإنتاج أو الرعاية الصحية.
للاستخدام الإنتاجي، يتطلب ترخيص SNOMED CT وخادم terminology خاص.

API Docs: https://snowstorm.ihtsdotools.org/snowstorm/snomed-ct/swagger-ui.html
"""

from collectors.base import BaseCollector, TermEntry


class SNOMEDCTCollector(BaseCollector):
    """
    مجمع مصطلحات من SNOMED CT عبر Snowstorm Public API
    للاستخدام المرجعي والبحثي فقط
    """

    def __init__(self, config: dict = None):
        super().__init__(
            "SNOMED_CT",
            "https://snowstorm.ihtsdotools.org/",
            config
        )
        self.api_base = "https://snowstorm.ihtsdotools.org/snowstorm/snomed-ct"
        self.branch = "MAIN"

        # فئات SNOMED CT الرئيسية للبحث
        self.search_categories = [
            {"term": "disease", "ecl": "<< 404684003"},      # Clinical finding
            {"term": "procedure", "ecl": "<< 71388002"},    # Procedure
            {"term": "substance", "ecl": "<< 105590001"},  # Substance
            {"term": "body structure", "ecl": "<< 123037004"},  # Body structure
            {"term": "organism", "ecl": "<< 410607006"},   # Organism
        ]

    def collect(self) -> int:
        new_count = 0

        try:
            for category in self.search_categories:
                try:
                    category_count = self._collect_category(
                        category["term"],
                        category["ecl"]
                    )
                    new_count += category_count
                    self.rate_limit(1.0)  # احترام rate limit

                except Exception as e:
                    self.logger.error(
                        f"خطأ في جمع فئة '{category['term']}': {e}"
                    )
                    continue

            self.logger.info(f"✅ SNOMED CT: {new_count} مصطلح جديد")

        except Exception as e:
            self.logger.error(f"❌ فشل SNOMED CT: {e}")
            raise

        return new_count

    def _collect_category(self, category_name: str, ecl: str) -> int:
        """جمع مصطلحات من فئة معينة"""
        new_count = 0

        # البحث عن المفاهيم في الفئة
        search_url = f"{self.api_base}/{self.branch}/concepts"
        params = {
            "ecl": ecl,
            "limit": 100,
            "offset": 0,
            "activeFilter": "true"
        }

        response = self.session.get(search_url, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()

        items = data.get("items", [])

        for item in items:
            concept_id = item.get("conceptId", "")
            fsn = item.get("fsn", {}).get("term", "")  # Fully Specified Name
            pt = item.get("pt", {}).get("term", "")     # Preferred Term

            # استخدام Preferred Term أو FSN
            term = pt or fsn
            if not term:
                continue

            # تنظيف المصطلح (إزالة (disorder) وما شابه)
            clean_term = self._clean_term(term)

            # جلب التعريف
            definition = self._get_concept_definition(concept_id)

            entry = TermEntry(
                term=clean_term,
                definition=definition or f"SNOMED CT: {clean_term}",
                source="SNOMED_CT",
                language="en",
                confidence=0.88,
                tags=["snomed", category_name, concept_id]
            )

            if self.add_term(entry):
                new_count += 1

            self.rate_limit(0.2)

        self.logger.info(f"📂 {category_name}: {new_count} مصطلح")
        return new_count

    def _get_concept_definition(self, concept_id: str) -> str:
        """جلب تعريف المفهوم"""
        try:
            concept_url = f"{self.api_base}/{self.branch}/concepts/{concept_id}"
            response = self.session.get(concept_url, timeout=30)
            response.raise_for_status()
            data = response.json()

            # محاولة الحصول على الوصف
            descriptions = data.get("descriptions", [])
            for desc in descriptions:
                if desc.get("type") == "DEFINITION":
                    return desc.get("term", "")

            # fallback: استخدام FSN
            return data.get("fsn", {}).get("term", "")

        except Exception:
            return ""

    def _clean_term(self, term: str) -> str:
        """تنظيف المصطلح من الأقواس التصنيفية"""
        import re
        # إزالة (disorder), (procedure), إلخ
        return re.sub(r'\s*\([^)]+\)$', '', term).strip()

"""
Collect medical terms from ICD-10-CM via NLM Clinical Table Search Service.
Free, no API key required.

API Docs: https://clinicaltables.nlm.nih.gov/apidoc/icd10cm/v3/doc.html
"""

from collectors.base import BaseCollector, TermEntry


class ICD10Collector(BaseCollector):
    """
    مجمع مصطلحات من ICD-10-CM
    مجاني تماماً - لا يتطلب API Key
    """

    def __init__(self, config: dict = None):
        super().__init__(
            "ICD-10-CM",
            "https://clinicaltables.nlm.nih.gov/",
            config
        )
        self.api_base = "https://clinicaltables.nlm.nih.gov/api/icd10cm/v3/search"

        # فئات بحث ICD-10-CM الرئيسية
        self.search_queries = [
            "diabetes", "hypertension", "pneumonia", "heart failure",
            "asthma", "stroke", "cancer", "fracture",
            "anemia", "hepatitis", "tuberculosis", "depression",
            "alzheimer", "arthritis", "migraine", "epilepsy"
        ]

    def collect(self) -> int:
        new_count = 0

        for query in self.search_queries:
            try:
                params = {
                    "terms": query,
                    "maxList": 50,
                    "sf": "code,name",  # search fields
                    "df": "code,name",  # display fields
                }

                response = self.session.get(
                    self.api_base,
                    params=params,
                    timeout=30
                )
                response.raise_for_status()
                data = response.json()

                # البنية: [count, [codes], [names], [...]]
                # data[1] = codes, data[2] = names
                codes = data[1] if len(data) > 1 else []
                names = data[2] if len(data) > 2 else []

                for code, name in zip(codes, names):
                    if not code or not name:
                        continue

                    entry = TermEntry(
                        term=name,
                        definition=f"ICD-10-CM Code: {code}",
                        source="ICD-10-CM",
                        language="en",
                        confidence=0.92,
                        tags=["icd10", code, query]
                    )

                    if self.add_term(entry):
                        new_count += 1

                self.rate_limit(0.3)

            except Exception as e:
                self.logger.error(f"خطأ في البحث عن '{query}': {e}")
                continue

        self.logger.info(f"✅ ICD-10-CM: {new_count} مصطلح جديد")
        return new_count

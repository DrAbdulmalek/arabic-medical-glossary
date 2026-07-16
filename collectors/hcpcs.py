"""
Collect medical terms from HCPCS (Healthcare Common Procedure Coding System) via NLM Clinical Table Search Service.
Free, no API key required.

HCPCS Level II covers items, supplies, and non-physician services not in CPT.
API Docs: https://clinicaltables.nlm.nih.gov/apidoc/hcpcs/v3/doc.html
"""

from collectors.base import BaseCollector, TermEntry


class HCPCSCollector(BaseCollector):
    """
    مجمع مصطلحات من HCPCS Level II
    مجاني تماماً - بدون API Key
    """

    def __init__(self, config: dict = None):
        super().__init__(
            "HCPCS",
            "https://clinicaltables.nlm.nih.gov/",
            config
        )
        self.api_base = "https://clinicaltables.nlm.nih.gov/api/hcpcs/v3/search"

        # فئات HCPCS الرئيسية (A-V)
        self.search_queries = [
            "transportation", "dental", "durable medical equipment",
            "prosthetics", "orthotics", "drugs", "lab", "radiology",
            "surgery", "therapy", "diagnostic", "vaccine"
        ]

    def collect(self) -> int:
        new_count = 0

        for query in self.search_queries:
            try:
                params = {
                    "terms": query,
                    "maxList": 50,
                    "sf": "code,desc",   # search fields
                    "df": "code,desc",   # display fields
                }

                response = self.session.get(
                    self.api_base,
                    params=params,
                    timeout=30
                )
                response.raise_for_status()
                data = response.json()

                # البنية: [count, [codes], [descriptions], [...]]
                codes = data[1] if len(data) > 1 else []
                descriptions = data[2] if len(data) > 2 else []

                for code, desc in zip(codes, descriptions):
                    if not code or not desc:
                        continue

                    # تحديد الفئة من الحرف الأول
                    category = self._get_category(code[0])

                    entry = TermEntry(
                        term=desc,
                        definition=f"HCPCS Level II Code: {code} ({category})",
                        source="HCPCS",
                        language="en",
                        confidence=0.93,
                        tags=["hcpcs", code, category.lower().replace(" ", "_")]
                    )

                    if self.add_term(entry):
                        new_count += 1

                self.rate_limit(0.3)

            except Exception as e:
                self.logger.error(f"خطأ في البحث عن '{query}': {e}")
                continue

        self.logger.info(f"✅ HCPCS: {new_count} مصطلح جديد")
        return new_count

    def _get_category(self, letter: str) -> str:
        """تحديد فئة HCPCS من الحرف الأول"""
        categories = {
            "A": "Transportation",
            "B": "Enteral and Parenteral Therapy",
            "C": "Temporary Codes",
            "D": "Dental Procedures",
            "E": "Durable Medical Equipment",
            "G": "Temporary Procedures",
            "H": "Behavioral Health",
            "J": "Drugs",
            "K": "Temporary Codes",
            "L": "Orthotics and Prosthetics",
            "M": "Medical Services",
            "P": "Pathology and Laboratory",
            "Q": "Temporary Codes",
            "R": "Diagnostic Radiology",
            "S": "Temporary National Codes",
            "T": "State Medicaid Agency",
            "U": "Medicare",
            "V": "Vision/Hearing Services"
        }
        return categories.get(letter.upper(), "Other")

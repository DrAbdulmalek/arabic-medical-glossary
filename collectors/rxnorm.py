"""
Collect medical terms from RxNorm via NLM RxNav REST API.
Free, no API key required.

API Docs: https://lhncbc.nlm.nih.gov/RxNav/APIs/RxNormAPIs.html
Base URL: https://rxnav.nlm.nih.gov/REST
"""

from collectors.base import BaseCollector, TermEntry


class RxNormCollector(BaseCollector):
    """
    مجمع مصطلحات من RxNorm (أسماء الأدوية الموحدة)
    مجاني تماماً - لا يتطلب API Key
    """

    def __init__(self, config: dict = None):
        super().__init__(
            "RxNorm",
            "https://rxnav.nlm.nih.gov/",
            config
        )
        self.api_base = "https://rxnav.nlm.nih.gov/REST"

        # أدوية شائعة للبحث
        self.drug_names = [
            "aspirin", "ibuprofen", "acetaminophen", "amoxicillin",
            "metformin", "atorvastatin", "lisinopril", "amlodipine",
            "omeprazole", "albuterol", "insulin", "warfarin",
            "prednisone", "azithromycin", "ciprofloxacin", "fluconazole"
        ]

    def collect(self) -> int:
        new_count = 0

        for drug_name in self.drug_names:
            try:
                # البحث عن الدواء
                search_url = f"{self.api_base}/drugs.json"
                params = {"name": drug_name}

                response = self.session.get(
                    search_url,
                    params=params,
                    timeout=30
                )
                response.raise_for_status()
                data = response.json()

                # استخراج المفاهيم
                concept_groups = data.get("drugGroup", {}).get("conceptGroup", [])

                for group in concept_groups:
                    tty = group.get("tty", "")  # term type
                    concepts = group.get("conceptProperties", [])

                    for concept in concepts:
                        rxcui = concept.get("rxcui", "")
                        name = concept.get("name", "")
                        synonym = concept.get("synonym", "")

                        if not name:
                            continue

                        # جلب معلومات إضافية
                        related_info = self._get_related_info(rxcui)

                        definition = f"RxNorm {tty}: {name}"
                        if related_info.get("ingredient"):
                            definition += f" | المادة الفعالة: {related_info['ingredient']}"

                        entry = TermEntry(
                            term=name,
                            definition=definition,
                            source="RxNorm",
                            language="en",
                            confidence=0.88,
                            tags=["rxnorm", rxcui, tty, drug_name]
                        )

                        if self.add_term(entry):
                            new_count += 1

                        # إضافة المرادف إن وجد
                        if synonym and synonym != name:
                            entry_syn = TermEntry(
                                term=synonym,
                                definition=f"Synonym for {name} (RxNorm)",
                                source="RxNorm",
                                language="en",
                                confidence=0.75,
                                tags=["rxnorm", rxcui, "synonym", drug_name]
                            )
                            if self.add_term(entry_syn):
                                new_count += 1

                self.rate_limit(0.3)

            except Exception as e:
                self.logger.error(f"خطأ في البحث عن '{drug_name}': {e}")
                continue

        self.logger.info(f"✅ RxNorm: {new_count} مصطلح جديد")
        return new_count

    def _get_related_info(self, rxcui: str) -> dict:
        """جلب معلومات إضافية عن الدواء"""
        info = {}

        try:
            url = f"{self.api_base}/rxcui/{rxcui}/allrelated.json"
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            data = response.json()

            concept_groups = data.get("allRelatedGroup", {}).get("conceptGroup", [])

            for group in concept_groups:
                tty = group.get("tty", "")
                if tty == "IN":  # Ingredient
                    concepts = group.get("conceptProperties", [])
                    if concepts:
                        info["ingredient"] = concepts[0].get("name", "")
                        break

            return info

        except Exception:
            return info

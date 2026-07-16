"""
Collect medical terms from Wikidata SPARQL endpoint.
"""

from collectors.base import BaseCollector, TermEntry


class WikidataCollector(BaseCollector):
    """مجمع مصطلحات طبية من Wikidata"""

    def __init__(self, config: dict = None):
        super().__init__("Wikidata", "https://www.wikidata.org/", config)
        self.sparql_endpoint = "https://query.wikidata.org/sparql"

    def collect(self) -> int:
        new_count = 0

        # استعلام للمصطلحات الطبية مع التعريفات
        query = """
        SELECT ?item ?itemLabel ?itemDescription ?arLabel ?arDescription
        WHERE {
            ?item wdt:P31 wd:Q12136 .  # instance of disease
            SERVICE wikibase:label {
                bd:serviceParam wikibase:language "en,ar" .
            }
        }
        LIMIT 2000
        """

        headers = {
            "Accept": "application/sparql-results+json",
            "User-Agent": "MedicalGlossaryBot/1.0"
        }

        try:
            response = self.session.get(
                self.sparql_endpoint,
                params={"query": query},
                headers=headers,
                timeout=60
            )
            response.raise_for_status()

            data = response.json()
            results = data.get("results", {}).get("bindings", [])

            for result in results:
                en_term = result.get("itemLabel", {}).get("value", "")
                en_def = result.get("itemDescription", {}).get("value", "")
                ar_term = result.get("arLabel", {}).get("value", "")
                ar_def = result.get("arDescription", {}).get("value", "")

                # إضافة المصطلح الإنجليزي
                if en_term:
                    entry = TermEntry(
                        term=en_term,
                        definition=en_def or f"Wikidata: {en_term}",
                        source="Wikidata",
                        language="en",
                        confidence=0.85
                    )
                    if self.add_term(entry):
                        new_count += 1

                # إضافة المصطلح العربي إن وجد
                if ar_term and ar_term != en_term:
                    entry = TermEntry(
                        term=ar_term,
                        definition=ar_def or en_def or f"Wikidata: {ar_term}",
                        source="Wikidata",
                        language="ar",
                        confidence=0.8
                    )
                    if self.add_term(entry):
                        new_count += 1

                self.rate_limit(0.2)

        except Exception as e:
            self.logger.error(f"خطأ في جمع Wikidata: {e}")
            raise

        return new_count

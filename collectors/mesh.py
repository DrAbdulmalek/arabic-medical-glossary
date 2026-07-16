"""
Collect medical terms from MeSH (Medical Subject Headings) via SPARQL.
"""

from collectors.base import BaseCollector, TermEntry


class MeSHCollector(BaseCollector):
    """مجمع مصطلحات من MeSH"""

    def __init__(self, config: dict = None):
        super().__init__("MeSH", "https://id.nlm.nih.gov/mesh/", config)
        self.sparql_endpoint = "https://id.nlm.nih.gov/mesh/sparql"

    def collect(self) -> int:
        new_count = 0

        query = """
        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
        PREFIX meshv: <http://id.nlm.nih.gov/mesh/vocab#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

        SELECT ?concept ?label ?definition
        WHERE {
            ?concept rdf:type meshv:TopicalDescriptor .
            ?concept rdfs:label ?label .
            OPTIONAL { ?concept meshv:scopeNote ?definition . }
        }
        LIMIT 5000
        """

        headers = {
            "Accept": "application/sparql-results+json",
            "Content-Type": "application/x-www-form-urlencoded"
        }

        try:
            response = self.session.post(
                self.sparql_endpoint,
                data={"query": query},
                headers=headers,
                timeout=60
            )
            response.raise_for_status()

            data = response.json()
            results = data.get("results", {}).get("bindings", [])

            for result in results:
                term = result.get("label", {}).get("value", "")
                definition = result.get("definition", {}).get("value", "")

                if term:
                    entry = TermEntry(
                        term=term,
                        definition=definition or f"MeSH Descriptor: {term}",
                        source="MeSH",
                        language="en",
                        confidence=0.95
                    )
                    if self.add_term(entry):
                        new_count += 1

                self.rate_limit(0.1)

        except Exception as e:
            self.logger.error(f"خطأ في جمع MeSH: {e}")
            raise

        return new_count

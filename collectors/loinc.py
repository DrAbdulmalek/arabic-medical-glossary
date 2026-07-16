"""
Collect medical terms from LOINC via FHIR Terminology Server.
Requires free LOINC account (Basic Auth).

API Docs: https://loinc.org/fhir/
Base URL: https://fhir.loinc.org
"""

import os
from collectors.base import BaseCollector, TermEntry


class LOINCCollector(BaseCollector):
    """
    مجمع مصطلحات من LOINC (Logical Observation Identifiers Names and Codes)
    يتطلب حساب LOINC مجاني
    """

    def __init__(self, config: dict = None):
        super().__init__(
            "LOINC",
            "https://loinc.org/",
            config
        )
        self.api_base = "https://fhir.loinc.org"
        self.username = os.getenv("LOINC_USERNAME", "")
        self.password = os.getenv("LOINC_PASSWORD", "")

        if not self.username or not self.password:
            self.logger.warning(
                "⚠️ LOINC_USERNAME/LOINC_PASSWORD غير موجود. "
                "سجّل مجاناً في https://loinc.org/login/"
            )

    def collect(self) -> int:
        if not self.username or not self.password:
            self.logger.warning("⏭️ بيانات LOINC غير موجودة. يتم التخطي.")
            return 0

        new_count = 0

        # استعلام FHIR للحصول على مصطلحات LOINC شائعة
        # نستخدم $lookup للحصول على تفاصيل مصطلحات معروفة
        common_codes = [
            "4544-3",   # Hematocrit
            "718-7",    # Hemoglobin
            "787-2",    # Erythrocyte mean corpuscular volume
            "777-3",    # Platelets
            "6690-2",   # Leukocytes
            "2345-7",   # Glucose
            "3094-0",   # Urea nitrogen
            "2160-0",   # Creatinine
            "2951-2",   # Sodium
            "2823-3",   # Potassium
            "2093-3",   # Cholesterol
            "2571-8",   # Triglycerides
            "13457-7",  # LDL Cholesterol
            "2085-9",   # HDL Cholesterol
            "33717-0",  # C-reactive protein
            "21176-3",  # COVID-19
        ]

        for code in common_codes:
            try:
                url = f"{self.api_base}/CodeSystem/http://loinc.org/$lookup"
                params = {
                    "code": code,
                    "_format": "json"
                }

                response = self.session.get(
                    url,
                    params=params,
                    auth=(self.username, self.password),
                    timeout=30
                )

                if response.status_code == 401:
                    self.logger.error("❌ فشل مصادقة LOINC. تحقق من بيانات الدخول.")
                    return new_count

                response.raise_for_status()
                data = response.json()

                # استخراج الاسم والتعريف
                parameter = data.get("parameter", [])

                name = ""
                definition = ""

                for param in parameter:
                    param_name = param.get("name", "")
                    if param_name == "name":
                        name = param.get("valueString", "")
                    elif param_name == "display":
                        if not name:
                            name = param.get("valueString", "")
                    elif param_name == "designation":
                        # يمكن أن يحتوي على تعريفات إضافية
                        pass

                # جلب خصائص إضافية
                properties = self._get_code_properties(code)

                if name:
                    entry = TermEntry(
                        term=name,
                        definition=properties.get("definition") or f"LOINC Code: {code}",
                        source="LOINC",
                        language="en",
                        confidence=0.9,
                        tags=["loinc", code, properties.get("class", "")]
                    )

                    if self.add_term(entry):
                        new_count += 1

                self.rate_limit(0.5)

            except Exception as e:
                self.logger.error(f"خطأ في جلب LOINC {code}: {e}")
                continue

        self.logger.info(f"✅ LOINC: {new_count} مصطلح جديد")
        return new_count

    def _get_code_properties(self, code: str) -> dict:
        """جلب خصائص إضافية للكود"""
        try:
            url = f"{self.api_base}/CodeSystem/http://loinc.org/$lookup"
            params = {
                "code": code,
                "property": "*",
                "_format": "json"
            }

            response = self.session.get(
                url,
                params=params,
                auth=(self.username, self.password),
                timeout=30
            )
            response.raise_for_status()
            data = response.json()

            properties = {}
            for param in data.get("parameter", []):
                if param.get("name") == "property":
                    part = param.get("part", [])
                    prop_code = ""
                    prop_value = ""
                    for p in part:
                        if p.get("name") == "code":
                            prop_code = p.get("valueCode", "")
                        elif p.get("name") == "value":
                            prop_value = p.get("valueString", "")

                    if prop_code == "DefinitionDescription":
                        properties["definition"] = prop_value
                    elif prop_code == "CLASS":
                        properties["class"] = prop_value

            return properties

        except Exception:
            return {}

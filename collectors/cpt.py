"""
CPT (Current Procedural Terminology) Codes Collector

⚠️ ⚠️ ⚠️ تحذير هام جداً:
CPT codes تملكها AMA (American Medical Association) وهي **مدفوعة**.
لا يوجد API مجاني للوصول لها.

للاستخدام القانوني:
1. شراء ترخيص من AMA: https://www.ama-assn.org/practice-management/cpt
2. أو استخدام بدائل مجانية:
   - HCPCS (Healthcare Common Procedure Coding System) - مجاني من CMS
   - SNOMED CT للإجراءات الطبية
   - ICD-10-PCS للإجراءات داخل المستشفيات

هذا الملف placeholder فقط. لا يمكن تشغيله بدون ترخيص CPT صالح.
"""

from collectors.base import BaseCollector


class CPTCollector(BaseCollector):
    """
    مجمع placeholder لـ CPT codes
    يتطلب ترخيص AMA مدفوع
    """

    def __init__(self, config: dict = None):
        super().__init__(
            "CPT",
            "https://www.ama-assn.org/practice-management/cpt",
            config
        )

    def collect(self) -> int:
        self.logger.error(
            "❌ CPT codes تتطلب ترخيص AMA مدفوع.\n"
            "البدائل المجانية المتاحة:\n"
            "- HCPCS: https://www.cms.gov/medicare/coding/hcpcsreleasecodesets\n"
            "- SNOMED CT للإجراءات\n"
            "- ICD-10-PCS للإجراءات داخل المستشفيات"
        )
        return 0

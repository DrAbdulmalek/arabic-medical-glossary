"""
RadLex (Radiology Lexicon) Collector

RadLex is a unified language of radiology terms developed by RSNA.
It provides standardized terminology for radiology reporting and imaging.

⚠️ ملاحظة:
RadLex لا يوفر REST API مباشر للجمع التلقائي.
المصطلحات متاحة عبر:
1. BioPortal: https://bioportal.bioontology.org/ontologies/RADLEX
2. ملف OWL/RDF للتحميل

للحصول على RadLex:
https://www.rsna.org/practice-management/data-science-and-ai/radlex

هذا الملف placeholder — يمكن توسيعه إذا توفر API مستقبلاً.
"""

from collectors.base import BaseCollector


class RadLexCollector(BaseCollector):
    """
    مجمع placeholder لـ RadLex
    يتطلب تحميل ملف OWL/RDF يدوي أو استخدام BioPortal
    """

    def __init__(self, config: dict = None):
        super().__init__(
            "RadLex",
            "https://www.rsna.org/practice-management/data-science-and-ai/radlex",
            config
        )

    def collect(self) -> int:
        self.logger.warning(
            "⚠️ RadLex لا يوفر API مباشر للجمع التلقائي.\n"
            "البدائل المتاحة:\n"
            "1. BioPortal: https://bioportal.bioontology.org/ontologies/RADLEX\n"
            "2. تحميل ملف OWL من موقع RSNA\n"
            "3. استخدام SNOMED CT (يحتوي على مصطلحات التصوير الطبي)"
        )
        return 0

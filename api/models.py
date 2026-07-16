"""
نماذج Pydantic لـ REST API — طلبات واستجابات المسارد الطبية.
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


# ─── نماذج المصطلح ───────────────────────────────────────────────

class TermResponse(BaseModel):
    """مصطلح واحد في الاستجابة"""
    term: str = Field(..., description="المصطلح", examples=["Diabetes"])
    definition: str = Field(..., description="التعريف / الترجمة", examples=["السكري"])
    source: str = Field(..., description="مصدر المصطلح", examples=["MeSH", "Wikidata"])
    language: str = Field(..., description="لغة المصطلح (ar/en)", examples=["ar", "en"])
    confidence: float = Field(..., ge=0, le=1, description="مستوى الثقة (0-1)")
    tags: List[str] = Field(default_factory=list, description="الوسوم")
    date_added: Optional[str] = Field(None, description="تاريخ الإضافة")

    model_config = {"from_attributes": True}


class TermPair(BaseModel):
    """زوج مصطلح ثنائي اللغة"""
    en_term: str = Field(..., description="المصطلح الإنجليزي")
    ar_term: str = Field(..., description="المصطلح العربي")
    en_definition: str = Field(default="", description="التعريف الإنجليزي")
    ar_definition: str = Field(default="", description="التعريف العربي")
    source: str = Field(default="")
    confidence: float = Field(default=0.0)


# ─── نماذج البحث ─────────────────────────────────────────────────

class SearchRequest(BaseModel):
    """معاملات البحث المتقدم"""
    query: str = Field(..., min_length=1, description="نص البحث", examples=["سكري", "diabetes"])
    language: Optional[str] = Field(None, description="تصفية حسب اللغة (ar/en)", pattern="^(ar|en)$")
    source: Optional[str] = Field(None, description="تصفية حسب المصدر")
    min_confidence: Optional[float] = Field(None, ge=0, le=1, description="الحد الأدنى للثقة")
    tags: Optional[List[str]] = Field(None, description="تصفية حسب الوسوم")
    limit: int = Field(20, ge=1, le=200, description="عدد النتائج الأقصى")
    offset: int = Field(0, ge=0, description="عدد النتائج للتخطي (pagination)")


# ─── نماذج الاستجابة العامة ─────────────────────────────────────

class PaginatedResponse(BaseModel):
    """استجابة مُصفَّحة"""
    results: List[TermResponse] = Field(..., description="قائمة النتائج")
    total: int = Field(..., description="إجمالي النتائج المتطابقة")
    limit: int = Field(..., description="عدد النتائج في هذه الصفحة")
    offset: int = Field(..., description="موضع البداية")
    query: Optional[str] = Field(None, description="نص البحث الأصلي")


class StatsResponse(BaseModel):
    """إحصائيات المسرد"""
    total_terms: int = Field(..., description="إجمالي المصطلحات")
    by_language: Dict[str, int] = Field(..., description="عدد المصطلحات حسب اللغة")
    by_source: Dict[str, int] = Field(..., description="عدد المصطلحات حسب المصدر")
    sources: List[Dict[str, Any]] = Field(default_factory=list, description="تفاصيل المصادر")
    metadata: Dict[str, Any] = Field(default_factory=dict)


class SourceInfo(BaseModel):
    """معلومات عن مصدر واحد"""
    name: str
    terms_count: int
    file: Optional[str] = None


class HealthResponse(BaseModel):
    """فحص صحة الخادم"""
    status: str = Field("ok", examples=["ok"])
    version: str
    total_terms: int
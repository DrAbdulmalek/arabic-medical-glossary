"""
REST API للمسارد الطبية العربية-الإنجليزية.
FastAPI مع بحث نصي، تصفح، تصفية، و pagination.
"""

from __future__ import annotations

import os
import uvicorn
from typing import List, Optional, Dict, Any
from contextlib import asynccontextmanager

from fastapi import FastAPI, Query, HTTPException, Path as PathParam
from fastapi.middleware.cors import CORSMiddleware

from api.models import (
    TermResponse,
    TermPair,
    SearchRequest,
    PaginatedResponse,
    StatsResponse,
    HealthResponse,
    SourceInfo,
)
from api.service import GlossaryService

# ─── التهيئة ─────────────────────────────────────────────────────

service = GlossaryService()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """تحميل البيانات عند بدء التشغيل."""
    print(f"✅ تم تحميل {service.total_terms:,} مصطلح")
    yield
    print("👋 إيقاف الخادم")


app = FastAPI(
    title="Arabic-English Medical Glossary API",
    description="""
    واجهة برمجة تطبيقات للبحث في المسارد الطبية ثنائية اللغة.

    ## المميزات
    - 🔍 **بحث نصي** في المصطلحات والتعريفات (عربي + إنجليزي)
    - 🔄 **بحث ثنائي اللغة** — ابحث بـ EN واحصل على AR والعكس
    - 📄 **Pagination** كامل مع limit/offset
    - 🏷️ **تصفية** حسب اللغة، المصدر، الثقة، والوسوم
    - 📊 **إحصائيات** شاملة عن المسرد
    - 🎲 **مصطلحات عشوائية** للعرض في الواجهات
    """,
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

__version__ = "1.0.0-rc1"


# ─── Root & Health ───────────────────────────────────────────────

@app.get("/", tags=["Health"])
async def root():
    """نقطة البداية — معلومات أساسية عن API."""
    return {
        "name": "Arabic-English Medical Glossary API",
        "version": __version__,
        "total_terms": service.total_terms,
        "docs": "/docs",
    }


@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    """فحص صحة الخادم وعدد المصطلحات المحملة."""
    return HealthResponse(
        status="ok",
        version=__version__,
        total_terms=service.total_terms,
    )


# ─── البحث ───────────────────────────────────────────────────────

@app.get(
    "/search",
    response_model=PaginatedResponse,
    summary="بحث نصي في المصطلحات",
    description="بحث في المصطلحات والتعريفات مع دعم ثنائي اللغة التلقائي.",
    tags=["Search"],
)
async def search_get(
    q: str = Query(..., min_length=1, description="نص البحث", examples=["diabetes", "سكري"]),
    language: Optional[str] = Query(None, description="تصفية: ar أو en"),
    source: Optional[str] = Query(None, description="تصفية حسب المصدر"),
    min_confidence: Optional[float] = Query(None, ge=0, le=1, description="الحد الأدنى للثقة"),
    tag: Optional[str] = Query(None, description="تصفية حسب وسم (متعدد ممكن)"),
    limit: int = Query(20, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """بحث بسيط عبر GET — مناسب للروابط المباشرة."""
    tags = tag.split(",") if tag else None
    results, total = service.search(
        query=q,
        language=language,
        source=source,
        min_confidence=min_confidence,
        tags=tags,
        limit=limit,
        offset=offset,
    )
    return PaginatedResponse(
        results=results,
        total=total,
        limit=limit,
        offset=offset,
        query=q,
    )


@app.post("/search", response_model=PaginatedResponse, tags=["Search"])
async def search_post(req: SearchRequest):
    """بحث متقدم عبر POST — يدعم قوائم الوسوم المتعددة."""
    results, total = service.search(
        query=req.query,
        language=req.language,
        source=req.source,
        min_confidence=req.min_confidence,
        tags=req.tags,
        limit=req.limit,
        offset=req.offset,
    )
    return PaginatedResponse(
        results=results,
        total=total,
        limit=req.limit,
        offset=req.offset,
        query=req.query,
    )


# ─── التصفح ──────────────────────────────────────────────────────

@app.get(
    "/terms",
    response_model=PaginatedResponse,
    summary="تصفح المصطلحات",
    description="تصفح جميع المصطلحات مع تصفية حسب اللغة والمصدر.",
    tags=["Browse"],
)
async def browse_terms(
    language: Optional[str] = Query(None, description="ar أو en"),
    source: Optional[str] = Query(None, description="اسم المصدر"),
    limit: int = Query(20, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """تصفح المصطلحات معPagination وفلترة."""
    results, total = service.browse(
        language=language,
        source=source,
        limit=limit,
        offset=offset,
    )
    return PaginatedResponse(
        results=results,
        total=total,
        limit=limit,
        offset=offset,
        query=None,
    )


@app.get(
    "/terms/{term}",
    response_model=List[TermResponse],
    summary="جلب مصطلح محدد",
    description="جلب جميع إصدارات المصطلح من مصادر مختلفة.",
    tags=["Browse"],
)
async def get_term(
    term: str = PathParam(..., description="المصطلح المطلوب", examples=["diabetes", "السكري"]),
):
    """جلب مصطلح محدد بجميع ترجماته ومصادره."""
    matches = service.get_term(term)
    if not matches:
        raise HTTPException(status_code=404, detail=f"المصطلح '{term}' غير موجود")
    return matches


# ─── الأزواج ثنائية اللغة ────────────────────────────────────────

@app.get(
    "/pairs/{term}",
    response_model=List[TermPair],
    summary="أزواج EN-AR",
    description="جلب الأزواج ثنائية اللغة لمصطلح معين.",
    tags=["Pairs"],
)
async def get_pairs(
    term: str = PathParam(..., description="المصطلح (EN أو AR)", examples=["diabetes", "السكري"]),
):
    """جلب أزواج الترجمة الإنجليزية-العربية."""
    pairs = service.get_bilingual_pairs(term)
    if not pairs:
        raise HTTPException(status_code=404, detail=f"لا توجد أزواج للمصطلح '{term}'")
    return pairs


# ─── عشوائي ──────────────────────────────────────────────────────

@app.get(
    "/random",
    response_model=List[TermResponse],
    summary="مصطلحات عشوائية",
    description="مصطلحات عشوائية — مفيدة للواجهات والعرض.",
    tags=["Browse"],
)
async def random_terms(
    count: int = Query(5, ge=1, le=50, description="عدد المصطلحات"),
    language: Optional[str] = Query(None, description="ar أو en"),
):
    """مصطلحات عشوائية من المسرد."""
    return service.random_terms(count=count, language=language)


# ─── الإحصائيات ──────────────────────────────────────────────────

@app.get(
    "/stats",
    response_model=StatsResponse,
    summary="إحصائيات المسرد",
    description="إحصائيات شاملة: عدد المصطلحات حسب اللغة والمصدر.",
    tags=["Stats"],
)
async def get_stats():
    """إحصائيات شاملة عن المسرد."""
    return service.get_stats()


@app.get("/sources", response_model=List[SourceInfo], tags=["Stats"])
async def list_sources():
    """قائمة المصادر المتاحة."""
    stats = service.get_stats()
    return [SourceInfo(**s) for s in stats.get("sources", [])]


# ─── إعادة التحميل ───────────────────────────────────────────────

@app.post("/reload", tags=["Admin"])
async def reload_data():
    """إعادة تحميل البيانات من القرص (بعد تحديث المسرد)."""
    service.reload()
    return {"message": "تم إعادة التحميل", "total_terms": service.total_terms}


# ─── تشغيل مباشر ────────────────────────────────────────────────

if __name__ == "__main__":
    port = int(os.getenv("API_PORT", "8000"))
    uvicorn.run("api.main:app", host="0.0.0.0", port=port, reload=True)
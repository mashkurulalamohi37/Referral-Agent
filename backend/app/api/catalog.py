"""Catalog API endpoints (§20, ADR 0019)."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db_session
from app.catalog import service as catalog_service
from app.core.errors import ErrorCode, PlatformError

router = APIRouter(tags=["catalog"])


@router.get("/products")
async def list_products(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict[str, Any]:
    """Lists all active products in the catalog."""
    products = await catalog_service.list_products(session)
    return {
        "success": True,
        "data": [
            {
                "id": str(p.id),
                "slug": p.slug,
                "name": p.name,
                "status": p.status,
                "signup_url": p.signup_url,
                "referrer_visibility": p.referrer_visibility,
                "attribution_window_days": p.attribution_window_days,
                "confirmation_days": p.confirmation_days,
            }
            for p in products
        ],
    }


@router.get("/products/{slug}")
async def get_product(
    slug: str,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict[str, Any]:
    """Retrieves product details by slug."""
    product = await catalog_service.get_product_by_slug(session, slug)
    if not product:
        raise PlatformError(ErrorCode.PRODUCT_NOT_FOUND, f"Product '{slug}' not found")

    return {
        "success": True,
        "data": {
            "id": str(product.id),
            "slug": product.slug,
            "name": product.name,
            "status": product.status,
            "signup_url": product.signup_url,
            "referrer_visibility": product.referrer_visibility,
            "attribution_window_days": product.attribution_window_days,
            "confirmation_days": product.confirmation_days,
            "credit_max_invoice_pct": product.credit_max_invoice_pct,
            "theme": product.theme,
        },
    }


@router.get("/public/products/{slug}/theme")
async def get_product_theme(
    slug: str,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict[str, Any]:
    """Public theming endpoint for embeddable components and branded portal views (ADR 0019)."""
    product = await catalog_service.get_product_by_slug(session, slug)
    if not product:
        raise PlatformError(ErrorCode.PRODUCT_NOT_FOUND, f"Product '{slug}' not found")

    return {
        "success": True,
        "data": {
            "slug": product.slug,
            "name": product.name,
            "theme": product.theme or {},
        },
    }

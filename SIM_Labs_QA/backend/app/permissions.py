from fastapi import HTTPException
from .auth import Principal

EXECUTIVE = {"executive"}
AUDIT_READ = {"executive", "auditor"}
TEAM_READ = {"executive", "operations", "product", "qa", "ux", "business", "engineering", "security", "red_team", "sac", "marketing", "analytics", "release_manager", "auditor"}
PRODUCT_MANAGE = {"executive", "operations", "product"}


def require_any(principal: Principal, allowed: set[str]) -> None:
    if not principal.roles.intersection(allowed):
        raise HTTPException(status_code=403, detail="Permission denied")


def can_access_product(principal: Principal, product_id: str) -> bool:
    return "executive" in principal.roles or product_id in principal.product_ids

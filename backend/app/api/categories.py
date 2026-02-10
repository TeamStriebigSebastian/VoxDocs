from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from loguru import logger
from pydantic import BaseModel

from app.core.database import get_db
from app.models import CategoryDefinition, Group, User, UserRole
from app.core.dependencies import get_current_active_user
from app.core.llm import llm_client

router = APIRouter(prefix="/categories", tags=["Categories"])

# --- Authorization Helper ---

def check_group_permission(user: User, group_id: int, required_role: UserRole):
    """
    Check if user has specific role (or higher) in the target group.
    Admin is allowed everywhere.
    """
    # 1. Check Global Admin (via max role or explicit is_superuser flag if we trust it, 
    # but let's check roles for correctness)
    # (Simplified: User check)
    
    # Check if user has ADMIN role in any group (Platform Admin) or specific group role
    # For V1, let's look for matching group_id
    
    has_permission = False
    
    for gr in user.group_roles:
        # Platform Admin (Global) - usually assigned to a specialized group or flagged
        if gr.role == UserRole.ADMIN:
            has_permission = True
            break
            
        if gr.group_id == group_id:
            # Check hierarchy
            role_hierarchy = {
                UserRole.ADMIN: 4,
                UserRole.SUPERUSER: 3,
                UserRole.USER: 2,
                UserRole.VIEWER: 1
            }
            if role_hierarchy.get(gr.role, 0) >= role_hierarchy.get(required_role, 0):
                has_permission = True
                break
    
    if not has_permission:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Insufficient permissions for group {group_id}. Required: {required_role.value}"
        )

# --- Pydantic Models ---
class CategoryCreate(BaseModel):
    group_id: int
    name: str
    guidelines: Optional[str] = None
    keywords: Optional[str] = None
    structure_schema: Optional[dict] = {}
    prompt_template: Optional[str] = None

class CategoryUpdate(BaseModel):
    name: Optional[str] = None
    guidelines: Optional[str] = None
    keywords: Optional[str] = None
    structure_schema: Optional[dict] = None
    prompt_template: Optional[str] = None

class CategoryResponse(BaseModel):
    id: int
    group_id: int
    name: str
    guidelines: Optional[str]
    keywords: Optional[str]
    structure_schema: dict
    prompt_template: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True

# --- Endpoints ---

@router.post("/", response_model=CategoryResponse)
async def create_category(
    category_in: CategoryCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new category definition (Superuser only)."""
    check_group_permission(current_user, category_in.group_id, UserRole.SUPERUSER)
    
    try:
        # Validate group exists
        group = await db.scalar(select(Group).where(Group.id == category_in.group_id))
        if not group:
            raise HTTPException(status_code=404, detail="Group not found")

        new_category = CategoryDefinition(
            group_id=category_in.group_id,
            name=category_in.name,
            guidelines=category_in.guidelines,
            keywords=category_in.keywords,
            structure_schema=category_in.structure_schema or {},
            prompt_template=category_in.prompt_template or llm_client.DEFAULT_CATEGORIZE_PROMPT,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        db.add(new_category)
        await db.commit()
        await db.refresh(new_category)
        
        return new_category
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating category: {e}")
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/", response_model=List[CategoryResponse])
async def list_categories(
    group_id: int = Query(..., description="Filter by Group ID"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """List categories for a group (Any User in group)."""
    check_group_permission(current_user, group_id, UserRole.VIEWER)
    
    try:
        query = select(CategoryDefinition).where(CategoryDefinition.group_id == group_id).order_by(CategoryDefinition.name)
        result = await db.execute(query)
        categories = result.scalars().all()
        # Fallback to default prompt for display
        for cat in categories:
            if not cat.prompt_template:
                cat.prompt_template = llm_client.DEFAULT_CATEGORIZE_PROMPT
        return categories
    except Exception as e:
        logger.error(f"Error listing categories: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{id}", response_model=CategoryResponse)
async def get_category(
    id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get category details."""
    try:
        category = await db.get(CategoryDefinition, id)
        if not category:
            raise HTTPException(status_code=404, detail="Category not found")
            
        # Check permission for this category's group
        check_group_permission(current_user, category.group_id, UserRole.VIEWER)
        
        if not category.prompt_template:
            category.prompt_template = llm_client.DEFAULT_CATEGORIZE_PROMPT
            
        return category
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting category: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/{id}", response_model=CategoryResponse)
async def update_category(
    id: int,
    category_in: CategoryUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Update a category (Superuser only)."""
    try:
        category = await db.get(CategoryDefinition, id)
        if not category:
            raise HTTPException(status_code=404, detail="Category not found")
            
        # Check permission for this category's group
        check_group_permission(current_user, category.group_id, UserRole.SUPERUSER)
            
        if category_in.name is not None:
            category.name = category_in.name
        if category_in.guidelines is not None:
            category.guidelines = category_in.guidelines
        if category_in.keywords is not None:
            category.keywords = category_in.keywords
        if category_in.structure_schema is not None:
            category.structure_schema = category_in.structure_schema
        if category_in.prompt_template is not None:
            category.prompt_template = category_in.prompt_template
            
        category.updated_at = datetime.utcnow()
        await db.commit()
        await db.refresh(category)
        return category
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating category: {e}")
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{id}", status_code=204)
async def delete_category(
    id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete a category (Superuser only)."""
    try:
        category = await db.get(CategoryDefinition, id)
        if not category:
            raise HTTPException(status_code=404, detail="Category not found")
        
        # Check permission
        check_group_permission(current_user, category.group_id, UserRole.SUPERUSER)
        
        await db.delete(category)
        await db.commit()
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting category: {e}")
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

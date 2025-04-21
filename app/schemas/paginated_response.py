from fastapi import HTTPException, status
from sqlalchemy.orm import Query
from sqlalchemy import func
from typing import TypeVar, Generic, List, Type
from pydantic import BaseModel
from math import ceil

T = TypeVar('T')


class PaginatedResponse(BaseModel, Generic[T]):
    data: List[T]
    total: int
    skip: int
    limit: int
    has_more: bool


def paginate_query(
        query: Query,
        page: int,
        items_per_page: int,
        response_model: Type[BaseModel]
) -> PaginatedResponse:
    try:
        page = int(page)
        items_per_page = int(items_per_page)
        if page < 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Page must be greater than 0"
            )

        if items_per_page < 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Items per page must be greater than 0"
            )
        if hasattr(query, '_entities') and len(query._entities) > 1:
            base_entity = query._entities[0].entity_zero
            total_query = Query(func.count(base_entity.id))
            total_query = total_query.select_from(query.subquery())
            total = total_query.scalar() or 0
        else:
            total = query.count()
        skip = (page - 1) * items_per_page
        limit = items_per_page
        has_more = (skip + limit) < total
        if page > 1 and skip >= total and total > 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Page {page} does not exist. Total items: {total}"
            )
        query = query.offset(skip).limit(limit)
        results = query.all()
        if not results:
            return PaginatedResponse(
                data=[],
                total=total,
                skip=skip,
                limit=limit,
                has_more=has_more
            )
        if not hasattr(results[0], '__table__'):
            items = [item[0] for item in results if item[0] is not None]
        else:
            items = results
        response_items = []
        for item in items:
            try:
                model_item = response_model.model_validate(item)
                response_items.append(model_item)
            except Exception as e:
                continue
        return PaginatedResponse(
            data=response_items,
            total=total,
            skip=skip,
            limit=limit,
            has_more=has_more
        )

    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid pagination parameters. Page and items_per_page must be valid integers."
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error paginating results: {str(e)}"
        )
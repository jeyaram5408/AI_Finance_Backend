from math import ceil
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession


# -----------------------------------------------------------------------------------


async def paginate_query(
    db: AsyncSession,
    base_query,
    page: int,
    page_size: int
):
    # -------- Count Total Records --------
    count_query = select(func.count()).select_from(base_query.subquery())
    total = await db.scalar(count_query)

    # -------- Pagination --------
    offset = (page - 1) * page_size

    paginated_query = (
        base_query
        .limit(page_size)
        .offset(offset)
    )

    result = await db.execute(paginated_query)

    return {
        "result": result,
        "total": total,
        "total_pages": ceil(total / page_size) if total else 0
    }
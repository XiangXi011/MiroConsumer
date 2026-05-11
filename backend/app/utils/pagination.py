"""分页查询工具"""


def paginate_query(query, page=1, per_page=20):
    """通用分页

    Args:
        query: 列表或 SQLAlchemy Query 对象
        page: 页码（从1开始）
        per_page: 每页条数（上限100）

    Returns:
        {"items": [...], "pagination": {...}}
    """
    page = max(1, page)
    per_page = min(100, max(1, per_page))

    if isinstance(query, list):
        total = len(query)
        items = query[(page - 1) * per_page: page * per_page]
    else:
        total = query.count()
        items = query.offset((page - 1) * per_page).limit(per_page).all()

    return {
        "items": items,
        "pagination": {
            "page": page,
            "per_page": per_page,
            "total": total,
            "pages": (total + per_page - 1) // per_page,
        },
    }

"""
股票公告数据控制器
"""
from fastapi import APIRouter, Query, HTTPException, Depends
from typing import List, Optional
from datetime import date, timedelta
from clickhouse_connect.driver import Client
from common.db.clickhouse_client import get_clickhouse_client
from stock.stock_announcement.schemas.announcement_schemas import (
    AnnouncementItem,
    AnnouncementListResponse,
    AnnouncementCreate,
    AnnouncementBatchCreate
)
from loguru import logger
from config import config

# 创建公告路由器
router = APIRouter(tags=["股票公告"])


@router.get("/announcements/{code}", response_model=AnnouncementListResponse, summary="获取指定股票的公告列表")
def get_stock_announcements(
    code: str,
    start_date: Optional[date] = Query(None, description="开始日期"),
    end_date: Optional[date] = Query(None, description="结束日期"),
    type: Optional[str] = Query(None, description="公告类型筛选"),
    page: int = Query(1, ge=1, description="页码"),
    size: int = Query(10, ge=1, le=200, description="每页数量"),
    client: Client = Depends(get_clickhouse_client)
):
    """
    获取指定股票的公告列表
    """
    # 验证股票代码
    if not code or len(code) != 6 or not code.isdigit():
        raise HTTPException(status_code=400, detail="股票代码格式错误")
    
    # 设置默认日期范围（最近30天）
    if not end_date:
        end_date = date.today()
    if not start_date:
        start_date = end_date - timedelta(days=30)
    
    # 获取股票名称
    stock_name_query = "SELECT name FROM stock_info WHERE code = %(code)s"
    stock_name_result = client.query(stock_name_query, parameters={'code': code}).result_rows
    if not stock_name_result:
        raise HTTPException(status_code=404, detail="股票不存在")
    stock_name = stock_name_result[0][0]
    
    # 构建查询条件
    where_conditions = [
        "code = %(code)s",
        "announce_date >= %(start_date)s",
        "announce_date <= %(end_date)s"
    ]
    params = {
        'code': code,
        'start_date': start_date,
        'end_date': end_date
    }
    
    if type:
        where_conditions.append("type = %(type)s")
        params['type'] = type
    
    where_sql = "WHERE " + " AND ".join(where_conditions)
    
    # 计算分页
    limit = size
    offset = (page - 1) * size
    
    # 查询公告列表
    list_sql = f"""
        SELECT 
            code,
            announce_date,
            title,
            type,
            detail_url,
            content,
            attachments,
            version
        FROM stock_announcement FINAL
        {where_sql}
        ORDER BY announce_date DESC, version DESC
        LIMIT %(limit)s OFFSET %(offset)s
    """
    
    rows = client.query(
        list_sql,
        parameters={**params, 'limit': limit, 'offset': offset}
    ).result_rows
    
    # 查询总数
    count_sql = f"SELECT count() FROM stock_announcement FINAL {where_sql}"
    total = client.query(count_sql, parameters=params).result_rows[0][0]
    
    # 转换数据
    items = [
        AnnouncementItem(
            code=row[0],
            announce_date=row[1],
            title=row[2],
            type=row[3],
            detail_url=row[4],
            content=row[5] or "",
            attachments=row[6] or "",
            version=str(row[7]) if row[7] else None
        )
        for row in rows
    ]
    
    return AnnouncementListResponse(
        code=code,
        name=stock_name,
        total=total,
        items=items
    )


@router.post("/announcements", response_model=dict, summary="创建单条股票公告")
def create_announcement(
    payload: AnnouncementCreate,
    client: Client = Depends(get_clickhouse_client)
):
    """
    创建单条公告
    """
    # 验证股票代码
    if not payload.code or len(payload.code) != 6 or not payload.code.isdigit():
        raise HTTPException(status_code=400, detail="股票代码格式错误")
    
    # 插入数据
    insert_sql = """
        INSERT INTO stock_announcement 
        (code, announce_date, title, type, detail_url, content, attachments)
        VALUES (%(code)s, %(announce_date)s, %(title)s, %(type)s, %(detail_url)s, %(content)s, %(attachments)s)
    """
    
    client.command(
        insert_sql,
        parameters={
            'code': payload.code,
            'announce_date': payload.announce_date,
            'title': payload.title,
            'type': payload.type,
            'detail_url': payload.detail_url,
            'content': payload.content or "",
            'attachments': payload.attachments or ""
        }
    )
    
    return {"message": "创建成功"}


@router.post("/announcements/batch", response_model=dict, summary="批量创建股票公告")
def batch_create_announcements(
    payload: AnnouncementBatchCreate,
    client: Client = Depends(get_clickhouse_client)
):
    """
    批量创建公告
    """
    if not payload.announcements:
        raise HTTPException(status_code=400, detail="公告列表不能为空")
    
    # 准备批量数据
    batch_data = []
    for ann in payload.announcements:
        # 验证股票代码
        if not ann.code or len(ann.code) != 6 or not ann.code.isdigit():
            raise HTTPException(status_code=400, detail=f"股票代码{ann.code}格式错误")
        
        batch_data.append([
            ann.code,
            ann.announce_date,
            ann.title,
            ann.type,
            ann.detail_url,
            ann.content or "",
            ann.attachments or ""
        ])
    
    # 批量插入
    client.insert(
        table='stock_announcement',
        data=batch_data,
        column_names=[
            'code', 'announce_date', 'title', 'type', 
            'detail_url', 'content', 'attachments'
        ]
    )
    
    return {
        "message": "批量创建成功",
        "count": len(batch_data)
    }


@router.get("/announcements", response_model=List[AnnouncementItem], summary="查询公告列表（支持多股票、多条件筛选）")
def list_announcements(
    code: Optional[str] = Query(None, description="股票代码"),
    start_date: Optional[date] = Query(None, description="开始日期"),
    end_date: Optional[date] = Query(None, description="结束日期"),
    type: Optional[str] = Query(None, description="公告类型筛选"),
    limit: int = Query(50, ge=1, le=config.MAX_QUERY_LIMIT, description="返回数量限制"),
    client: Client = Depends(get_clickhouse_client)
):
    """
    查询公告列表（支持多股票、多条件筛选）
    """
    # 构建查询条件
    where_conditions = []
    params = {}
    
    if code:
        if len(code) != 6 or not code.isdigit():
            raise HTTPException(status_code=400, detail="股票代码格式错误")
        where_conditions.append("code = %(code)s")
        params['code'] = code
    
    if start_date:
        where_conditions.append("announce_date >= %(start_date)s")
        params['start_date'] = start_date
    
    if end_date:
        where_conditions.append("announce_date <= %(end_date)s")
        params['end_date'] = end_date
    
    if type:
        where_conditions.append("type = %(type)s")
        params['type'] = type
    
    where_sql = "WHERE " + " AND ".join(where_conditions) if where_conditions else ""
    
    # 查询公告列表
    list_sql = f"""
        SELECT 
            code,
            announce_date,
            title,
            type,
            detail_url,
            content,
            attachments,
            version
        FROM stock_announcement FINAL
        {where_sql}
        ORDER BY announce_date DESC, version DESC
        LIMIT %(limit)s
    """
    
    rows = client.query(
        list_sql,
        parameters={**params, 'limit': limit}
    ).result_rows
    
    # 转换数据
    items = [
        AnnouncementItem(
            code=row[0],
            announce_date=row[1],
            title=row[2],
            type=row[3],
            detail_url=row[4],
            content=row[5] or "",
            attachments=row[6] or "",
            version=str(row[7]) if row[7] else None
        )
        for row in rows
    ]
    
    return items


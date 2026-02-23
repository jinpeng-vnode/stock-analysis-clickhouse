"""
股票信息管理控制器
提供股票基础信息的 CRUD 操作接口
"""
from fastapi import APIRouter, Query, HTTPException, Depends
from typing import Optional, List
from datetime import date, datetime
from clickhouse_connect.driver import Client

from common.db.clickhouse_client import get_clickhouse_client
from stock.stock_info.schemas.stock_info_schemas import (
    StockInfoListItem,
    StockInfoListResponse,
    StockInfoCreate,
    StockInfoUpdate,
    BatchDeletePayload
)


router = APIRouter(tags=["股票信息管理"])


# ======== 工具函数 ========

def _format_version(version_value) -> Optional[str]:
    """
    格式化版本时间，去掉时区信息
    
    Args:
        version_value: 版本时间值（可能是 datetime 对象或字符串）
        
    Returns:
        格式化后的时间字符串（格式：YYYY-MM-DD HH:MM:SS），如果为 None 则返回 None
    """
    if version_value is None:
        return None
    
    try:
        # 如果是 datetime 对象
        if isinstance(version_value, datetime):
            # 如果有时区信息，先去掉时区
            if version_value.tzinfo is not None:
                version_value = version_value.replace(tzinfo=None)
            return version_value.strftime("%Y-%m-%d %H:%M:%S")
        
        # 如果是字符串
        if isinstance(version_value, str):
            # 尝试解析 ISO 格式的字符串
            if 'T' in version_value or '+' in version_value or version_value.endswith('Z'):
                dt = datetime.fromisoformat(version_value.replace('Z', '+00:00'))
                if dt.tzinfo:
                    dt = dt.replace(tzinfo=None)
                return dt.strftime("%Y-%m-%d %H:%M:%S")
            # 如果已经是简单格式，直接返回（最多19个字符，去掉时区部分）
            return version_value[:19] if len(version_value) > 19 else version_value
        
        # 其他类型，尝试转换为字符串
        return str(version_value)
    except Exception:
        # 解析失败，返回 None
        return None

def _exists_code(client: Client, code: str) -> bool:
    """
    检查股票代码是否存在
    
    Args:
        client: ClickHouse 客户端
        code: 股票代码
        
    Returns:
        bool: 如果股票代码存在返回 True，否则返回 False
    """
    sql = "SELECT count() FROM stock_info WHERE code = %(code)s"
    rows = client.query(sql, parameters={"code": code}).result_rows
    return (rows and rows[0][0] > 0)


# ======== 接口定义 ========

@router.get("/stock-info", response_model=StockInfoListResponse, summary="获取股票信息列表（分页查询）")
def list_stock_info(
    page: int = Query(1, ge=1, description="页码，从1开始"),
    size: int = Query(10, ge=1, le=200, description="每页数量，最大200"),
    q: Optional[str] = Query(None, description="关键词，按代码/名称模糊匹配"),
    market: Optional[str] = Query(None, description="市场：SH/SZ"),
    status: Optional[str] = Query(None, description="状态"),
    client: Client = Depends(get_clickhouse_client),
):
    """
    获取股票信息列表（分页查询）
    
    支持按关键词、市场、状态筛选，返回包含所有字段的股票信息列表
    """
    # 构建查询条件
    where = []
    params: dict = {}
    if q and q.strip():
        # 关键词搜索：按代码或名称模糊匹配（不区分大小写）
        # 使用 lowerUTF8 函数实现不区分大小写的搜索
        where.append("(lowerUTF8(code) LIKE lowerUTF8(%(kw)s) OR lowerUTF8(name) LIKE lowerUTF8(%(kw)s))")
        params["kw"] = f"%{q.strip()}%"
    if market:
        # 市场筛选：SH 或 SZ
        where.append("market = %(market)s")
        params["market"] = market
    if status:
        # 状态筛选：正常、停牌等
        where.append("status = %(status)s")
        params["status"] = status

    where_sql = ("WHERE " + " AND ".join(where)) if where else ""

    # 计算分页参数
    limit = size
    offset = (page - 1) * size

    # 查询所有字段的股票信息列表（43个字段）
    list_sql = f"""
        SELECT 
            code, name, market, status, version,
            org_id, org_name_cn, org_name_en, org_short_name_en, pre_name_cn,
            main_operation_business, operating_scope, industry_code, industry_name,
            district_encode, provincial_name, established_date, reg_asset, 
            reg_address_cn, reg_address_en, office_address_cn, office_address_en,
            telephone, postcode, fax, email, org_website,
            legal_representative, chairman, general_manager, secretary, executives_nums,
            actual_controller, classi_name,
            listed_date, actual_issue_vol, issue_price, actual_rc_net_amt,
            pe_after_issuing, online_success_rate_of_issue,
            staff_num, currency_encode, currency
        FROM stock_info
        {where_sql}
        ORDER BY code
        LIMIT %(limit)s OFFSET %(offset)s
    """
    rows = client.query(list_sql, parameters={**params, "limit": limit, "offset": offset}).result_rows

    # 查询总记录数
    count_sql = f"SELECT count() FROM stock_info {where_sql}"
    total = client.query(count_sql, parameters=params).result_rows[0][0]

    # 将查询结果转换为 Pydantic 模型，处理空值
    items = [
        StockInfoListItem(
            # 基础字段（索引 0-4）
            code=r[0],
            name=r[1],
            market=r[2] or "",
            status=r[3] or "正常",
            version=_format_version(r[4]),
            # 组织信息（索引 5-9）
            org_id=r[5] if r[5] is not None else None,
            org_name_cn=r[6] if r[6] is not None else None,
            org_name_en=r[7] if r[7] is not None else None,
            org_short_name_en=r[8] if r[8] is not None else None,
            pre_name_cn=r[9] if r[9] is not None else None,
            main_operation_business=r[10] if r[10] is not None else None,
            operating_scope=r[11] if r[11] is not None else None,
            industry_code=r[12] if r[12] is not None else None,
            industry_name=r[13] if r[13] is not None else None,
            district_encode=r[14] if r[14] is not None else None,
            provincial_name=r[15] if r[15] is not None else None,
            established_date=r[16] if r[16] is not None else None,
            reg_asset=float(r[17]) if r[17] is not None else None,
            reg_address_cn=r[18] if r[18] is not None else None,
            reg_address_en=r[19] if r[19] is not None else None,
            office_address_cn=r[20] if r[20] is not None else None,
            office_address_en=r[21] if r[21] is not None else None,
            telephone=r[22] if r[22] is not None else None,
            postcode=r[23] if r[23] is not None else None,
            fax=r[24] if r[24] is not None else None,
            email=r[25] if r[25] is not None else None,
            org_website=r[26] if r[26] is not None else None,
            legal_representative=r[27] if r[27] is not None else None,
            chairman=r[28] if r[28] is not None else None,
            general_manager=r[29] if r[29] is not None else None,
            secretary=r[30] if r[30] is not None else None,
            executives_nums=int(r[31]) if r[31] is not None else None,
            actual_controller=r[32] if r[32] is not None else None,
            classi_name=r[33] if r[33] is not None else None,
            listed_date=r[34] if r[34] is not None else None,
            actual_issue_vol=float(r[35]) if r[35] is not None else None,
            issue_price=float(r[36]) if r[36] is not None else None,
            actual_rc_net_amt=float(r[37]) if r[37] is not None else None,
            pe_after_issuing=float(r[38]) if r[38] is not None else None,
            online_success_rate_of_issue=float(r[39]) if r[39] is not None else None,
            staff_num=int(r[40]) if r[40] is not None else None,
            currency_encode=r[41] if r[41] is not None else None,
            currency=r[42] if r[42] is not None else None,
        )
        for r in rows
    ]

    return StockInfoListResponse(total=total, items=items)


@router.get("/stock-info/{code}", response_model=StockInfoListItem, summary="获取股票详细信息")
def get_stock_info_detail(code: str, client: Client = Depends(get_clickhouse_client)):
    """
    获取股票详细信息
    
    Args:
        code: 股票代码（6位数字）
        
    Returns:
        StockInfoListItem: 包含所有字段的股票详细信息
        
    Raises:
        HTTPException: 如果股票不存在，返回404错误
    """
    # 查询单个股票的所有字段信息（43个字段）
    sql = """
        SELECT 
            code, name, market, status, version,
            org_id, org_name_cn, org_name_en, org_short_name_en, pre_name_cn,
            main_operation_business, operating_scope, industry_code, industry_name,
            district_encode, provincial_name, established_date, reg_asset, 
            reg_address_cn, reg_address_en, office_address_cn, office_address_en,
            telephone, postcode, fax, email, org_website,
            legal_representative, chairman, general_manager, secretary, executives_nums,
            actual_controller, classi_name,
            listed_date, actual_issue_vol, issue_price, actual_rc_net_amt,
            pe_after_issuing, online_success_rate_of_issue,
            staff_num, currency_encode, currency
        FROM stock_info 
        WHERE code = %(code)s
    """
    rows = client.query(sql, parameters={"code": code}).result_rows
    if not rows:
        raise HTTPException(status_code=404, detail="股票不存在")
    r = rows[0]
    return StockInfoListItem(
        code=r[0],
        name=r[1],
        market=r[2] or "",
        status=r[3] or "正常",
        version=str(r[4]) if r[4] is not None else None,
        org_id=r[5] if r[5] is not None else None,
        org_name_cn=r[6] if r[6] is not None else None,
        org_name_en=r[7] if r[7] is not None else None,
        org_short_name_en=r[8] if r[8] is not None else None,
        pre_name_cn=r[9] if r[9] is not None else None,
        main_operation_business=r[10] if r[10] is not None else None,
        operating_scope=r[11] if r[11] is not None else None,
        industry_code=r[12] if r[12] is not None else None,
        industry_name=r[13] if r[13] is not None else None,
        district_encode=r[14] if r[14] is not None else None,
        provincial_name=r[15] if r[15] is not None else None,
        established_date=r[16] if r[16] is not None else None,
        reg_asset=float(r[17]) if r[17] is not None else None,
        reg_address_cn=r[18] if r[18] is not None else None,
        reg_address_en=r[19] if r[19] is not None else None,
        office_address_cn=r[20] if r[20] is not None else None,
        office_address_en=r[21] if r[21] is not None else None,
        telephone=r[22] if r[22] is not None else None,
        postcode=r[23] if r[23] is not None else None,
        fax=r[24] if r[24] is not None else None,
        email=r[25] if r[25] is not None else None,
        org_website=r[26] if r[26] is not None else None,
        legal_representative=r[27] if r[27] is not None else None,
        chairman=r[28] if r[28] is not None else None,
        general_manager=r[29] if r[29] is not None else None,
        secretary=r[30] if r[30] is not None else None,
        executives_nums=int(r[31]) if r[31] is not None else None,
        actual_controller=r[32] if r[32] is not None else None,
        classi_name=r[33] if r[33] is not None else None,
        listed_date=r[34] if r[34] is not None else None,
        actual_issue_vol=float(r[35]) if r[35] is not None else None,
        issue_price=float(r[36]) if r[36] is not None else None,
        actual_rc_net_amt=float(r[37]) if r[37] is not None else None,
        pe_after_issuing=float(r[38]) if r[38] is not None else None,
        online_success_rate_of_issue=float(r[39]) if r[39] is not None else None,
        staff_num=int(r[40]) if r[40] is not None else None,
        currency_encode=r[41] if r[41] is not None else None,
        currency=r[42] if r[42] is not None else None,
    )


@router.post("/stock-info", response_model=dict, summary="创建股票信息")
def create_stock_info(payload: StockInfoCreate, client: Client = Depends(get_clickhouse_client)):
    """
    创建股票信息
    
    注意：只创建基础字段（代码、名称、市场、状态），其他字段由后台自动同步
    
    Args:
        payload: 股票信息创建数据
        
    Returns:
        dict: 创建成功消息
        
    Raises:
        HTTPException: 如果股票代码已存在，返回400错误
    """
    if _exists_code(client, payload.code):
        raise HTTPException(status_code=400, detail="股票代码已存在")

    sql = (
        "INSERT INTO stock_info (code, name, market, status) "
        "VALUES (%(code)s, %(name)s, %(market)s, %(status)s)"
    )
    client.query(
        sql,
        parameters={
            "code": payload.code,
            "name": payload.name,
            "market": payload.market or "",
            "status": payload.status or "正常",
        },
    )
    return {"message": "创建成功"}


@router.put("/stock-info/{code}", response_model=dict, summary="更新股票信息")
def update_stock_info(code: str, payload: StockInfoUpdate, client: Client = Depends(get_clickhouse_client)):
    """
    更新股票信息
    
    注意：只更新基础字段（名称、市场、状态），其他字段由后台自动同步
    
    Args:
        code: 股票代码
        payload: 股票信息更新数据
        
    Returns:
        dict: 更新成功消息
        
    Raises:
        HTTPException: 如果股票不存在或无可更新字段，返回相应错误
    """
    if not _exists_code(client, code):
        raise HTTPException(status_code=404, detail="股票不存在")

    set_parts = []
    params: dict = {"code": code}
    if payload.name is not None:
        set_parts.append("name = %(name)s")
        params["name"] = payload.name
    if payload.market is not None:
        set_parts.append("market = %(market)s")
        params["market"] = payload.market
    if payload.status is not None:
        set_parts.append("status = %(status)s")
        params["status"] = payload.status
    

    if not set_parts:
        raise HTTPException(status_code=400, detail="无可更新字段")

    sql = f"ALTER TABLE stock_info UPDATE {', '.join(set_parts)} WHERE code = %(code)s"
    client.query(sql, parameters=params)
    return {"message": "已提交更新"}


@router.delete("/stock-info/{code}", response_model=dict, summary="删除股票信息")
def delete_stock_info(code: str, client: Client = Depends(get_clickhouse_client)):
    """
    删除股票信息
    
    Args:
        code: 股票代码
        
    Returns:
        dict: 删除成功消息
        
    Raises:
        HTTPException: 如果股票不存在，返回404错误
    """
    if not _exists_code(client, code):
        raise HTTPException(status_code=404, detail="股票不存在")
    sql = "ALTER TABLE stock_info DELETE WHERE code = %(code)s"
    client.query(sql, parameters={"code": code})
    return {"message": "已提交删除"}


@router.post("/stock-info/batch-delete", response_model=dict, summary="批量删除股票信息")
def batch_delete_stock_info(payload: BatchDeletePayload, client: Client = Depends(get_clickhouse_client)):
    """
    批量删除股票信息
    
    Args:
        payload: 包含要删除的股票代码列表
        
    Returns:
        dict: 批量删除成功消息
        
    Raises:
        HTTPException: 如果代码列表为空，返回400错误
    """
    codes = list({c for c in (payload.codes or []) if c})
    if not codes:
        raise HTTPException(status_code=400, detail="codes 不能为空")
    # ClickHouse IN 参数使用 tuple 传入
    sql = "ALTER TABLE stock_info DELETE WHERE code IN %(codes)s"
    client.query(sql, parameters={"codes": tuple(codes)})
    return {"message": "已提交批量删除"}


"""
股票信息管理相关 Pydantic 模型（从 controllers/stock_info_controller.py 提取）
"""
from typing import Optional, List
from datetime import date
from pydantic import BaseModel, Field


class StockInfoListItem(BaseModel):
    code: str = Field(..., description="股票代码（6位数字）")
    name: str = Field(..., description="股票名称")
    market: str = Field("", description="市场类型：SH/SZ")
    status: str = Field("正常", description="股票状态")
    version: Optional[str] = Field(None, description="版本时间，用于去重")
    
    # 组织信息
    org_id: Optional[str] = Field(None, description="组织ID")
    org_name_cn: Optional[str] = Field(None, description="中文全称")
    org_name_en: Optional[str] = Field(None, description="英文全称")
    org_short_name_en: Optional[str] = Field(None, description="英文简称")
    pre_name_cn: Optional[str] = Field(None, description="曾用名")
    
    # 业务信息
    main_operation_business: Optional[str] = Field(None, description="主营业务")
    operating_scope: Optional[str] = Field(None, description="经营范围")
    industry_code: Optional[str] = Field(None, description="行业代码")
    industry_name: Optional[str] = Field(None, description="行业名称")
    
    # 注册信息
    district_encode: Optional[str] = Field(None, description="地区编码")
    provincial_name: Optional[str] = Field(None, description="省份名称")
    established_date: Optional[date] = Field(None, description="成立日期")
    reg_asset: Optional[float] = Field(None, description="注册资本")
    reg_address_cn: Optional[str] = Field(None, description="注册地址（中文）")
    reg_address_en: Optional[str] = Field(None, description="注册地址（英文）")
    office_address_cn: Optional[str] = Field(None, description="办公地址（中文）")
    office_address_en: Optional[str] = Field(None, description="办公地址（英文）")
    
    # 联系信息
    telephone: Optional[str] = Field(None, description="电话")
    postcode: Optional[str] = Field(None, description="邮编")
    fax: Optional[str] = Field(None, description="传真")
    email: Optional[str] = Field(None, description="邮箱")
    org_website: Optional[str] = Field(None, description="网站")
    
    # 管理信息
    legal_representative: Optional[str] = Field(None, description="法定代表人")
    chairman: Optional[str] = Field(None, description="董事长")
    general_manager: Optional[str] = Field(None, description="总经理")
    secretary: Optional[str] = Field(None, description="董事会秘书")
    executives_nums: Optional[int] = Field(None, description="高管人数")
    actual_controller: Optional[str] = Field(None, description="实际控制人")
    classi_name: Optional[str] = Field(None, description="企业性质")
    
    # 上市信息
    listed_date: Optional[date] = Field(None, description="上市日期")
    actual_issue_vol: Optional[float] = Field(None, description="实际发行量")
    issue_price: Optional[float] = Field(None, description="发行价格")
    actual_rc_net_amt: Optional[float] = Field(None, description="实际募集净额")
    pe_after_issuing: Optional[float] = Field(None, description="发行后市盈率")
    online_success_rate_of_issue: Optional[float] = Field(None, description="网上中签率")
    
    # 其他信息
    staff_num: Optional[int] = Field(None, description="员工数")
    currency_encode: Optional[str] = Field(None, description="货币编码")
    currency: Optional[str] = Field(None, description="货币")


class StockInfoListResponse(BaseModel):
    total: int = Field(..., description="总记录数")
    items: List[StockInfoListItem] = Field(..., description="股票信息列表")


class StockInfoCreate(BaseModel):
    code: str = Field(..., description="股票代码（6位数字）")
    name: str = Field(..., description="股票名称")
    market: str = Field("", description="市场类型：SH/SZ")
    status: str = Field("正常", description="股票状态")
    
    # 组织信息
    org_id: Optional[str] = Field(None, description="组织ID")
    org_name_cn: Optional[str] = Field(None, description="中文全称")
    org_name_en: Optional[str] = Field(None, description="英文全称")
    org_short_name_en: Optional[str] = Field(None, description="英文简称")
    pre_name_cn: Optional[str] = Field(None, description="曾用名")
    
    # 业务信息
    main_operation_business: Optional[str] = Field(None, description="主营业务")
    operating_scope: Optional[str] = Field(None, description="经营范围")
    industry_code: Optional[str] = Field(None, description="行业代码")
    industry_name: Optional[str] = Field(None, description="行业名称")
    
    # 注册信息
    district_encode: Optional[str] = Field(None, description="地区编码")
    provincial_name: Optional[str] = Field(None, description="省份名称")
    established_date: Optional[date] = Field(None, description="成立日期")
    reg_asset: Optional[float] = Field(None, description="注册资本")
    reg_address_cn: Optional[str] = Field(None, description="注册地址（中文）")
    reg_address_en: Optional[str] = Field(None, description="注册地址（英文）")
    office_address_cn: Optional[str] = Field(None, description="办公地址（中文）")
    office_address_en: Optional[str] = Field(None, description="办公地址（英文）")
    
    # 联系信息
    telephone: Optional[str] = Field(None, description="电话")
    postcode: Optional[str] = Field(None, description="邮编")
    fax: Optional[str] = Field(None, description="传真")
    email: Optional[str] = Field(None, description="邮箱")
    org_website: Optional[str] = Field(None, description="网站")
    
    # 管理信息
    legal_representative: Optional[str] = Field(None, description="法定代表人")
    chairman: Optional[str] = Field(None, description="董事长")
    general_manager: Optional[str] = Field(None, description="总经理")
    secretary: Optional[str] = Field(None, description="董事会秘书")
    executives_nums: Optional[int] = Field(None, description="高管人数")
    actual_controller: Optional[str] = Field(None, description="实际控制人")
    classi_name: Optional[str] = Field(None, description="企业性质")
    
    # 上市信息
    listed_date: Optional[date] = Field(None, description="上市日期")
    actual_issue_vol: Optional[float] = Field(None, description="实际发行量")
    issue_price: Optional[float] = Field(None, description="发行价格")
    actual_rc_net_amt: Optional[float] = Field(None, description="实际募集净额")
    pe_after_issuing: Optional[float] = Field(None, description="发行后市盈率")
    online_success_rate_of_issue: Optional[float] = Field(None, description="网上中签率")
    
    # 其他信息
    staff_num: Optional[int] = Field(None, description="员工数")
    currency_encode: Optional[str] = Field(None, description="货币编码")
    currency: Optional[str] = Field(None, description="货币")


class StockInfoUpdate(BaseModel):
    name: Optional[str] = Field(None, description="股票名称")
    market: Optional[str] = Field(None, description="市场类型：SH/SZ")
    status: Optional[str] = Field(None, description="股票状态")
    
    # 组织信息
    org_id: Optional[str] = Field(None, description="组织ID")
    org_name_cn: Optional[str] = Field(None, description="中文全称")
    org_name_en: Optional[str] = Field(None, description="英文全称")
    org_short_name_en: Optional[str] = Field(None, description="英文简称")
    pre_name_cn: Optional[str] = Field(None, description="曾用名")
    
    # 业务信息
    main_operation_business: Optional[str] = Field(None, description="主营业务")
    operating_scope: Optional[str] = Field(None, description="经营范围")
    industry_code: Optional[str] = Field(None, description="行业代码")
    industry_name: Optional[str] = Field(None, description="行业名称")
    
    # 注册信息
    district_encode: Optional[str] = Field(None, description="地区编码")
    provincial_name: Optional[str] = Field(None, description="省份名称")
    established_date: Optional[date] = Field(None, description="成立日期")
    reg_asset: Optional[float] = Field(None, description="注册资本")
    reg_address_cn: Optional[str] = Field(None, description="注册地址（中文）")
    reg_address_en: Optional[str] = Field(None, description="注册地址（英文）")
    office_address_cn: Optional[str] = Field(None, description="办公地址（中文）")
    office_address_en: Optional[str] = Field(None, description="办公地址（英文）")
    
    # 联系信息
    telephone: Optional[str] = Field(None, description="电话")
    postcode: Optional[str] = Field(None, description="邮编")
    fax: Optional[str] = Field(None, description="传真")
    email: Optional[str] = Field(None, description="邮箱")
    org_website: Optional[str] = Field(None, description="网站")
    
    # 管理信息
    legal_representative: Optional[str] = Field(None, description="法定代表人")
    chairman: Optional[str] = Field(None, description="董事长")
    general_manager: Optional[str] = Field(None, description="总经理")
    secretary: Optional[str] = Field(None, description="董事会秘书")
    executives_nums: Optional[int] = Field(None, description="高管人数")
    actual_controller: Optional[str] = Field(None, description="实际控制人")
    classi_name: Optional[str] = Field(None, description="企业性质")
    
    # 上市信息
    listed_date: Optional[date] = Field(None, description="上市日期")
    actual_issue_vol: Optional[float] = Field(None, description="实际发行量")
    issue_price: Optional[float] = Field(None, description="发行价格")
    actual_rc_net_amt: Optional[float] = Field(None, description="实际募集净额")
    pe_after_issuing: Optional[float] = Field(None, description="发行后市盈率")
    online_success_rate_of_issue: Optional[float] = Field(None, description="网上中签率")
    
    # 其他信息
    staff_num: Optional[int] = Field(None, description="员工数")
    currency_encode: Optional[str] = Field(None, description="货币编码")
    currency: Optional[str] = Field(None, description="货币")


class BatchDeletePayload(BaseModel):
    codes: List[str] = Field(..., description="要删除的股票代码列表")


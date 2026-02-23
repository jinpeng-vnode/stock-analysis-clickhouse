"""
股票公告相关 Pydantic 模型
"""
from datetime import date
from typing import List, Optional
from pydantic import BaseModel, Field


class AnnouncementItem(BaseModel):
    """公告数据模型"""
    code: str = Field(..., description="股票代码（6位数字）")
    announce_date: date = Field(..., description="公告日期")
    title: str = Field(..., description="公告标题")
    type: str = Field(..., description="公告类型")
    detail_url: str = Field(..., description="详情页URL")
    content: str = Field(default="", description="公告正文内容")
    attachments: Optional[str] = Field(default="", description="附件PDF链接URL（一般只有一个）")
    version: Optional[str] = Field(None, description="版本时间")


class AnnouncementListResponse(BaseModel):
    """公告列表响应模型"""
    code: str = Field(..., description="股票代码")
    name: str = Field(..., description="股票名称")
    total: int = Field(..., description="总记录数")
    items: List[AnnouncementItem] = Field(..., description="公告列表")


class AnnouncementCreate(BaseModel):
    """创建公告请求模型"""
    code: str = Field(..., description="股票代码（6位数字）")
    announce_date: date = Field(..., description="公告日期")
    title: str = Field(..., description="公告标题")
    type: str = Field(..., description="公告类型")
    detail_url: str = Field(..., description="详情页URL（唯一标识）")
    content: str = Field(default="", description="公告正文内容")
    attachments: Optional[str] = Field(default="", description="附件PDF链接URL（一般只有一个）")


class AnnouncementBatchCreate(BaseModel):
    """批量创建公告请求模型"""
    announcements: List[AnnouncementCreate] = Field(..., description="公告列表")


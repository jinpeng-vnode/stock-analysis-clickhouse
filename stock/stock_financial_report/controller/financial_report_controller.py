"""
财报表数据控制器
"""
from fastapi import APIRouter, Query, HTTPException, Depends
from typing import List, Optional
from datetime import date, timedelta
from clickhouse_connect.driver import Client
from common.db.clickhouse_client import get_clickhouse_client
from stock.stock_financial_report.schemas.financial_report_schemas import (
    FinancialReportItem,
    FinancialReportListResponse,
    FinancialReportCreate,
    FinancialReportBatchCreate
)
from loguru import logger
from config import config

# 创建财报表路由器
router = APIRouter(tags=["财报表"])


@router.get("/financial-reports/{code}", response_model=FinancialReportListResponse, summary="获取指定股票的财报表列表")
def get_stock_financial_reports(
    code: str,
    start_date: Optional[date] = Query(None, description="开始日期"),
    end_date: Optional[date] = Query(None, description="结束日期"),
    page: int = Query(1, ge=1, description="页码"),
    size: int = Query(10, ge=1, le=200, description="每页数量"),
    client: Client = Depends(get_clickhouse_client)
):
    """
    获取指定股票的财报表列表
    """
    # 验证股票代码
    if not code or len(code) != 6 or not code.isdigit():
        raise HTTPException(status_code=400, detail="股票代码格式错误")
    
    # 设置默认日期范围（最近5年）
    if not end_date:
        end_date = date.today()
    if not start_date:
        start_date = date(end_date.year - 5, 1, 1)
    
    # 获取股票名称
    stock_name_query = "SELECT name FROM stock_info WHERE code = %(code)s"
    stock_name_result = client.query(stock_name_query, parameters={'code': code}).result_rows
    if not stock_name_result:
        raise HTTPException(status_code=404, detail="股票不存在")
    stock_name = stock_name_result[0][0]
    
    # 构建查询条件
    where_conditions = [
        "code = %(code)s",
        "report_date >= %(start_date)s",
        "report_date <= %(end_date)s"
    ]
    params = {
        'code': code,
        'start_date': start_date,
        'end_date': end_date
    }
    
    where_sql = "WHERE " + " AND ".join(where_conditions)
    
    # 计算分页
    limit = size
    offset = (page - 1) * size
    
    # 查询财报表列表
    list_sql = f"""
        SELECT 
            code,
            quote_name,
            report_date,
            report_name,
            currency,
            currency_name,
            org_type,
            oa_ncf,
            oa_cash_received_of_sales_service,
            oa_refund_of_tax_and_levies,
            oa_cash_received_of_othr,
            oa_sub_total_ci,
            oa_goods_buy_and_service_cash_pay,
            oa_cash_paid_to_employee_etc,
            oa_payments_of_all_taxes,
            oa_othrcash_paid_relating_to,
            oa_sub_total_cos,
            ia_ncf,
            ia_cash_received_of_dspsl_invest,
            ia_invest_income_cash_received,
            ia_net_cash_of_disposal_assets,
            ia_net_cash_of_disposal_branch,
            ia_cash_received_of_othr,
            ia_sub_total_ci,
            ia_invest_paid_cash,
            ia_cash_paid_for_assets,
            ia_othrcash_paid_relating_to,
            ia_sub_total_cos,
            fa_ncf,
            fa_cash_received_of_absorb_invest,
            fa_cash_received_from_investor,
            fa_cash_received_from_bond_issue,
            fa_cash_received_of_borrowing,
            fa_cash_received_of_othr,
            fa_sub_total_ci,
            fa_cash_pay_for_debt,
            fa_cash_paid_of_distribution,
            fa_branch_paid_to_minority_holder,
            fa_othrcash_paid_relating_to,
            fa_sub_total_cos,
            cce_effect_of_exchange_chg,
            cce_net_increase,
            cce_initial_balance,
            cce_final_balance,
            net_cash_amt_from_branch,
            avg_roe,
            np_per_share,
            operate_cash_flow_ps,
            basic_eps,
            capital_reserve,
            undistri_profit_ps,
            net_interest_of_total_assets,
            net_selling_rate,
            gross_selling_rate,
            total_revenue,
            operating_income_yoy,
            net_profit_atsopc,
            net_profit_atsopc_yoy,
            net_profit_after_nrgal_atsolc,
            np_atsopc_nrgal_yoy,
            ore_dlt,
            rop,
            asset_liab_ratio,
            current_ratio,
            quick_ratio,
            equity_multiplier,
            equity_ratio,
            holder_equity,
            ncf_from_oa_to_total_liab,
            inventory_turnover_days,
            receivable_turnover_days,
            accounts_payable_turnover_days,
            cash_cycle,
            operating_cycle,
            total_capital_turnover,
            inventory_turnover,
            account_receivable_turnover,
            accounts_payable_turnover,
            current_asset_turnover_rate,
            fixed_asset_turnover_ratio,
            version
        FROM stock_financial_report FINAL
        {where_sql}
        ORDER BY report_date DESC, version DESC
        LIMIT %(limit)s OFFSET %(offset)s
    """
    
    rows = client.query(
        list_sql,
        parameters={**params, 'limit': limit, 'offset': offset}
    ).result_rows
    
    # 查询总数
    count_sql = f"SELECT count() FROM stock_financial_report FINAL {where_sql}"
    total = client.query(count_sql, parameters=params).result_rows[0][0]
    
    # 转换数据
    items = []
    for row in rows:
        items.append(FinancialReportItem(
            code=row[0],
            quote_name=row[1],
            report_date=row[2],
            report_name=row[3],
            currency=row[4] or "CNY",
            currency_name=row[5] or "人民币",
            org_type=row[6] or 1,
            oa_ncf=row[7],
            oa_cash_received_of_sales_service=row[8],
            oa_refund_of_tax_and_levies=row[9],
            oa_cash_received_of_othr=row[10],
            oa_sub_total_ci=row[11],
            oa_goods_buy_and_service_cash_pay=row[12],
            oa_cash_paid_to_employee_etc=row[13],
            oa_payments_of_all_taxes=row[14],
            oa_othrcash_paid_relating_to=row[15],
            oa_sub_total_cos=row[16],
            ia_ncf=row[17],
            ia_cash_received_of_dspsl_invest=row[18],
            ia_invest_income_cash_received=row[19],
            ia_net_cash_of_disposal_assets=row[20],
            ia_net_cash_of_disposal_branch=row[21],
            ia_cash_received_of_othr=row[22],
            ia_sub_total_ci=row[23],
            ia_invest_paid_cash=row[24],
            ia_cash_paid_for_assets=row[25],
            ia_othrcash_paid_relating_to=row[26],
            ia_sub_total_cos=row[27],
            fa_ncf=row[28],
            fa_cash_received_of_absorb_invest=row[29],
            fa_cash_received_from_investor=row[30],
            fa_cash_received_from_bond_issue=row[31],
            fa_cash_received_of_borrowing=row[32],
            fa_cash_received_of_othr=row[33],
            fa_sub_total_ci=row[34],
            fa_cash_pay_for_debt=row[35],
            fa_cash_paid_of_distribution=row[36],
            fa_branch_paid_to_minority_holder=row[37],
            fa_othrcash_paid_relating_to=row[38],
            fa_sub_total_cos=row[39],
            cce_effect_of_exchange_chg=row[40],
            cce_net_increase=row[41],
            cce_initial_balance=row[42],
            cce_final_balance=row[43],
            net_cash_amt_from_branch=row[44],
            avg_roe=row[45],
            np_per_share=row[46],
            operate_cash_flow_ps=row[47],
            basic_eps=row[48],
            capital_reserve=row[49],
            undistri_profit_ps=row[50],
            net_interest_of_total_assets=row[51],
            net_selling_rate=row[52],
            gross_selling_rate=row[53],
            total_revenue=row[54],
            operating_income_yoy=row[55],
            net_profit_atsopc=row[56],
            net_profit_atsopc_yoy=row[57],
            net_profit_after_nrgal_atsolc=row[58],
            np_atsopc_nrgal_yoy=row[59],
            ore_dlt=row[60],
            rop=row[61],
            asset_liab_ratio=row[62],
            current_ratio=row[63],
            quick_ratio=row[64],
            equity_multiplier=row[65],
            equity_ratio=row[66],
            holder_equity=row[67],
            ncf_from_oa_to_total_liab=row[68],
            inventory_turnover_days=row[69],
            receivable_turnover_days=row[70],
            accounts_payable_turnover_days=row[71],
            cash_cycle=row[72],
            operating_cycle=row[73],
            total_capital_turnover=row[74],
            inventory_turnover=row[75],
            account_receivable_turnover=row[76],
            accounts_payable_turnover=row[77],
            current_asset_turnover_rate=row[78],
            fixed_asset_turnover_ratio=row[79],
            version=str(row[80]) if row[80] else None
        ))
    
    return FinancialReportListResponse(
        code=code,
        name=stock_name,
        total=total,
        items=items
    )


@router.post("/financial-reports", response_model=dict, summary="创建单条股票财报表")
def create_financial_report(
    payload: FinancialReportCreate,
    client: Client = Depends(get_clickhouse_client)
):
    """
    创建单条财报表
    """
    # 验证股票代码
    if not payload.code or len(payload.code) != 6 or not payload.code.isdigit():
        raise HTTPException(status_code=400, detail="股票代码格式错误")
    
    # 插入数据
    insert_sql = """
        INSERT INTO stock_financial_report 
        (code, quote_name, report_date, report_name, currency, currency_name, org_type,
         oa_ncf, oa_cash_received_of_sales_service, oa_refund_of_tax_and_levies,
         oa_cash_received_of_othr, oa_sub_total_ci, oa_goods_buy_and_service_cash_pay,
         oa_cash_paid_to_employee_etc, oa_payments_of_all_taxes, oa_othrcash_paid_relating_to,
         oa_sub_total_cos, ia_ncf, ia_cash_received_of_dspsl_invest,
         ia_invest_income_cash_received, ia_net_cash_of_disposal_assets,
         ia_net_cash_of_disposal_branch, ia_cash_received_of_othr, ia_sub_total_ci,
         ia_invest_paid_cash, ia_cash_paid_for_assets, ia_othrcash_paid_relating_to,
         ia_sub_total_cos, fa_ncf, fa_cash_received_of_absorb_invest,
         fa_cash_received_from_investor, fa_cash_received_from_bond_issue,
         fa_cash_received_of_borrowing, fa_cash_received_of_othr, fa_sub_total_ci,
         fa_cash_pay_for_debt, fa_cash_paid_of_distribution,
         fa_branch_paid_to_minority_holder, fa_othrcash_paid_relating_to,
         fa_sub_total_cos, cce_effect_of_exchange_chg, cce_net_increase,
         cce_initial_balance, cce_final_balance, net_cash_amt_from_branch)
        VALUES (%(code)s, %(quote_name)s, %(report_date)s, %(report_name)s,
                %(currency)s, %(currency_name)s, %(org_type)s,
                %(oa_ncf)s, %(oa_cash_received_of_sales_service)s, %(oa_refund_of_tax_and_levies)s,
                %(oa_cash_received_of_othr)s, %(oa_sub_total_ci)s, %(oa_goods_buy_and_service_cash_pay)s,
                %(oa_cash_paid_to_employee_etc)s, %(oa_payments_of_all_taxes)s, %(oa_othrcash_paid_relating_to)s,
                %(oa_sub_total_cos)s, %(ia_ncf)s, %(ia_cash_received_of_dspsl_invest)s,
                %(ia_invest_income_cash_received)s, %(ia_net_cash_of_disposal_assets)s,
                %(ia_net_cash_of_disposal_branch)s, %(ia_cash_received_of_othr)s, %(ia_sub_total_ci)s,
                %(ia_invest_paid_cash)s, %(ia_cash_paid_for_assets)s, %(ia_othrcash_paid_relating_to)s,
                %(ia_sub_total_cos)s, %(fa_ncf)s, %(fa_cash_received_of_absorb_invest)s,
                %(fa_cash_received_from_investor)s, %(fa_cash_received_from_bond_issue)s,
                %(fa_cash_received_of_borrowing)s, %(fa_cash_received_of_othr)s, %(fa_sub_total_ci)s,
                %(fa_cash_pay_for_debt)s, %(fa_cash_paid_of_distribution)s,
                %(fa_branch_paid_to_minority_holder)s, %(fa_othrcash_paid_relating_to)s,
                %(fa_sub_total_cos)s, %(cce_effect_of_exchange_chg)s, %(cce_net_increase)s,
                %(cce_initial_balance)s, %(cce_final_balance)s, %(net_cash_amt_from_branch)s)
    """
    
    client.command(
        insert_sql,
        parameters={
            'code': payload.code,
            'quote_name': payload.quote_name,
            'report_date': payload.report_date,
            'report_name': payload.report_name,
            'currency': payload.currency or "CNY",
            'currency_name': payload.currency_name or "人民币",
            'org_type': payload.org_type or 1,
            'oa_ncf': payload.oa_ncf,
            'oa_cash_received_of_sales_service': payload.oa_cash_received_of_sales_service,
            'oa_refund_of_tax_and_levies': payload.oa_refund_of_tax_and_levies,
            'oa_cash_received_of_othr': payload.oa_cash_received_of_othr,
            'oa_sub_total_ci': payload.oa_sub_total_ci,
            'oa_goods_buy_and_service_cash_pay': payload.oa_goods_buy_and_service_cash_pay,
            'oa_cash_paid_to_employee_etc': payload.oa_cash_paid_to_employee_etc,
            'oa_payments_of_all_taxes': payload.oa_payments_of_all_taxes,
            'oa_othrcash_paid_relating_to': payload.oa_othrcash_paid_relating_to,
            'oa_sub_total_cos': payload.oa_sub_total_cos,
            'ia_ncf': payload.ia_ncf,
            'ia_cash_received_of_dspsl_invest': payload.ia_cash_received_of_dspsl_invest,
            'ia_invest_income_cash_received': payload.ia_invest_income_cash_received,
            'ia_net_cash_of_disposal_assets': payload.ia_net_cash_of_disposal_assets,
            'ia_net_cash_of_disposal_branch': payload.ia_net_cash_of_disposal_branch,
            'ia_cash_received_of_othr': payload.ia_cash_received_of_othr,
            'ia_sub_total_ci': payload.ia_sub_total_ci,
            'ia_invest_paid_cash': payload.ia_invest_paid_cash,
            'ia_cash_paid_for_assets': payload.ia_cash_paid_for_assets,
            'ia_othrcash_paid_relating_to': payload.ia_othrcash_paid_relating_to,
            'ia_sub_total_cos': payload.ia_sub_total_cos,
            'fa_ncf': payload.fa_ncf,
            'fa_cash_received_of_absorb_invest': payload.fa_cash_received_of_absorb_invest,
            'fa_cash_received_from_investor': payload.fa_cash_received_from_investor,
            'fa_cash_received_from_bond_issue': payload.fa_cash_received_from_bond_issue,
            'fa_cash_received_of_borrowing': payload.fa_cash_received_of_borrowing,
            'fa_cash_received_of_othr': payload.fa_cash_received_of_othr,
            'fa_sub_total_ci': payload.fa_sub_total_ci,
            'fa_cash_pay_for_debt': payload.fa_cash_pay_for_debt,
            'fa_cash_paid_of_distribution': payload.fa_cash_paid_of_distribution,
            'fa_branch_paid_to_minority_holder': payload.fa_branch_paid_to_minority_holder,
            'fa_othrcash_paid_relating_to': payload.fa_othrcash_paid_relating_to,
            'fa_sub_total_cos': payload.fa_sub_total_cos,
            'cce_effect_of_exchange_chg': payload.cce_effect_of_exchange_chg,
            'cce_net_increase': payload.cce_net_increase,
            'cce_initial_balance': payload.cce_initial_balance,
            'cce_final_balance': payload.cce_final_balance,
            'net_cash_amt_from_branch': payload.net_cash_amt_from_branch
        }
    )
    
    return {"message": "创建成功"}


@router.post("/financial-reports/batch", response_model=dict, summary="批量创建股票财报表")
def batch_create_financial_reports(
    payload: FinancialReportBatchCreate,
    client: Client = Depends(get_clickhouse_client)
):
    """
    批量创建财报表
    """
    if not payload.financial_reports:
        raise HTTPException(status_code=400, detail="财报表列表不能为空")
    
    # 准备批量数据
    batch_data = []
    for fr in payload.financial_reports:
        # 验证股票代码
        if not fr.code or len(fr.code) != 6 or not fr.code.isdigit():
            raise HTTPException(status_code=400, detail=f"股票代码{fr.code}格式错误")
        
        batch_data.append([
            fr.code,
            fr.quote_name,
            fr.report_date,
            fr.report_name,
            fr.currency or "CNY",
            fr.currency_name or "人民币",
            fr.org_type or 1,
            fr.oa_ncf,
            fr.oa_cash_received_of_sales_service,
            fr.oa_refund_of_tax_and_levies,
            fr.oa_cash_received_of_othr,
            fr.oa_sub_total_ci,
            fr.oa_goods_buy_and_service_cash_pay,
            fr.oa_cash_paid_to_employee_etc,
            fr.oa_payments_of_all_taxes,
            fr.oa_othrcash_paid_relating_to,
            fr.oa_sub_total_cos,
            fr.ia_ncf,
            fr.ia_cash_received_of_dspsl_invest,
            fr.ia_invest_income_cash_received,
            fr.ia_net_cash_of_disposal_assets,
            fr.ia_net_cash_of_disposal_branch,
            fr.ia_cash_received_of_othr,
            fr.ia_sub_total_ci,
            fr.ia_invest_paid_cash,
            fr.ia_cash_paid_for_assets,
            fr.ia_othrcash_paid_relating_to,
            fr.ia_sub_total_cos,
            fr.fa_ncf,
            fr.fa_cash_received_of_absorb_invest,
            fr.fa_cash_received_from_investor,
            fr.fa_cash_received_from_bond_issue,
            fr.fa_cash_received_of_borrowing,
            fr.fa_cash_received_of_othr,
            fr.fa_sub_total_ci,
            fr.fa_cash_pay_for_debt,
            fr.fa_cash_paid_of_distribution,
            fr.fa_branch_paid_to_minority_holder,
            fr.fa_othrcash_paid_relating_to,
            fr.fa_sub_total_cos,
            fr.cce_effect_of_exchange_chg,
            fr.cce_net_increase,
            fr.cce_initial_balance,
            fr.cce_final_balance,
            fr.net_cash_amt_from_branch
        ])
    
    # 批量插入
    client.insert(
        table='stock_financial_report',
        data=batch_data,
        column_names=[
            'code', 'quote_name', 'report_date', 'report_name', 'currency', 'currency_name', 'org_type',
            'oa_ncf', 'oa_cash_received_of_sales_service', 'oa_refund_of_tax_and_levies',
            'oa_cash_received_of_othr', 'oa_sub_total_ci', 'oa_goods_buy_and_service_cash_pay',
            'oa_cash_paid_to_employee_etc', 'oa_payments_of_all_taxes', 'oa_othrcash_paid_relating_to',
            'oa_sub_total_cos', 'ia_ncf', 'ia_cash_received_of_dspsl_invest',
            'ia_invest_income_cash_received', 'ia_net_cash_of_disposal_assets',
            'ia_net_cash_of_disposal_branch', 'ia_cash_received_of_othr', 'ia_sub_total_ci',
            'ia_invest_paid_cash', 'ia_cash_paid_for_assets', 'ia_othrcash_paid_relating_to',
            'ia_sub_total_cos', 'fa_ncf', 'fa_cash_received_of_absorb_invest',
            'fa_cash_received_from_investor', 'fa_cash_received_from_bond_issue',
            'fa_cash_received_of_borrowing', 'fa_cash_received_of_othr', 'fa_sub_total_ci',
            'fa_cash_pay_for_debt', 'fa_cash_paid_of_distribution',
            'fa_branch_paid_to_minority_holder', 'fa_othrcash_paid_relating_to',
            'fa_sub_total_cos', 'cce_effect_of_exchange_chg', 'cce_net_increase',
            'cce_initial_balance', 'cce_final_balance', 'net_cash_amt_from_branch'
        ]
    )
    
    return {
        "message": "批量创建成功",
        "count": len(batch_data)
    }


@router.get("/financial-reports", response_model=List[FinancialReportItem], summary="查询财报表列表（支持多股票、多条件筛选）")
def list_financial_reports(
    code: Optional[str] = Query(None, description="股票代码"),
    start_date: Optional[date] = Query(None, description="开始日期"),
    end_date: Optional[date] = Query(None, description="结束日期"),
    limit: int = Query(50, ge=1, le=config.MAX_QUERY_LIMIT, description="返回数量限制"),
    client: Client = Depends(get_clickhouse_client)
):
    """
    查询财报表列表（支持多股票、多条件筛选）
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
        where_conditions.append("report_date >= %(start_date)s")
        params['start_date'] = start_date
    
    if end_date:
        where_conditions.append("report_date <= %(end_date)s")
        params['end_date'] = end_date
    
    where_sql = "WHERE " + " AND ".join(where_conditions) if where_conditions else ""
    
    # 查询财报表列表
    list_sql = f"""
        SELECT 
            code,
            quote_name,
            report_date,
            report_name,
            currency,
            currency_name,
            org_type,
            oa_ncf,
            oa_cash_received_of_sales_service,
            oa_refund_of_tax_and_levies,
            oa_cash_received_of_othr,
            oa_sub_total_ci,
            oa_goods_buy_and_service_cash_pay,
            oa_cash_paid_to_employee_etc,
            oa_payments_of_all_taxes,
            oa_othrcash_paid_relating_to,
            oa_sub_total_cos,
            ia_ncf,
            ia_cash_received_of_dspsl_invest,
            ia_invest_income_cash_received,
            ia_net_cash_of_disposal_assets,
            ia_net_cash_of_disposal_branch,
            ia_cash_received_of_othr,
            ia_sub_total_ci,
            ia_invest_paid_cash,
            ia_cash_paid_for_assets,
            ia_othrcash_paid_relating_to,
            ia_sub_total_cos,
            fa_ncf,
            fa_cash_received_of_absorb_invest,
            fa_cash_received_from_investor,
            fa_cash_received_from_bond_issue,
            fa_cash_received_of_borrowing,
            fa_cash_received_of_othr,
            fa_sub_total_ci,
            fa_cash_pay_for_debt,
            fa_cash_paid_of_distribution,
            fa_branch_paid_to_minority_holder,
            fa_othrcash_paid_relating_to,
            fa_sub_total_cos,
            cce_effect_of_exchange_chg,
            cce_net_increase,
            cce_initial_balance,
            cce_final_balance,
            net_cash_amt_from_branch,
            version
        FROM stock_financial_report FINAL
        {where_sql}
        ORDER BY report_date DESC, version DESC
        LIMIT %(limit)s
    """
    
    rows = client.query(
        list_sql,
        parameters={**params, 'limit': limit}
    ).result_rows
    
    # 转换数据
    items = []
    for row in rows:
        items.append(FinancialReportItem(
            code=row[0],
            quote_name=row[1],
            report_date=row[2],
            report_name=row[3],
            currency=row[4] or "CNY",
            currency_name=row[5] or "人民币",
            org_type=row[6] or 1,
            oa_ncf=row[7],
            oa_cash_received_of_sales_service=row[8],
            oa_refund_of_tax_and_levies=row[9],
            oa_cash_received_of_othr=row[10],
            oa_sub_total_ci=row[11],
            oa_goods_buy_and_service_cash_pay=row[12],
            oa_cash_paid_to_employee_etc=row[13],
            oa_payments_of_all_taxes=row[14],
            oa_othrcash_paid_relating_to=row[15],
            oa_sub_total_cos=row[16],
            ia_ncf=row[17],
            ia_cash_received_of_dspsl_invest=row[18],
            ia_invest_income_cash_received=row[19],
            ia_net_cash_of_disposal_assets=row[20],
            ia_net_cash_of_disposal_branch=row[21],
            ia_cash_received_of_othr=row[22],
            ia_sub_total_ci=row[23],
            ia_invest_paid_cash=row[24],
            ia_cash_paid_for_assets=row[25],
            ia_othrcash_paid_relating_to=row[26],
            ia_sub_total_cos=row[27],
            fa_ncf=row[28],
            fa_cash_received_of_absorb_invest=row[29],
            fa_cash_received_from_investor=row[30],
            fa_cash_received_from_bond_issue=row[31],
            fa_cash_received_of_borrowing=row[32],
            fa_cash_received_of_othr=row[33],
            fa_sub_total_ci=row[34],
            fa_cash_pay_for_debt=row[35],
            fa_cash_paid_of_distribution=row[36],
            fa_branch_paid_to_minority_holder=row[37],
            fa_othrcash_paid_relating_to=row[38],
            fa_sub_total_cos=row[39],
            cce_effect_of_exchange_chg=row[40],
            cce_net_increase=row[41],
            cce_initial_balance=row[42],
            cce_final_balance=row[43],
            net_cash_amt_from_branch=row[44],
            version=str(row[45]) if row[45] else None
        ))
    
    return items


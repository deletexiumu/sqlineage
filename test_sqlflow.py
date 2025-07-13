#!/usr/bin/env python3
"""测试SQLFlow服务连接"""

import sys
import os
import django

# 设置Django环境
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hive_ide.settings')
django.setup()

from apps_lineage.lineage_service import LineageService

def test_sqlflow_connection():
    """测试SQLFlow服务连接"""
    
    test_sql = """CREATE TABLE if not exists dwt_capital.dim_investment_event_df
(
    `bk_investment_event_id`           STRING COMMENT '主键-投资事件ID',
    `sk_investment_event_id`           BIGINT COMMENT '代理键-投资事件ID',
    `investment_event_name`            STRING COMMENT '投资事件名称'
) COMMENT '维度表-投资事件'
PARTITIONED BY ( `dt` string COMMENT '分区列-日期,yyyyMMdd')
stored as orc;

insert overwrite table dwt_capital.dim_investment_event_df partition (dt = '20250625')
select logic_id                         as bk_investment_event_id,
       shared_udf_prod.xxhash(logic_id) as sk_investment_event_id,
       investment_event_name            as investment_event_name
from dwd_zbk.dwd_zbk_investor_project_information;"""
    
    print("🚀 Testing SQLFlow service connection...")
    print(f"SQL to parse:\n{test_sql}\n")
    
    try:
        service = LineageService()
        
        # 测试SQL解析
        print("📡 Calling SQLFlow service...")
        parsed_data = service.parse_sql(test_sql)
        
        if parsed_data:
            print("✅ SQLFlow service responded successfully!")
            print(f"Response data keys: {list(parsed_data.keys())}")
            
            # 打印完整的响应数据以便调试
            import json
            print(f"Full response data:\n{json.dumps(parsed_data, indent=2, ensure_ascii=False)}")
            
            # 测试血缘关系提取
            relations = service.extract_lineage_relations(parsed_data)
            if relations:
                print(f"✅ Found {len(relations)} lineage relations:")
                for i, relation in enumerate(relations, 1):
                    print(f"  {i}. {relation.source_table.full_name} -> {relation.target_table.full_name}")
            else:
                print("⚠️  No lineage relations found")
                
        else:
            print("❌ SQLFlow service returned no data")
            
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_sqlflow_connection()
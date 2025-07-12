from django.core.management.base import BaseCommand
from apps_lineage.lineage_service import LineageService


class Command(BaseCommand):
    help = 'Test lineage parsing functionality'

    def add_arguments(self, parser):
        parser.add_argument(
            '--sql',
            type=str,
            help='SQL statement to parse',
            default="""
CREATE TABLE dwt_capital.dim_investment_event_df AS
SELECT 
    logic_id as bk_investment_event_id,
    investment_event_name,
    project_operational_status
FROM dwd_zbk.dwd_zbk_investor_project_information
WHERE dt = '20250625';
            """.strip()
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Testing lineage parsing...'))
        
        try:
            service = LineageService()
            sql_text = options['sql']
            
            self.stdout.write(f'SQL to parse:\n{sql_text}\n')
            
            # 测试SQL解析
            parsed_data = service.parse_sql(sql_text)
            if parsed_data:
                self.stdout.write(self.style.SUCCESS('✅ SQL parsing successful'))
                self.stdout.write(f'Parsed data keys: {list(parsed_data.keys())}')
                
                # 测试血缘关系提取
                relations = service.extract_lineage_relations(parsed_data)
                if relations:
                    self.stdout.write(self.style.SUCCESS(f'✅ Found {len(relations)} lineage relations'))
                    for i, relation in enumerate(relations, 1):
                        self.stdout.write(f'  {i}. {relation.source_table} -> {relation.target_table}')
                else:
                    self.stdout.write(self.style.WARNING('⚠️  No lineage relations found'))
            else:
                self.stdout.write(self.style.ERROR('❌ SQL parsing failed'))
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Error during testing: {str(e)}')
            )
from django.core.management.base import BaseCommand
from apps_metadata.hive_crawler import HiveCrawler


class Command(BaseCommand):
    help = 'Crawl Hive metadata and save to local database'

    def add_arguments(self, parser):
        parser.add_argument(
            '--database',
            type=str,
            help='Specific database to crawl (default: all databases)',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting Hive metadata crawling...'))
        
        try:
            crawler = HiveCrawler()
            
            if options['database']:
                self.stdout.write(f'Crawling specific database: {options["database"]}')
                
            total_tables = crawler.crawl_metadata()
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'Successfully crawled metadata for {total_tables} tables'
                )
            )
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Failed to crawl metadata: {str(e)}')
            )
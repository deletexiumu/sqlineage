from pyhive import hive
from django.conf import settings
import logging
from .models import HiveTable


logger = logging.getLogger(__name__)


class HiveCrawler:
    def __init__(self):
        self.config = settings.HIVE_CONFIG
        self.connection = None

    def connect(self):
        try:
            self.connection = hive.Connection(
                host=self.config['host'],
                port=self.config['port'],
                database=self.config['database'],
                auth=self.config['auth'],
                kerberos_service_name=self.config['kerberos_service_name']
            )
            logger.info("Successfully connected to Hive")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to Hive: {str(e)}")
            return False

    def get_databases(self):
        if not self.connection:
            raise Exception("Not connected to Hive")
        
        cursor = self.connection.cursor()
        try:
            cursor.execute("SHOW DATABASES")
            databases = [row[0] for row in cursor.fetchall()]
            return databases
        except Exception as e:
            logger.error(f"Failed to get databases: {str(e)}")
            return []
        finally:
            cursor.close()

    def get_tables(self, database):
        if not self.connection:
            raise Exception("Not connected to Hive")
        
        cursor = self.connection.cursor()
        try:
            cursor.execute(f"USE {database}")
            cursor.execute("SHOW TABLES")
            tables = [row[0] for row in cursor.fetchall()]
            return tables
        except Exception as e:
            logger.error(f"Failed to get tables from database {database}: {str(e)}")
            return []
        finally:
            cursor.close()

    def get_table_columns(self, database, table):
        if not self.connection:
            raise Exception("Not connected to Hive")
        
        cursor = self.connection.cursor()
        try:
            cursor.execute(f"USE {database}")
            cursor.execute(f"DESCRIBE {table}")
            columns = []
            for row in cursor.fetchall():
                if row[0] and not row[0].startswith('#'):
                    columns.append({
                        'name': row[0].strip(),
                        'type': row[1].strip() if row[1] else '',
                        'comment': row[2].strip() if row[2] else ''
                    })
            return columns
        except Exception as e:
            logger.error(f"Failed to get columns for table {database}.{table}: {str(e)}")
            return []
        finally:
            cursor.close()

    def crawl_metadata(self):
        if not self.connect():
            raise Exception("Failed to connect to Hive")
        
        try:
            databases = self.get_databases()
            total_tables = 0
            
            for database in databases:
                if database in ['information_schema', 'sys']:
                    continue
                    
                logger.info(f"Crawling database: {database}")
                tables = self.get_tables(database)
                
                for table in tables:
                    try:
                        columns = self.get_table_columns(database, table)
                        
                        import json
                        hive_table, created = HiveTable.objects.update_or_create(
                            name=table,
                            database=database,
                            defaults={'columns_json': json.dumps(columns)}
                        )
                        
                        action = "Created" if created else "Updated"
                        logger.info(f"{action} table: {database}.{table}")
                        total_tables += 1
                        
                    except Exception as e:
                        logger.error(f"Failed to process table {database}.{table}: {str(e)}")
                        continue
            
            logger.info(f"Crawling completed. Processed {total_tables} tables.")
            return total_tables
            
        finally:
            if self.connection:
                self.connection.close()

    def disconnect(self):
        if self.connection:
            self.connection.close()
            self.connection = None
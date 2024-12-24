import subprocess
import os
import configparser
import logging
import tempfile
import shutil
from util import load_config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class LiquibaseMigrator:
    def __init__(self):
        self.config = self._load_config()
        self.liquibase_home = os.path.join(os.path.dirname(__file__), 'liquibase')
        self.liquibase_jar_path = os.path.join(self.liquibase_home, 'internal', 'lib', 'liquibase-core.jar')
        self.mysql_connector_path = os.path.join(self.liquibase_home, 'internal', 'lib', 'mysql-connector-j.jar')
        
    def _load_config(self):
        """从 application.properties 加载配置"""
        return load_config('database')

    def _create_temp_properties(self):
        """创建临时的 liquibase.properties 文件"""
        tmp_dir = os.path.join(os.path.dirname(__file__), 'tmp')
        os.makedirs(tmp_dir, exist_ok=True)
        
        temp_file_path = os.path.join(tmp_dir, 'liquibase.properties')
        
        content = f"""
changeLogFile=migrations/changelog.xml
url={self.config['url']}
username={self.config['username']}
password={self.config['password']}
driver=com.mysql.cj.jdbc.Driver
classpath={self.mysql_connector_path}
logLevel=info
liquibase.hub.mode=off
"""
        with open(temp_file_path, 'w') as f:
            f.write(content)
            
        return temp_file_path

    def run_migration(self):
        """执行数据库迁移"""
        temp_properties = None
        try:
            temp_properties = self._create_temp_properties()
            
            cmd = [
                os.path.join(self.liquibase_home, 'liquibase'),
                f'--defaults-file={temp_properties}',
                'update'
            ]
            
            logger.info("开始执行数据库迁移...")
            
            env = os.environ.copy()
            env['LIQUIBASE_HOME'] = self.liquibase_home
            
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
                env=env
            )
            
            while True:
                output = process.stdout.readline()
                if output == '' and process.poll() is not None:
                    break
                if output:
                    logger.info(output.strip())
            
            return_code = process.poll()
            
            if return_code == 0:
                logger.info("数据库迁移成功完成")
            else:
                error = process.stderr.read()
                logger.error(f"数据库迁移失败: {error}")
                raise Exception(f"Migration failed with return code {return_code}")
                
        except Exception as e:
            logger.error(f"执行迁移时发生错误: {str(e)}")
            raise
        finally:
            if temp_properties and os.path.exists(temp_properties):
                os.remove(temp_properties)
                logger.debug(f"临时配置文件已删除: {temp_properties}")

def run_migrations():
    migrator = LiquibaseMigrator()
    migrator.run_migration()
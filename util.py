import os
import configparser

def load_config(section=None):
    """
    加载配置文件
    :param section: 指定要读取的配置节，如果为None则返回所有配置
    :return: 配置字典
    """
    config = configparser.ConfigParser()
    config_path = os.path.join(os.path.dirname(__file__), 'application.properties')
    config.read(config_path)
    
    if section:
        return config[section]
    return config 
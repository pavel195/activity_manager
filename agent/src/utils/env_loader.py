#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import re
import yaml
from dotenv import load_dotenv

def load_env_vars():
    """Загрузка переменных окружения из файла .env"""
    # Путь к файлу .env в корне проекта
    dotenv_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))), '.env')
    load_dotenv(dotenv_path)

def process_env_vars(value):
    """Обработка значения и замена переменных окружения"""
    if isinstance(value, str):
        # Ищем переменные окружения в формате ${VAR_NAME}
        pattern = r'\${([A-Za-z0-9_]+)}'
        matches = re.findall(pattern, value)
        
        # Заменяем найденные переменные их значениями из окружения
        for var_name in matches:
            env_value = os.getenv(var_name)
            if env_value is not None:
                value = value.replace(f'${{{var_name}}}', env_value)
        
        return value
    elif isinstance(value, list):
        return [process_env_vars(item) for item in value]
    elif isinstance(value, dict):
        return {k: process_env_vars(v) for k, v in value.items()}
    else:
        return value

def load_config_with_env(config_path):
    """Загрузка конфигурации из YAML-файла с обработкой переменных окружения"""
    # Загружаем переменные окружения
    load_env_vars()
    
    try:
        with open(config_path, 'r') as file:
            config = yaml.safe_load(file)
        
        # Обрабатываем переменные окружения в конфигурации
        config = process_env_vars(config)
        
        return config
    except Exception as e:
        print(f"Ошибка при загрузке конфигурации: {e}")
        raise 
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
import sqlalchemy as sa
from sqlalchemy import create_engine, MetaData, Table, Column, Integer, String, DateTime
from sqlalchemy.sql import select, insert
from elasticsearch import Elasticsearch
from datetime import datetime

# Создаем логгер
logger = logging.getLogger('server.db')

# Глобальные переменные для соединений
db_engine = None
es_client = None
metadata = MetaData()

# Определение таблицы событий
events = Table(
    'events', metadata,
    Column('id', Integer, primary_key=True),
    Column('timestamp', DateTime, nullable=False),
    Column('username', String, nullable=False),
    Column('process_name', String, nullable=False),
    Column('pid', Integer, nullable=False),
    Column('agent_id', String, nullable=True)
)

def init_db(config):
    """Инициализация соединения с базой данных и Elasticsearch"""
    global db_engine, es_client
    
    # Подключение к PostgreSQL
    db_config = config['database']
    db_url = f"postgresql://{db_config['user']}:{db_config['password']}@{db_config['host']}:{db_config['port']}/{db_config['name']}"
    
    try:
        db_engine = create_engine(db_url)
        metadata.create_all(db_engine)
        logger.info("Соединение с PostgreSQL установлено")
    except Exception as e:
        logger.error(f"Ошибка при подключении к PostgreSQL: {str(e)}")
        raise
    
    # Подключение к Elasticsearch
    es_config = config['elasticsearch']
    
    try:
        es_client = Elasticsearch(
            es_config['hosts'],
            basic_auth=(es_config['username'], es_config['password'])
        )
        
        # Проверка соединения с Elasticsearch
        if es_client.ping():
            logger.info("Соединение с Elasticsearch установлено")
        else:
            logger.error("Не удалось подключиться к Elasticsearch")
            raise Exception("Не удалось подключиться к Elasticsearch")
            
        # Создание индекса, если он не существует
        index_name = f"{es_config['index_prefix']}-{datetime.now().strftime('%Y.%m.%d')}"
        if not es_client.indices.exists(index=index_name):
            es_client.indices.create(
                index=index_name,
                body={
                    "mappings": {
                        "properties": {
                            "timestamp": {"type": "date"},
                            "username": {"type": "keyword"},
                            "process_name": {"type": "keyword"},
                            "pid": {"type": "integer"},
                            "agent_id": {"type": "keyword"}
                        }
                    }
                }
            )
            logger.info(f"Индекс {index_name} создан")
    except Exception as e:
        logger.error(f"Ошибка при подключении к Elasticsearch: {str(e)}")
        raise

def save_event_to_db(event):
    """Сохранение события в PostgreSQL"""
    try:
        with db_engine.connect() as conn:
            # Преобразуем строку timestamp в объект datetime
            event_timestamp = datetime.fromisoformat(event.timestamp)
            
            # Вставляем запись в базу данных
            result = conn.execute(
                insert(events).values(
                    timestamp=event_timestamp,
                    username=event.username,
                    process_name=event.process_name,
                    pid=event.pid,
                    agent_id=None  # В данной реализации agent_id не используется
                )
            )
            conn.commit()
            
            # Получаем ID вставленной записи
            event_id = result.inserted_primary_key[0]
            
            logger.info(f"Событие сохранено в PostgreSQL с ID: {event_id}")
            return event_id
    except Exception as e:
        logger.error(f"Ошибка при сохранении события в PostgreSQL: {str(e)}")
        raise

def save_event_to_elasticsearch(event):
    """Сохранение события в Elasticsearch"""
    try:
        # Формируем имя индекса с префиксом и датой
        index_name = f"monitoring-{datetime.now().strftime('%Y.%m.%d')}"
        
        # Преобразуем строку timestamp в объект datetime
        event_timestamp = datetime.fromisoformat(event.timestamp)
        
        # Подготавливаем документ для Elasticsearch
        doc = {
            "timestamp": event_timestamp,
            "username": event.username,
            "process_name": event.process_name,
            "pid": event.pid,
            "agent_id": None  # В данной реализации agent_id не используется
        }
        
        # Индексируем документ
        result = es_client.index(index=index_name, document=doc)
        
        logger.info(f"Событие сохранено в Elasticsearch с ID: {result['_id']}")
        return result['_id']
    except Exception as e:
        logger.error(f"Ошибка при сохранении события в Elasticsearch: {str(e)}")
        raise 
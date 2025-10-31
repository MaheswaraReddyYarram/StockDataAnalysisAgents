from typing import List

from database_manager import DatabaseClient, StockMarketAnalysisData
from stock_models import StockAnalysisDataList

try:
    from crewai.tools import tool
except Exception:
    # Fallback no-op decorator if crewai is not installed at runtime
    def tool(_name=None):
        def decorator(func):
            return func
        return decorator
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy import create_engine, Column, String, Integer, DateTime, Boolean, Float
import logging
from datetime import datetime
from langchain_community.tools.sql_database.tool import InfoSQLDatabaseTool, ListSQLDatabaseTool, QuerySQLCheckerTool
from langchain_community.tools.sql_database.tool import QuerySQLDatabaseTool
from langchain_community.utilities.sql_database import SQLDatabase
# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


connection_string= f"postgresql+psycopg2://dev_user:dev_password@localhost:5432/stock_data_db"
# Attempt to create the SQLDatabase; if this fails (e.g., Postgres not running), fall back to SQLite
try:
    db = SQLDatabase.from_uri(connection_string)
except Exception as e:
    logger.warning(f"Failed to initialize Postgres SQLDatabase, falling back to local SQLite. Error: {e}")
    connection_string = "sqlite:///local_stock_data.db"
    db = SQLDatabase.from_uri(connection_string)

database_client = DatabaseClient()

# create a tool to store data into database
@tool("StockDataStorageTool")
def store_stock_data(stock_analysis_data: StockAnalysisDataList) -> bool:
    """
    Tool to store researched stock data into the database.
    Use this tool only to store data into database
    :param List[data]: List of stock analysis data dictionaries
    :return:
    """
    try:
        session = database_client.SessionLocal()
        logger.info(f"type of stock_analysis_data is {type(stock_analysis_data)}")
        logger.info(f"Received stock analysis data to store: {stock_analysis_data}")

        # Normalize payload into a list of dictionaries
        payload = stock_analysis_data
        if hasattr(payload, "stocks"):
            items = payload.stocks
        elif isinstance(payload, dict) and "stocks" in payload:
            items = payload["stocks"]
        elif isinstance(payload, list):
            items = payload
        else:
            items = [payload]

        saved = 0
        for item in items:
            # Convert pydantic objects to dicts if needed
            if hasattr(item, "model_dump"):
                data = item.model_dump()
            elif hasattr(item, "dict"):
                data = item.dict()
            else:
                data = item

            if not isinstance(data, dict):
                logger.warning(f"Skipping non-dict item: {type(data)} -> {data}")
                continue

            stock_data = StockMarketAnalysisData(
                stock_name=data.get("stock_name"),
                stock_code=data.get("stock_code"),
                market=data.get("market"),
                buy_price=data.get("buy_price"),
                target_price_daily=data.get("target_price_daily"),
                target_price_weekly=data.get("target_price_weekly"),
                stop_loss=data.get("stop_loss"),
                analysis_date=data.get("analysis_date_time")
            )
            session.add(stock_data)
            saved += 1

        session.commit()
        logger.info(f"Stored {saved} stock analysis rows successfully.")
        return True
    except Exception as e:
        session.rollback()
        logger.error(f"Failed to store stock data: {e}")
        return False
    finally:
        session.close()



@tool("execute_sql")
def execute_sql(query: str) -> str:
    """
    Tool to execute SQL queries against the stock market analysis database.
    :param query: The SQL query to execute.
    :return: The result of the SQL query.
    """
    try:
        session = database_client.SessionLocal()
        result = session.execute(query)
        rows = result.fetchall()
        session.commit()
        logger.info(f"Executed SQL query successfully: {query}")
        return str(rows)
    except Exception as e:
        logger.error(f"Failed to execute SQL query: {e}")
        return f"Error executing query: {e}"
    finally:
        session.close()


@tool("list_tables")
def list_tables() -> List[str]:
    """
    Tool to list all tables in the stock market analysis database.
    :return: List of table names.
    """
    # try:
    #     inspector = create_engine(database_client.connection_string).inspect()
    #     tables = inspector.get_table_names()
    #     logger.info("Listed tables successfully.")
    #     return tables
    # except Exception as e:
    #     logger.error(f"Failed to list tables: {e}")
    #     return []

    return ListSQLDatabaseTool(db=db).invoke("")

@tool("tables_schema")
def tables_schema(tables: str) -> str:
    """
    Tool to get the schema of specified tables in the stock market analysis database.
    Be sure that the tables actually exist by calling `list_tables` first!
    :param tables: table names.
    :return: Schema information of the specified tables.
    """
    return InfoSQLDatabaseTool(db=db).invoke(tables)

@tool("execute_sql")
def execute_sql(query: str):
    """
    Execute a SQL query against the database. Returns the result
    :param query:
    :return:
    """
    return QuerySQLDatabaseTool(db=db).invoke(query)

@tool("check_sql")
def check_sql(sql_query: str):
    """
    Use this tool to double-check if your query is correct before executing it. Always use this
    tool before executing a query with `execute_sql`.
    :param sql_query:
    :return:
    """
    return QuerySQLCheckerTool(db=db).invoke(sql_query)


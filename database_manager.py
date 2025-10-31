from typing import List

from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.sql import text
from sqlalchemy import create_engine, Column, String, DateTime, PrimaryKeyConstraint, Float, Date
from datetime import datetime, date
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Database setup for caching
Base = declarative_base()
connection_string= f"postgresql+psycopg2://dev_user:dev_password@localhost:5432/stock_data_db"
class StockMarketAnalysisData(Base):
    """Database model for SharePoint file caching."""
    __tablename__ = 'stock_market_data_analysis'

    stock_name = Column(String(150), nullable=False)
    stock_code = Column(String(20), nullable=False)
    market = Column(String(20), nullable=False, index=True)
    buy_price = Column(Float, nullable=False)
    target_price_daily = Column(Float, nullable=False)
    target_price_weekly = Column(Float, nullable=False)
    stop_loss = Column(Float, nullable=False, default=0)
    analysis_date = Column(Date, nullable=False, default=datetime.utcnow().date())
    day_end_price = Column(Float, nullable=True)

    #primary key constraint
    __table_args__ = (
        PrimaryKeyConstraint('stock_name', 'analysis_date', name='pk_stock_analysis'),
    )

class DatabaseClient:
    def __init__(self):
        # Initialize database connection here
        self.connection_string=connection_string
        try:
            self.engine = create_engine(self.connection_string, pool_pre_ping=True, pool_recycle=3600)
            self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
            # Create tables if they don't exist
            Base.metadata.create_all(bind=self.engine)
            logger.info("Database cache tables initialized successfully")
        except Exception as e:
            logger.warning(f"Primary DB initialization failed ({e}). Falling back to local SQLite database.")
            # Fallback to SQLite file DB to keep the app importable/runable without Postgres
            self.connection_string = "sqlite:///local_stock_data.db"
            self.engine = create_engine(self.connection_string, pool_pre_ping=True, pool_recycle=3600)
            self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
            Base.metadata.create_all(bind=self.engine)
            logger.info("Fallback SQLite database initialized successfully")


    def store(self, data: str) -> bool:
        # Logic to store data into the database
        print(f"Storing data: {data}")
        return True

    def list_stock_data_analysis_dates(self) -> List[date]:
        """
        List all stock data analysis from the database.
        :return:
        """
        query = text("select distinct analysis_date from stock_market_data_analysis;")
        with self.engine.engine.connect() as session:
            result = session.execute(query).fetchall()
            logger.info(f'result from db is {result}')
        # convert to pure dates (handles datetime, date, and ISO strings)
        dates = []
        for row in result:
            val = row[0]
            if isinstance(val, datetime):
                dates.append(val.date())
            elif isinstance(val, date):
                dates.append(val)
            elif isinstance(val, str):
                try:
                    dates.append(datetime.fromisoformat(val).date())
                except ValueError:
                    # e.g. 'YYYY-MM-DD'
                    dates.append(datetime.strptime(val, "%Y-%m-%d").date())
            else:
                dates.append(val)
        logger.info(f'stock data analysis dates are {dates}')
        return dates




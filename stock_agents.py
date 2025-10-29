from datetime import datetime
from textwrap import dedent
from typing import List
import logging
import pandas as pd
from crewai import Agent, Task, Crew, CrewOutput
from crewai_tools import SerperDevTool
from load_dotenv import load_dotenv
from stock_agent_tools import (store_stock_data, execute_sql, list_tables, check_sql, tables_schema)
from stock_models import StockAnalysisData, StockAnalysisDataList


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# create agents
search_tool = SerperDevTool()
verbose_flag=True
load_dotenv()

class CrewAiAgentsConfig:
    def __init__(self):
        # agent for research task
        self.stock_research_agent = Agent(
            role="Stock Research Agent",
            goal="Research financial markets and stock information for {market}",
            backstory=("You are a seasoned financial analyst with deep knowledge of stock markets and investment strategies."
                      " Your expertise allows you to gather and analyze latest market data effectively."
                      " Your goal is to gather comprehensive information on stocks and market trends."
                      " Use already analyzed data from previous runs from database by using proper tools and adjust the research accordingly."),
            tools=[search_tool, execute_sql],
            allow_delegation=True,
            verbose=verbose_flag
        )

        # define tasks for stock research agent
        self.research_task = Task(
            description="Conduct in-depth research on the current state of the {market} stock market.",
            expected_output="Comprehensive latest market data, stock performance metrics, and relevant news articles.",
            agent=self.stock_research_agent
        )

        # agent for stock analysis task
        self.stock_analysis_agent = Agent(
            role = "Stock Analysis Agent",
            goal = "Analyze stock data and provide investment insights for {market}",
            backstory=(" With a strong background in financial analysis, you excel at interpreting stock data and market trends."
                       " Your goal is to interpret the researched data and identify top {number} of stocks to buy."
                       " Generate stock name, stock code, buy price, target price for both day and week trades, "
                       " stop loss prices for each identified stock, current date and time as analysis date time,"
                       " in the {market} and provide a brief rationale for each recommendation."
                       " Use already analyzed data from previous runs from database by using proper tools and adjust the research accordingly."),
            tools =[search_tool, execute_sql],
            allow_delegation=True,
            verbose=verbose_flag,
            memory=True
        )

        # define tasks for stock analysis agent
        self.analysis_task = Task(
            description="Analyze the researched stock data and identify top {number} stocks to buy with detailed recommendations.",
            expected_output=("A list of top {number} stocks along with stock code in the specified {market} to buy with buy price, "
                             "target price for day and weekly trades, stop loss prices, analysis date time and rationale."
                             "Analysis date time should be the current date and time when the analysis is performed."
                             "Analysis date time should be in the format of YYYY-MM-DDTHH:MM:SS"
                             "Output should be in the form of list of StockAnalysisData objects"),
            agent=self.stock_analysis_agent,
            output_json=StockAnalysisDataList
        )


        # define agent to store indentified stock data
        self.stock_data_storage_agent = Agent(
            role="Stock Data Storage Agent",
            goal="Store and manage researched stock data efficiently",
            backstory=(" You are responsible for organizing and maintaining the integrity of stock data generated from stock_analysis_agent"
                       " Your expertise ensures that all researched information is accurately stored and easily accessible."
                       " Expect input in the form of StockAnalysisDataList objects"),
            tools=[store_stock_data]
        )

        # define task for stock_data_storage_agent
        self.storage_task = Task(
            description="Store the analyzed stock data into the database for future reference.",
            expected_output="Confirmation of successful data storage and list of stored stock data.",
            agent=self.stock_data_storage_agent
        )

        # create agent to read from database
        self.sql_query_agent = Agent(
            role= "SQL Query Agent",
            goal="Generate and execute SQL queries based on a request from the database",
            backstory=dedent("""
                You are an experienced database engineer who is master at creating efficient and complex SQL queries.
                You have a deep understanding of how different databases work and how to optimize queries.
                Use the `list_tables` to find available tables.
                Use the `tables_schema` to understand the metadata for the tables.
                Use the `execute_sql` to check your queries for correctness.
                Use the `check_sql` to execute queries against the database.
            """),
            tools=[execute_sql, list_tables, check_sql, tables_schema],
            allow_delegation=False,
            verbose=verbose_flag,
            cache=True
        )

        self.extract_data_task = Task(
            description="Generate and execute SQL queries to extract relevant stock market analysis data based on the given {query}.",
            expected_output="List of database query results based on the specified criteria.",
            agent=self.sql_query_agent,
            output_pydantic=StockAnalysisDataList
        )

        # agent to get stock price at end of the day
        self.stock_closing_price_analysis_agent= Agent(
            role="Stock Price Agent",
            goal="Fetch the stock closing price for the day {date} for given stock codes {stock_codes}",
            backstory=(" You are an expert in retrieving accurate stock price data."
                       " Your goal is to provide the closing stock prices for the requested stock codes."
                       " Use search tool to get the stock prices."
                       " Use the `list_tables` to find available tables."
                       " Use the `tables_schema` to understand the metadata for the tables."
                       " Use the `execute_sql` to check your queries for correctness."
                       " Use the `check_sql` to execute queries against the database."),
            verbose=verbose_flag,
            memory=True,
            allow_delegation=False,
            tools=[search_tool, execute_sql, check_sql, list_tables, tables_schema]
        )

        self.stock_closing_price_task = Task(
            description="Retrieve the closing stock prices for the specified stock codes {stock_codes} for the given date {date}.",
            expected_output="(Update the day_end_price column for each stock code with the retrieved closing price)."
                            " A list of stock codes with their corresponding closing prices for the day.",
            agent=self.stock_closing_price_analysis_agent
        )


    def get_closing_price(self, date: str, stock_codes: List[str]):
        """
        Get the closing stock prices for the given date and stock codes.
        :param date:
        :param stock_codes:
        :return:
        """
        stock_price_crew = Crew(
            agents=[self.stock_closing_price_analysis_agent],
            tasks=[self.stock_closing_price_task],
            verbose=verbose_flag,
            memory=True
        )

        inputs = {
            "date": date,
            "stock_codes": stock_codes
        }

        response = stock_price_crew.kickoff(inputs=inputs)
        return response

    def run_stock_analysis(self,market: str, number: int):
        """
        Run the stock analysis crew with given market and number of stocks to analyze.
        :param market:
        :param number:
        :return:
        """
        # create crew to orchestrate the agents and tasks
        stock_crew = Crew(
                agents=[self.stock_research_agent, self.stock_analysis_agent, self.stock_data_storage_agent],
                tasks=[self.research_task, self.analysis_task, self.storage_task],
                verbose=verbose_flag,
                memory=True,
                output_log_file=f"agent_logs/stock_crew_output_{datetime.now().strftime('%Y-%m-%d')}.log"
        )

        inputs = {
            "market": market,
            "number": number
        }

        response = stock_crew.kickoff(inputs=inputs)
        return response

    def get_stock_data_from_db(self, query: str):
        """
        Get stock data from database based on the given query.
        :param query:
        :return:
        """
        sql_crew = Crew(
            agents=[self.sql_query_agent],
            tasks=[self.extract_data_task],
            verbose=verbose_flag,
            memory=True
        )

        inputs = {
            "query": query
        }

        response = sql_crew.kickoff(inputs=inputs)
        return response


#to test
if __name__ == '__main__':
    # create crew to orchestrate the agents and tasks
    crewAiAgentsConfig = CrewAiAgentsConfig()
    crew = Crew(
        agents=[crewAiAgentsConfig.stock_research_agent, crewAiAgentsConfig.stock_analysis_agent, crewAiAgentsConfig.stock_data_storage_agent],
        tasks=[crewAiAgentsConfig.research_task, crewAiAgentsConfig.analysis_task, crewAiAgentsConfig.storage_task],
        verbose=verbose_flag,
        memory=True,
        output_log_file=f"stock_crew_output_{datetime.date}.log"
    )

    inputs = {
        "market": "Sweden",
        "number": 5
    }

    # crew = Crew(
    #     agents=[crewAiAgentsConfig.sql_query_agent],
    #     tasks=[crewAiAgentsConfig.extract_data_task],
    #     verbose=verbose_flag,
    #     memory=True
    # )
    #
    # inputs = {
    #     "query": "Fetch all columns from stock_market_analysis_data table based on today's date"
    # }

    response: CrewOutput = crew.kickoff(inputs=inputs)
    print(f"type of response is {type(response)}")
    df = pd.DataFrame(response["stocks"])
    print(f"df columns are {df.columns}")
    #print(f"response is {response}")
    print(df.head(10))


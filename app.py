from typing import List
import pandas as pd
import streamlit as st
from crewai import CrewOutput
from dotenv import load_dotenv
from datetime import datetime
import json

from database_manager import DatabaseClient
from stock_agents import CrewAiAgentsConfig

# configure main page
st.set_page_config(
    page_title="Stock Market Analysis with CrewAI",
    layout="wide",
    initial_sidebar_state="expanded"
)
load_dotenv()

# Custom CSS for better styling
st.markdown("""
<style>
    .main {
        padding-top: 1rem;
    }
    .stMetric {
        background-color: #f0f2f6;
        border: 1px solid #e0e0e0;
        padding: 1rem;
        border-radius: 0.5rem;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .analysis-card {
        background-color: #ffffff;
        padding: 1.5rem;
        border-radius: 0.75rem;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        border: 1px solid #e5e7eb;
        margin: 1rem 0;
    }
    .status-badge {
        padding: 0.25rem 0.75rem;
        border-radius: 9999px;
        font-size: 0.875rem;
        font-weight: 500;
    }
    .status-success {
        background-color: #d1fae5;
        color: #065f46;
    }
    .status-warning {
        background-color: #fef3c7;
        color: #92400e;
    }
    .status-error {
        background-color: #fee2e2;
        color: #991b1b;
    }
</style>
""", unsafe_allow_html=True)


class StockMarketAnalyzer:
    def __init__(self):
        self.setup_session_state()
        self.crewAiAgentsConfig = CrewAiAgentsConfig()
        self.database_manager = DatabaseClient()


    def setup_session_state(self):
        if 'morning_results' not in st.session_state:
            st.session_state.morning_results = None
        if 'evening_results' not in st.session_state:
            st.session_state.evening_results = None

    def run_morning_scan(self, market: str, max_recommendations: int):
        """
        Run the morning stock market analysis scan.
        :param market:
        :param max_recommendations:
        :return:
        """
        # Placeholder implementation - replace with actual analysis logic
        return self.crewAiAgentsConfig.run_stock_analysis(market, max_recommendations)

    def list_recommendation_dates(self) -> List[datetime]:
        """
        Read all the dates for which stock recommendations are available from storage.
        :return:
        """
        # Placeholder implementation - replace with actual data retrieval logic
        return self.database_manager.list_stock_data_analysis_dates()

    def list_stock_data_analysis(self):
        """
        List all stock data analysis from the database.
        :return:
        """
        query = "Fetch all rows and columns except day_end_price from stock_market_analysis_data table based on today's date"
        response = self.crewAiAgentsConfig.get_stock_data_from_db(query)
        print(f'stock data analysis response is {response}')
        return response

    def get_closing_price(self, review_date: datetime):
        """
        Get the closing price for stocks on a given date.
        :param review_date:
        :return:
        """
        query = f"Fetch stock_name, stock_code, day_end_price, analysis_date from stock_market_analysis_data where analysis_date = '{review_date.date()}'"
        response = self.crewAiAgentsConfig.get_stock_data_from_db(query)
        print(f'closing price response is {response}')
        if not response.stocks:
            return {'error': f'No closing price data found for {review_date.date()}'}
        return response


    def main(self):
        st.title("Stock Market Analysis with CrewAI")
        st.markdown("Leverage the power of CrewAI agents to analyze stock market trends and make informed investment decisions.")

        #sidebar inputs
        with st.sidebar:
            st.header("Daily Scanner")
            st.subheader("Morning Scan")
            market = st.selectbox("Select Market", ["Sweden", "USA"], key="morning_market", accept_new_options=True)
            max_recs = st.number_input("Max Recommendations", min_value=1, max_value=20, value=5, key="morning_max_recs")
            run_morning = st.button("Run Morning Scan", type="primary", key="morning_scan_button", use_container_width=True)

            st.subheader("Evening Scan")
            dates = self.list_recommendation_dates()
            review_date = st.selectbox("Select Review Date", options=dates if dates else [datetime.utcnow()], key="evening_review_date")
            run_evening = st.button("Run Evening Review", type="primary", key="evening_review_button", use_container_width=True)

        if 'run_morning' not in locals():
            run_morning = False
        if run_morning:
            with st.spinner("Running Stock Analysis..."):
                response = self.run_morning_scan(market, max_recs)
                st.session_state.morning_results = "Analysis Completed"
        if st.session_state.morning_results:
            st.markdown("### ✅ Morning Recommendations")
            response = self.list_stock_data_analysis()
            if response is not None:
                if hasattr(response, "pydantic") and hasattr(response.pydantic, "stocks"):
                    rows = [s.model_dump() if hasattr(s, "model_dump") else s.dict() for s in response.pydantic.stocks]
                    df = pd.DataFrame(rows)[
                    ["stock_name", "stock_code", "market", "buy_price", "target_price_daily", "target_price_weekly",
                     "stop_loss", "analysis_date_time", "analysis"]]
                # Fallbacks if pydantic is a JSON string or dict
                else:
                    import json
                    payload = response.pydantic if hasattr(response, "pydantic") else getattr(response, "json_dict", response)
                    if isinstance(payload, str):
                        payload = json.loads(payload)
                    if isinstance(payload, dict) and "stocks" in payload:
                        df = pd.DataFrame(payload["stocks"])[
                    ["stock_name", "stock_code", "market", "buy_price", "target_price_daily", "target_price_weekly",
                     "stop_loss", "analysis_date_time", "analysis"]]
                    else:
                        df = pd.DataFrame(payload if isinstance(payload, list) else [payload])
            else:
                # no recommendations. create an empty dataframe
                df = pd.DataFrame()
            st.dataframe(df)

        if 'run_evening' not in locals():
            run_evening = False
        if run_evening and dates:
            date_to_review = review_date
            with st.spinner(f"Reviewing recommendations for {date_to_review}..."):
                review = self.get_closing_price(date_to_review)
                if 'error' in review:
                    st.error(review['error'])
                else:
                    st.session_state.evening_results = review


if __name__ == '__main__':
    load_dotenv()
    analyzer = StockMarketAnalyzer()
    analyzer.main()
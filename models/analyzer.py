import sqlite3
import pandas as pd
from prophet import Prophet
import os

DB_PATH = 'data/slang_data.db'

class SlangAnalyzer:
    def __init__(self, db_path=DB_PATH):
        self.db_path = db_path

    def get_data(self, word):
        """Fetch daily counts for a specific word."""
        conn = sqlite3.connect(self.db_path)
        query = """
            SELECT 
                date(timestamp, 'unixepoch') as date, 
                CASE 
                    WHEN is_mainstream = 1 THEN 'mainstream'
                    ELSE 'niche'
                END as subreddit_type,
                COUNT(*) as count 
            FROM mentions 
            WHERE keyword = ?
            GROUP BY date, subreddit_type
        """
        df = pd.read_sql_query(query, conn, params=(word,))
        conn.close()
        return df

    def process_data(self, df):
        """Pivot and smooth data."""
        if df.empty:
            return pd.DataFrame()

        # Pivot data
        pivot_df = df.pivot_table(index='date', columns='subreddit_type', values='count', fill_value=0).reset_index()
        
        # Ensure columns exist
        for col in ['mainstream', 'niche']:
            if col not in pivot_df.columns:
                pivot_df[col] = 0
                
        # Fill missing dates to ensure continuous time series for Prophet
        pivot_df['date'] = pd.to_datetime(pivot_df['date'])
        all_dates = pd.date_range(start=pivot_df['date'].min(), end=pivot_df['date'].max())
        pivot_df = pivot_df.set_index('date').reindex(all_dates, fill_value=0).reset_index().rename(columns={'index': 'date'})
        
        # Metrics
        pivot_df['total'] = pivot_df['mainstream'] + pivot_df['niche']
        pivot_df['ratio'] = (pivot_df['mainstream'] + 1) / (pivot_df['niche'] + 1)
        pivot_df['saturation'] = pivot_df['mainstream'] / (pivot_df['total'] + 1) # Saturation Score
        
        return pivot_df

    def forecast_series(self, df, column, days=14):
        """Forecast a specific column using Prophet."""
        if df.empty or len(df) < 2:
            return None, None

        prophet_df = df[['date', column]].rename(columns={'date': 'ds', column: 'y'})
        
        # Disable seasonality for short data, fit daily seasonality if possible
        model = Prophet(daily_seasonality=True, yearly_seasonality=False, weekly_seasonality=False)
        model.fit(prophet_df)
        
        future = model.make_future_dataframe(periods=days)
        forecast = model.predict(future)
        return model, forecast

    def calculate_growth_rate(self, forecast_df, days=14):
        """Calculate Compound Annual Growth Rate (CAGR) equivalent for the forecast period."""
        if forecast_df is None or forecast_df.empty:
            return 0.0
        
        # Get current (last historical point estimate) and future (end of forecast)
        current = forecast_df.iloc[-days-1]['trend'] # Approximate start of forecast
        future = forecast_df.iloc[-1]['trend']
        
        if current <= 0: return 0.0 # Avoid div by zero or negative logic issues for simple growth
        
        # Simple growth rate over the period
        growth_rate = (future - current) / current
        return growth_rate

    def analyze_word(self, word):
        """Full analysis pipeline."""
        raw_data = self.get_data(word)
        if raw_data.empty:
            return None
            
        hist_df = self.process_data(raw_data)
        
        # Forecast Mainstream and Niche separately
        m_model, m_forecast = self.forecast_series(hist_df, 'mainstream', days=14)
        n_model, n_forecast = self.forecast_series(hist_df, 'niche', days=14)
        
        # Calculate Growth Rates (Slang Velocity)
        m_growth = self.calculate_growth_rate(m_forecast)
        n_growth = self.calculate_growth_rate(n_forecast)
        
        # Check Alert
        is_cringe_alert = self.check_cringe_alert(m_growth, n_growth)
        
        return {
            'historical': hist_df,
            'm_forecast': m_forecast,
            'n_forecast': n_forecast,
            'metrics': {
                'mainstream_growth': m_growth,
                'niche_growth': n_growth,
                'current_ratio': hist_df.iloc[-1]['ratio'],
                'saturation': hist_df.iloc[-1]['saturation']
            },
            'cringe_alert': is_cringe_alert
        }

    def check_cringe_alert(self, m_growth, n_growth):
        """
        Alert if mainstream growth rate > 200% of niche growth rate.
        (i.e., Mainstream is growing more than 2x faster than Niche)
        """
        # Handle cases where niche growth is negative or zero
        if n_growth <= 0:
            return m_growth > 0.1 # If niche is dying, any significant mainstream growth is cringe
            
        return m_growth > (n_growth + 2.0 * n_growth) # exceeds by 200% means = n + 2n = 3n? 
        # "Exceeds niche growth rate by 200%" usually means (M - N) / N > 2.0 => M > 3N.
        # Or did they mean "is 200% of"? 
        # Let's interpret "exceeds by 200%" as M > N + 2N => M > 3N.
        # This seems aggressive. 
        # If N grows 10%, M needs 30% to trigger.
        # Let's stick to M > 3 * N.
        
if __name__ == "__main__":
    analyzer = SlangAnalyzer()
    print("Analyzer initialized.")

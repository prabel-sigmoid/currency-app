import os
from multiprocessing import process
from fastapi import FastAPI, HTTPException, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
import requests
import pandas as pd
import io
import psycopg2
from psycopg2.extras import execute_values
from contextlib import contextmanager

app = FastAPI(title="Currency Exchange Rate API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database configuration
DB_CONFIG = {
    "host": os.getenv("DB_CONFIG_HOST"),
    "database": os.getenv("DB_CONFIG_DATABASE"),
    "user": os.getenv("DB_CONFIG_USERNAME"),
    "password": os.getenv("DB_CONFIG_PASSWORD"),
    "port": os.getenv("DB_CONFIG_PORT")
}

@contextmanager
def get_db_connection():
    """Context manager for database connections"""
    conn = None
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        yield conn
        conn.commit()
    except Exception as e:
        if conn:
            conn.rollback()
        raise e
    finally:
        if conn:
            conn.close()

def init_database():
    """Initialize database tables"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Create exchange_rates table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS exchange_rates (
                    id SERIAL PRIMARY KEY,
                    date DATE NOT NULL,
                    currency VARCHAR(10) NOT NULL,
                    rate DECIMAL(18, 6) NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(date, currency)
                )
            """)
            
            # Create index for faster queries
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_exchange_rates_date_currency 
                ON exchange_rates(date, currency)
            """)
            
            # Create uploads table to track CSV uploads
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS csv_uploads (
                    id SERIAL PRIMARY KEY,
                    filename VARCHAR(255) NOT NULL,
                    upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    records_count INTEGER,
                    date_range_start DATE,
                    date_range_end DATE
                )
            """)
            
            cursor.close()
            print("Database initialized successfully")
    except Exception as e:
        print(f"Error initializing database: {str(e)}")

# Initialize database on startup
init_database()

class CurrencyRequest(BaseModel):
    currencies: List[str] = Field(..., description="List of currency codes (e.g., EUR, GBP, JPY)")
    start_date: str = Field(..., description="Start date in YYYY-MM-DD format")
    end_date: str = Field(..., description="End date in YYYY-MM-DD format")
    interval: str = Field(default="1d", description="Data interval: 1d, 1wk, 1mo")

class CurrencyData(BaseModel):
    currency: str
    dates: List[str]
    rates: List[float]
    start_rate: float
    end_rate: float
    percentage_change: float
    min_rate: float
    max_rate: float

class CurrencyResponse(BaseModel):
    data: List[CurrencyData]
    status: str
    message: Optional[str] = None
    errors: Optional[List[str]] = None

def store_exchange_rates_in_db(df: pd.DataFrame, filename: str = "api_data"):
    """Store exchange rate data in PostgreSQL database"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Prepare data for insertion
            data_to_insert = []
            for date_idx in df.index:
                for currency in df.columns:
                    rate = df.loc[date_idx, currency]
                    if pd.notna(rate):
                        data_to_insert.append((
                            date_idx.strftime('%Y-%m-%d'),
                            currency,
                            float(rate)
                        ))
            
            if data_to_insert:
                # Insert data using ON CONFLICT to handle duplicates
                execute_values(
                    cursor,
                    """
                    INSERT INTO exchange_rates (date, currency, rate)
                    VALUES %s
                    ON CONFLICT (date, currency) 
                    DO UPDATE SET rate = EXCLUDED.rate
                    """,
                    data_to_insert
                )
                
                # Log upload
                min_date = df.index.min().strftime('%Y-%m-%d')
                max_date = df.index.max().strftime('%Y-%m-%d')
                
                cursor.execute("""
                    INSERT INTO csv_uploads (filename, records_count, date_range_start, date_range_end)
                    VALUES (%s, %s, %s, %s)
                """, (filename, len(data_to_insert), min_date, max_date))
                
                cursor.close()
                print(f"Stored {len(data_to_insert)} records in database")
                # print(data_to_insert[:5])  
                return True
            return False
    except Exception as e:
        print(f"Error storing data in database: {str(e)}")
        raise e

def get_exchange_rates_from_db(currencies: List[str], start_date: str, end_date: str):
    """Retrieve exchange rates from PostgreSQL database"""
    try:
        with get_db_connection() as conn:
            query = """
                SELECT date, currency, rate
                FROM exchange_rates
                WHERE currency IN %s
                AND date BETWEEN %s AND %s
                ORDER BY date, currency
            """
            
            df = pd.read_sql_query(
                query,
                conn,
                params=(tuple(currencies), start_date, end_date)
            )
            
            if df.empty:
                return pd.DataFrame()
            
            # Pivot to get currencies as columns
            df['date'] = pd.to_datetime(df['date'])
            pivot_df = df.pivot(index='date', columns='currency', values='rate')
            pivot_df = pivot_df.sort_index()
            
            print(f"Retrieved {len(pivot_df)} rows from database")
            return pivot_df
    except Exception as e:
        print(f"Error retrieving data from database: {str(e)}")
        return pd.DataFrame()

@app.get("/")
def read_root():
    return {
        "message": "Currency Exchange Rate API",
        "version": "4.0",
        "data_source": "Frankfurter API (European Central Bank)",
        "endpoints": {
            "/currencies": "GET - List available currencies",
            "/exchange-rates": "POST - Get historical exchange rates",
            "/analyze-csv": "POST - Upload and analyze CSV (stores in database)",
            "/download-template": "GET - Download CSV template",
            "/db-stats": "GET - Database statistics"
        }
    }

@app.get("/db-stats")
def get_db_stats():
    """Get database statistics"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Total records
            cursor.execute("SELECT COUNT(*) FROM exchange_rates")
            total_records = cursor.fetchone()[0]
            
            # Unique currencies
            cursor.execute("SELECT COUNT(DISTINCT currency) FROM exchange_rates")
            unique_currencies = cursor.fetchone()[0]
            
            # Date range
            cursor.execute("SELECT MIN(date), MAX(date) FROM exchange_rates")
            date_range = cursor.fetchone()
            
            # Recent uploads
            cursor.execute("""
                SELECT filename, upload_date, records_count 
                FROM csv_uploads 
                ORDER BY upload_date DESC 
                LIMIT 5
            """)
            recent_uploads = cursor.fetchall()
            
            cursor.close()
            
            return {
                "total_records": total_records,
                "unique_currencies": unique_currencies,
                "date_range": {
                    "start": str(date_range[0]) if date_range[0] else None,
                    "end": str(date_range[1]) if date_range[1] else None
                },
                "recent_uploads": [
                    {
                        "filename": upload[0],
                        "upload_date": str(upload[1]),
                        "records_count": upload[2]
                    }
                    for upload in recent_uploads
                ]
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@app.get("/currencies")
def get_currencies():
    """Return list of supported currencies from Frankfurter API"""
    try:
        response = requests.get("https://api.frankfurter.app/currencies", timeout=10)
        if response.status_code == 200:
            currencies = response.json()
            currencies.pop("USD", None)
            print(currencies)
            return {"currencies": currencies}
        else:
            # Fallback list
            return {"currencies": get_fallback_currencies()}
    except Exception as e:
        print(f"Error fetching currencies: {str(e)}")
        return {"currencies": get_fallback_currencies()}

def get_fallback_currencies():
    """Fallback currency list if API fails"""
    return {
        "AUD": "Australian Dollar",
        "BGN": "Bulgarian Lev",
        "BRL": "Brazilian Real",
        "CAD": "Canadian Dollar",
        "CHF": "Swiss Franc",
        "CNY": "Chinese Yuan",
        "CZK": "Czech Koruna",
        "DKK": "Danish Krone",
        "EUR": "Euro",
        "GBP": "British Pound",
        "HKD": "Hong Kong Dollar",
        "HUF": "Hungarian Forint",
        "IDR": "Indonesian Rupiah",
        "ILS": "Israeli Shekel",
        "INR": "Indian Rupee",
        "ISK": "Icelandic Krona",
        "JPY": "Japanese Yen",
        "KRW": "South Korean Won",
        "MXN": "Mexican Peso",
        "MYR": "Malaysian Ringgit",
        "NOK": "Norwegian Krone",
        "NZD": "New Zealand Dollar",
        "PHP": "Philippine Peso",
        "PLN": "Polish Zloty",
        "RON": "Romanian Leu",
        "SEK": "Swedish Krona",
        "SGD": "Singapore Dollar",
        "THB": "Thai Baht",
        "TRY": "Turkish Lira",
        "ZAR": "South African Rand"
    }

def fetch_currency_data(currencies: List[str], start_date: str, end_date: str):
    """
    Returns exchange rates with USD as base currency
    """
    try:
        url = f"https://api.frankfurter.app/{start_date}..{end_date}"
        
        # Join currencies into comma-separated string
        currency_list = ",".join(currencies)
        
        # Parameters - USD as base, fetch requested currencies
        params = {
            "from": "USD",
            "to": currency_list
        }
        
        print(f"Fetching from Frankfurter API: {url}")
        print(f"Parameters: {params}")
        
        # Make request to Frankfurter API
        response = requests.get(url, params=params, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            
            # Extract rates data
            if "rates" in data:
                rates_data = data["rates"]
                
                # Convert to DataFrame
                df = pd.DataFrame(rates_data).T
                df.index = pd.to_datetime(df.index)
                df = df.sort_index()
                
                print(f"Successfully fetched data: {len(df)} rows, {len(df.columns)} currencies")
                return df
            else:
                print("No 'rates' key in response")
                return pd.DataFrame()
        else:
            print(f"API Error: {response.status_code}")
            return pd.DataFrame()
            
    except Exception as e:
        print(f"Error fetching currency data: {str(e)}")
        return pd.DataFrame()

def process_csv_data(df: pd.DataFrame, currencies: List[str], start_date: str, end_date: str):
    """Process CSV data in the format: Date, Currency, Rate"""
    try:
        # Validate required columns
        required_columns = ['Date', 'Currency', 'Rate']
        if not all(col in df.columns for col in required_columns):
            raise ValueError(f"CSV must contain columns: {', '.join(required_columns)}")
        
        # Convert Date column to datetime
        df['Date'] = pd.to_datetime(df['Date'])
        
        # Filter by date range
        start = pd.to_datetime(start_date)
        end = pd.to_datetime(end_date)
        df = df[(df['Date'] >= start) & (df['Date'] <= end)]
        
        # Filter by currencies
        df = df[df['Currency'].isin(currencies)]
        
        # Pivot the data
        pivot_df = df.pivot(index='Date', columns='Currency', values='Rate')
        pivot_df = pivot_df.sort_index()
        
        print(f"Processed CSV data: {len(pivot_df)} rows, {len(pivot_df.columns)} currencies")
        return pivot_df
    except Exception as e:
        print(f"Error processing CSV data: {str(e)}")
        raise e

def resample_data(df: pd.DataFrame, interval: str) -> pd.DataFrame:
    """
    Resample data based on interval
    """
    if df.empty:
        return df
    
    if interval == "1d":
        return df  # Daily data, no resampling needed
    elif interval == "1wk":
        return df.resample('W').last().dropna()
    elif interval == "1mo":
        return df.resample('M').last().dropna()  # 'ME' for month-end frequency
    else:
        return df

def build_currency_response(df: pd.DataFrame, currencies: List[str]) -> CurrencyResponse:
    """Build response from DataFrame"""
    result_data = []
    failed_currencies = []
    
    for currency in currencies:
        try:
            if currency not in df.columns:
                failed_currencies.append(f"{currency} (Not available in data)")
                print(f"Currency {currency} not in data")
                continue
            
            rates = df[currency].dropna()
            
            if len(rates) == 0:
                failed_currencies.append(f"{currency} (Empty dataset)")
                continue
            
            start_rate = float(rates.iloc[0])
            end_rate = float(rates.iloc[-1])
            percentage_change = ((end_rate - start_rate) / start_rate) * 100
            min_rate = float(rates.min())
            max_rate = float(rates.max())
            
            dates = [date.strftime("%Y-%m-%d") for date in rates.index]
            rates_list = [float(rate) for rate in rates.values]
            
            currency_data = CurrencyData(
                currency=currency,
                dates=dates,
                rates=rates_list,
                start_rate=start_rate,
                end_rate=end_rate,
                percentage_change=round(percentage_change, 2),
                min_rate=min_rate,
                max_rate=max_rate
            )
            
            result_data.append(currency_data)
            print(f"Successfully processed {currency}: {len(dates)} data points")
            
        except Exception as e:
            error_msg = f"{currency} ({str(e)[:100]})"
            failed_currencies.append(error_msg)
            print(f"Error processing {currency}: {str(e)}")
            continue
    
    if not result_data:
        return CurrencyResponse(
            data=[],
            status="error",
            message="No data found for any of the specified currencies",
            errors=failed_currencies if failed_currencies else None
        )
    
    success_msg = f"Successfully retrieved data for {len(result_data)} out of {len(currencies)} currencies"
    
    return CurrencyResponse(
        data=result_data,
        status="success" if not failed_currencies else "partial",
        message=success_msg,
        errors=failed_currencies if failed_currencies else None
    )

@app.post("/exchange-rates", response_model=CurrencyResponse)
def get_exchange_rates(request: CurrencyRequest):
    """
    Fetch historical exchange rates for specified currencies against USD
    """
    try:
        # Validate dates
        start = datetime.strptime(request.start_date, "%Y-%m-%d")
        end = datetime.strptime(request.end_date, "%Y-%m-%d")
        
        if start >= end:
            raise HTTPException(status_code=400, detail="Start date must be before end date")
        
        if end > datetime.now():
            raise HTTPException(status_code=400, detail="End date cannot be in the future")
        
        if start.year < 1999:
            raise HTTPException(status_code=400, detail="Start date must be 1999-01-04 or later")
        
        # Validate interval
        valid_intervals = ["1d", "1wk", "1mo"]
        if request.interval not in valid_intervals:
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid interval. Must be one of: {', '.join(valid_intervals)}"
            )
        
        # Fetch data for all currencies at once
        df = fetch_currency_data(request.currencies, request.start_date, request.end_date)
        
        if df.empty:
            return CurrencyResponse(
                data=[],
                status="error",
                message="No data found for the specified criteria",
                errors=["Failed to fetch data from Frankfurter API"]
            )
        
        # Resample based on interval
        df = resample_data(df, request.interval)
        
        if df.empty:
            return CurrencyResponse(
                data=[],
                status="error",
                message="No data available after resampling",
                errors=["Data is empty after applying the selected interval"]
            )
        
        result_data = []
        failed_currencies = []
        
        # Process each currency
        for currency in request.currencies:
            try:
                if currency not in df.columns:
                    failed_currencies.append(f"{currency} (Not available in API response)")
                    print(f"Currency {currency} not in data")
                    continue
                
                # Extract rates for this currency
                rates = df[currency].dropna()
                
                if len(rates) == 0:
                    failed_currencies.append(f"{currency} (Empty dataset)")
                    continue
                
                # Calculate statistics
                start_rate = float(rates.iloc[0])
                end_rate = float(rates.iloc[-1])
                percentage_change = ((end_rate - start_rate) / start_rate) * 100
                min_rate = float(rates.min())
                max_rate = float(rates.max())
                
                # Format dates and rates
                dates = [date.strftime("%Y-%m-%d") for date in rates.index]
                rates_list = [float(rate) for rate in rates.values]
                
                currency_data = CurrencyData(
                    currency=currency,
                    dates=dates,
                    rates=rates_list,
                    start_rate=start_rate,
                    end_rate=end_rate,
                    percentage_change=round(percentage_change, 2),
                    min_rate=min_rate,
                    max_rate=max_rate
                )
                
                result_data.append(currency_data)
                print(f"Successfully processed {currency}: {len(dates)} data points")
                
            except Exception as e:
                error_msg = f"{currency} ({str(e)[:100]})"
                failed_currencies.append(error_msg)
                print(f"Error processing {currency}: {str(e)}")
                continue
        
        # Prepare response
        if not result_data:
            return CurrencyResponse(
                data=[],
                status="error",
                message="No data found for any of the specified currencies",
                errors=failed_currencies if failed_currencies else None
            )
        
        # Prepare success message
        success_msg = f"Successfully retrieved data for {len(result_data)} out of {len(request.currencies)} currencies"
        
        # print(result_data)

        return CurrencyResponse(
            data=result_data,
            status="success" if not failed_currencies else "partial",
            message=success_msg,
            errors=failed_currencies if failed_currencies else None
        )
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid date format: {str(e)}")
    except Exception as e:
        print(f"Error in get_exchange_rates: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.post("/analyze-csv", response_model=CurrencyResponse)
async def analyze_csv(
    file: UploadFile = File(...),
    currencies: str = "",
    start_date: str = "",
    end_date: str = "",
    interval: str = "1d"
):
    """Analyze exchange rates from uploaded CSV file and store in database"""
    try:
        # Read CSV file
        contents = await file.read()
        df = pd.read_csv(io.StringIO(contents.decode('utf-8')))
        
        # Validate CSV format
        required_columns = ['Date', 'Currency', 'Rate']
        if not all(col in df.columns for col in required_columns):
            raise HTTPException(
                status_code=400, 
                detail=f"CSV must contain columns: {', '.join(required_columns)}"
            )
        
        # Parse currencies from comma-separated string
        currency_list = [c.strip() for c in currencies.split(',') if c.strip()] if currencies else df['Currency'].unique().tolist()
        
        # Use date range from CSV if not provided
        if not start_date:
            start_date = pd.to_datetime(df['Date']).min().strftime("%Y-%m-%d")
        if not end_date:
            end_date = pd.to_datetime(df['Date']).max().strftime("%Y-%m-%d")
        
        # Process the CSV data
        processed_df = process_csv_data(df, currency_list, start_date, end_date)
        
        if processed_df.empty:
            return CurrencyResponse(
                data=[],
                status="error",
                message="No data found in CSV for the specified criteria",
                errors=["Failed to process CSV data"]
            )
        
        # Store in database
        try:
            store_exchange_rates_in_db(processed_df, file.filename)
        except Exception as db_error:
            print(f"Warning: Failed to store in database: {str(db_error)}")
            # Continue even if database storage fails
        
        # Resample based on interval
        processed_df = resample_data(processed_df, interval)
        
        if processed_df.empty:
            return CurrencyResponse(
                data=[],
                status="error",
                message="No data available after resampling",
                errors=["Data is empty after applying the selected interval"]
            )
        
        return build_currency_response(processed_df, currency_list)
        
    except Exception as e:
        print(f"Error in analyze_csv: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing CSV: {str(e)}")

@app.get("/download-template")
def download_template():
    """Download CSV template"""
    csv_content = """Date,Currency,Rate
2024-01-01,EUR,0.92
2024-01-01,GBP,0.78
2024-01-01,JPY,140.50
2024-01-02,EUR,0.93
2024-01-02,GBP,0.79
2024-01-02,JPY,141.20"""
    
    return StreamingResponse(
        io.StringIO(csv_content),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=exchange_rates_template.csv"}
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
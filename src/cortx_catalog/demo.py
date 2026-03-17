"""Demo data generation module."""

import os
import sqlite3
from datetime import datetime, timedelta
from typing import Tuple

import numpy as np
import pandas as pd


def create_demo_data(base_dir: str = "demo_data") -> str:
    """Create synthetic demo data for testing.
    
    Args:
        base_dir: Directory to create demo data in
        
    Returns:
        Path to demo directory
    """
    os.makedirs(base_dir, exist_ok=True)
    
    # Create SQLite database with trading data
    create_trading_database(os.path.join(base_dir, "trading.db"))
    
    # Create CSV with customer data
    create_customer_csv(os.path.join(base_dir, "customers.csv"))
    
    # Create Parquet with product data
    create_product_parquet(os.path.join(base_dir, "products.parquet"))
    
    return base_dir


def create_trading_database(db_path: str) -> None:
    """Create SQLite database with trading data.
    
    Args:
        db_path: Path to database file
    """
    # Remove existing database
    if os.path.exists(db_path):
        os.remove(db_path)
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Create positions table
    cursor.execute("""
        CREATE TABLE positions (
            id INTEGER PRIMARY KEY,
            portfolio_id INTEGER NOT NULL,
            ticker TEXT NOT NULL,
            quantity REAL NOT NULL,
            price REAL NOT NULL,
            date DATE NOT NULL,
            sector TEXT
        )
    """)
    
    # Create trades table
    cursor.execute("""
        CREATE TABLE trades (
            trade_id TEXT PRIMARY KEY,
            portfolio_id INTEGER NOT NULL,
            ticker TEXT NOT NULL,
            side TEXT NOT NULL,
            quantity REAL NOT NULL,
            price REAL NOT NULL,
            timestamp DATETIME NOT NULL
        )
    """)
    
    # Generate positions data
    np.random.seed(42)
    tickers = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "NVDA", "META", "JPM", "BAC", "XOM"]
    sectors = ["Technology", "Technology", "Technology", "Consumer", "Auto", "Technology", "Technology", "Finance", "Finance", "Energy"]
    
    positions_data = []
    for i in range(1000):
        ticker_idx = np.random.randint(0, len(tickers))
        positions_data.append({
            "id": i + 1,
            "portfolio_id": np.random.randint(1, 51),
            "ticker": tickers[ticker_idx],
            "quantity": np.random.randint(100, 10000),
            "price": round(np.random.uniform(50, 500), 2),
            "date": (datetime.now() - timedelta(days=np.random.randint(0, 365))).strftime("%Y-%m-%d"),
            "sector": sectors[ticker_idx],
        })
    
    # Insert positions
    for pos in positions_data:
        cursor.execute("""
            INSERT INTO positions VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (pos["id"], pos["portfolio_id"], pos["ticker"], pos["quantity"], pos["price"], pos["date"], pos["sector"]))
    
    # Generate trades data
    trades_data = []
    for i in range(5000):
        ticker_idx = np.random.randint(0, len(tickers))
        timestamp = datetime.now() - timedelta(days=np.random.randint(0, 365), hours=np.random.randint(0, 24))
        trades_data.append({
            "trade_id": f"TXN{i+1:06d}",
            "portfolio_id": np.random.randint(1, 51),
            "ticker": tickers[ticker_idx],
            "side": np.random.choice(["BUY", "SELL"]),
            "quantity": np.random.randint(10, 1000),
            "price": round(np.random.uniform(50, 500), 2),
            "timestamp": timestamp.strftime("%Y-%m-%d %H:%M:%S"),
        })
    
    # Insert trades
    for trade in trades_data:
        cursor.execute("""
            INSERT INTO trades VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (trade["trade_id"], trade["portfolio_id"], trade["ticker"], trade["side"], trade["quantity"], trade["price"], trade["timestamp"]))
    
    conn.commit()
    conn.close()
    
    print(f"Created trading database: {db_path}")


def create_customer_csv(csv_path: str) -> None:
    """Create CSV file with customer data including PII.
    
    Args:
        csv_path: Path to CSV file
    """
    np.random.seed(42)
    
    first_names = ["John", "Jane", "Bob", "Alice", "Charlie", "Diana", "Edward", "Fiona", "George", "Hannah"]
    last_names = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis", "Rodriguez", "Martinez"]
    domains = ["gmail.com", "yahoo.com", "outlook.com", "company.com"]
    
    customers = []
    for i in range(500):
        first = np.random.choice(first_names)
        last = np.random.choice(last_names)
        email = f"{first.lower()}.{last.lower()}{np.random.randint(1, 999)}@{np.random.choice(domains)}"
        
        customers.append({
            "customer_id": i + 1,
            "first_name": first,
            "last_name": last,
            "email": email,
            "phone": f"+1-555-{np.random.randint(100, 999)}-{np.random.randint(1000, 9999)}",
            "signup_date": (datetime.now() - timedelta(days=np.random.randint(0, 730))).strftime("%Y-%m-%d"),
            "tier": np.random.choice(["basic", "premium", "enterprise"], p=[0.6, 0.3, 0.1]),
            "lifetime_value": round(np.random.uniform(100, 50000), 2),
        })
    
    df = pd.DataFrame(customers)
    df.to_csv(csv_path, index=False)
    print(f"Created customer CSV: {csv_path}")


def create_product_parquet(parquet_path: str) -> None:
    """Create Parquet file with product inventory data.
    
    Args:
        parquet_path: Path to Parquet file
    """
    np.random.seed(42)
    
    categories = ["Electronics", "Clothing", "Home & Garden", "Sports", "Books", "Food"]
    products = []
    
    for i in range(200):
        category = np.random.choice(categories)
        base_price = np.random.uniform(10, 500)
        
        products.append({
            "product_id": f"SKU{i+1:05d}",
            "name": f"Product {i+1}",
            "category": category,
            "price": round(base_price, 2),
            "cost": round(base_price * np.random.uniform(0.4, 0.7), 2),
            "stock_quantity": np.random.randint(0, 1000),
            "supplier_id": np.random.randint(1, 20),
            "created_date": (datetime.now() - timedelta(days=np.random.randint(0, 1000))).strftime("%Y-%m-%d"),
            "is_active": np.random.choice([True, False], p=[0.9, 0.1]),
        })
    
    df = pd.DataFrame(products)
    df.to_parquet(parquet_path, index=False)
    print(f"Created product Parquet: {parquet_path}")


if __name__ == "__main__":
    demo_dir = create_demo_data()
    print(f"\nDemo data created in: {demo_dir}")

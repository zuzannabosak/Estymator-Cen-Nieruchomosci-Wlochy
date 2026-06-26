# Italian Real Estate Price Predictor

A data-driven application designed to help users estimate the market value of properties in Italy (and check if the price that is offered is fair). It combines web scraping, linear regression, random forest models and an intuitive user interface to combine data analysis and practical real estate insights.

It provides users with:

- **Price Estimations:** Two distinct ML models (Linear Regression & Random Forest) to calculate property values.
- **Market Benchmarking:** A comparison tool that assesses whether a specific offer is a "bargain," "fair value," or "overpriced."
- **Data-Driven Insights:** A comprehensive scraping pipeline that collects real-time listings from the Italian market.


## How it works?
1. The scraper collects raw data, cleans it, and engineers features (e.g., extracting amenities like "sea view" or "elevator" from text descriptions).
2. Using historical data we train models to understand the relationship between property size, location, and market price.
3. Application (GUI) allows users to input property details. The input is being proccessed and we get an estimated market range (±15% of predicted value).

## The structure
- `main2.py`: The core GUI application.
- `scraper.py` & `generator_linkow.py`: Data collection scripts.
- `test_main2.py` & `test_scraper.py`: Automated test suites ensuring code reliability.
- `models/`: Pre-trained ML models.
- `dokumentacja/`: Automatically generated HTML documentation for the code.


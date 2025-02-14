## Abstract

This API leverages a combinatory approach to calculate price elasticity across all possible pairs of historical price–demand points. Unlike spreadsheets (such as Excel), which are not well-suited to handle all elasticity combinations, our method systematically computes **n * (n - 1) / 2** different elasticity values **epsilon_{i,j}**. Each **epsilon_{i,j}** is defined as:

```
epsilon_{i,j} = (Q_j - Q_i) / (P_j - P_i)
```

where **P_i** and **Q_i** (respectively **P_j** and **Q_j**) refer to the price and demand of the i-th (resp. j-th) historical data point.

Given an elasticity **epsilon** and a percentage change in price **Delta P%**, the API computes the new demand (**Q_new**) from the previous demand (**Q_previous**):

```
Q_new = Q_previous * (1 + epsilon * Delta P%)
```

IT is a tool, that allows the company to forecast effectively the new demand given a simple historical data, it can process multiple SKu's (product id's) and computes all possible elasticities. Returns a Graph and the .xslx file with the new demand (in order for the Company to evaluate the cost for example of a Commercial Operation)

# Elastic Price Variation Calculation API

An API for calculating price elasticity variations and forecasting demand based on historical price and demand data using logarithmic regression.

## Project Overview

This API leverages the economic principle of price elasticity of demand **epsilon = (Delta Q) / (Delta P)** to forecast demand variations in response to price changes. The tool is particularly designed for use in e-commerce scenarios, where price points—including psychological pricing—impact consumer demand.

## Features

- **Elasticity Calculation**: Computes price elasticity using historical price and demand data from two indicators (`indicators1` and `indicators2`).
- **Logarithmic Regression**: Utilizes logarithmic regression to generate additional price-demand data points from a limited historical dataset.
- **Demand Forecasting**: Given a dataset with new and old prices, calculates the percentage change in price (Delta P%) and predicts new demand using the computed elasticities.
- **E-commerce Ready**: Proven forecasting precision of 50% in e-commerce applications.
- **User-Friendly API**: Provides a client-friendly interface to upload data, calculate elasticity, and retrieve demand forecasts.

## Data Inputs

- **Indicators**:
  - `indicators1` and `indicators2` files with features such as:
    - `PRODUCT_ID`: Product identifier
    - `PRIX_TTC`: Price including tax
    - `PREVISION_J1`: Demand forecast for day J+1
    - `Delta_P`: Percentage price change
    - `Sales_J_1`: Sales on day J-1
    - Additional computed columns: `Elasticity`, `P_i`, `P_j`, `Q_i`, `Q_j`, `Delta_P_rel`, `i`, `j`

## API Endpoints

### `POST /api/v1/calculate-elasticity`
- **Description**: Upload historical price and demand data from indicators.
- **Request Body**:
  - `indicators1`: File path for the first indicators dataset.
  - `indicators2`: File path for the second indicators dataset.
- **Response**:
  - `elasticities`: Computed elasticity values for each price point.

### `POST /api/v1/forecast-demand`
- **Description**: Submit new and old prices to forecast demand changes.
- **Request Body**:
  - `old_prices`: List of previous prices.
  - `new_prices`: List of updated prices.
- **Response**:
  - `forecasted_demand`: List of predicted demand values based on elasticity and price variations.

## Technical Details

- **Elasticity Formula**: `epsilon = (Delta Q%) / (Delta P%)`
- **Logarithmic Regression**:
  - Generates synthetic price-demand pairs from limited historical data.
  - Improves accuracy of demand forecasting.
- **Supported Data Formats**: JSON, CSV for input/output.

## Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/elastic-price-api.git

# Navigate to project directory
cd elastic-price-api

# Install dependencies
pip install -r requirements.txt

# Run the API
uvicorn main:app --reload
```

## Usage

- Send historical data to the API to compute elasticity.
- Use computed elasticities to forecast demand by providing new price points.

## Performance

- Achieved 50% forecasting precision in real-world e-commerce price elasticity scenarios.

## Contribution

- Fork the repository and create a new branch.
- Commit your changes and create a pull request.

## License

This project is licensed under the MIT License.

## Contact

For further inquiries or support, contact [bernannouissam1@gmail.com](mailto:bernannouissam1@gmail.com).





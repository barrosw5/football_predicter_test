# ⚽ Premier League Match Predictor

This repository contains an advanced **Machine Learning** system designed to predict the outcomes of English Premier League matches.

This project has evolved to **Version 4.5**, shifting from simple models to **XGBoost**, integrating advanced metrics like **Expected Goals (xG)**, and implementing a specific optimization strategy to better predict draws.

## 📋 Project Overview

The goal is to solve a **Multi-Class Classification Problem** (Home Win, Draw, Away Win) by leveraging historical match data, advanced statistics, and betting odds to find value in predictions.

### Key Features
Unlike basic statistical models, this project includes:
1.  **Automated Web Scraping:** Real-time collection of *xG* data (from Understat) and match results (from Football-Data).
2.  **Dynamic Elo System:** Implementation of a custom Elo rating algorithm that updates match-by-match.
3.  **Optimized XGBoost:** Utilizes *Gradient Boosting* with specific sample weights to handle class imbalance (giving more importance to Draws).
4.  **Leakage Prevention:** Ensures the model does not "see" the future during training by using time-lagged rolling averages for all statistics.

## 🧠 Methodology (Pipeline)

The `football_predicter.ipynb` notebook handles the entire end-to-end process:

1.  **Data Acquisition:**
    * Scrapes data from the 2005 season up to 2025.
    * Merges classic stats (Goals, Corners, Shots) with *Expected Goals* (xG) data.
    * Cleans and normalizes team names across different data sources.

2.  **Feature Engineering:**
    * Calculation of **Elo Ratings** (Home and Away).
    * Rolling Stats (last 5 games) for: Points, Goals (scored/conceded), Shots on Target, and xG.
    * Conversion of Bet365 Odds into implied probabilities.

3.  **Modeling & Training:**
    * **Algorithm:** XGBoost Classifier (`objective='multi:softprob'`).
    * **Tuning:** Uses `GridSearchCV` with `TimeSeriesSplit` to find the best hyperparameters without violating the temporal order of games.
    * **Class Weighting:** Applies a weight of `1.3` to draw results to force the model to learn these harder-to-predict patterns.

## 🛠️ Tech Stack

* **Python 3.10+**
* **Jupyter Notebook:** Development environment.
* **XGBoost:** The core Machine Learning engine.
* **Pandas & NumPy:** Data manipulation and cleaning.
* **Scikit-Learn:** Evaluation metrics, *Grid Search*, and preprocessing.
* **BeautifulSoup (bs4) & Requests:** Web scraping.
* **Matplotlib & Seaborn:** Visualization of performance and confusion matrices.

## 🚀 How to Run

### 1. Install Dependencies
Ensure you have the required libraries installed. You can install them via pip:

```bash
pip install pandas numpy xgboost scikit-learn matplotlib seaborn beautifulsoup4 requests joblib

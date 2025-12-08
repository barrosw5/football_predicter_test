# ⚽ Premier League Match Predictor (v4.5)

![Python](https://img.shields.io/badge/Python-3.10%2B-blue)
![XGBoost](https://img.shields.io/badge/Model-XGBoost-orange)
![Status](https://img.shields.io/badge/Status-Active-success)

An advanced Machine Learning system designed to predict **English Premier League** match outcomes. This project moves beyond basic statistics by integrating **Expected Goals (xG)**, a dynamic **Elo Rating System**, and a specialized **XGBoost** model optimized to detect value bets and draws.

---

## 📋 Project Overview

The goal is to solve the classic football prediction problem (Home Win, Draw, Away Win) by combining historical data with modern advanced metrics.

**Current Version (v4.5)** focuses on:
* **Draw Prediction:** Specific sample weighting to solve the "draw blindness" common in ML models.
* **xG Integration:** Scraping and merging *Expected Goals* data to assess team performance better than just goals scored.
* **Value Betting:** Comparing model probabilities against Bookmaker Odds to find positive Expected Value (EV).

---

## 🧠 Key Features

| Feature | Description |
| :--- | :--- |
| **🕷️ Automated Scraping** | Fetches live xG data from **Understat** and match results from **Football-Data.co.uk**. |
| **📈 Dynamic Elo** | Calculates custom Elo Ratings updated match-by-match to track team strength momentum. |
| **🤖 XGBoost Engine** | Uses Gradient Boosting with `GridSearchCV` to find the perfect mathematical balance. |
| **🛡️ Time-Series Split** | Validates the model chronologically to prevent "future leakage" (cheating). |
| **💰 Value Detector** | Compares AI probabilities vs. Implied Odds to recommend "Value Bets". |

---

## 🛠️ Installation & Setup

1.  **Clone the repository:**
    ```bash
    git clone [https://github.com/barrosw5/football_match_predicter.git](https://github.com/barrosw5/football_match_predicter.git)
    cd football_match_predicter
    ```

2.  **Install dependencies:**
    ```bash
    pip install pandas numpy xgboost scikit-learn matplotlib seaborn beautifulsoup4 requests joblib
    ```

3.  **Run the Notebook:**
    Open `football_predicter.ipynb` in Jupyter Notebook or VS Code and run all cells to train the model.

---

## 🚀 How to Use

Once the model is trained (by running the notebook), use the `predict_match_advanced` function at the bottom of the notebook to get predictions for upcoming games.

### Example Usage:
```python
# Predict a match by providing the date, teams, and bookmaker odds
predict_match_advanced(
    date_str='2025-12-08', 
    home_team='Wolves', 
    away_team='Man United', 
    odd_h=4.45,  # Home Odd
    odd_d=3.93,  # Draw Odd
    odd_a=1.67,  # Away Odd
    odd_1x=2.02, # Double Chance 1X
    odd_12=1.22, # Double Chance 12
    odd_x2=1.18  # Double Chance X2
)

# ⚽ Premier League Match Predictor

This repository explores the application of **Machine Learning (Classification)** to predict the outcome of Premier League football matches.

The goal is to apply theoretical concepts of Linear Classification and Softmax Regression (learned in class with `numpy`) to a real-world scenario using production-grade tools like `scikit-learn`.

## 📋 Project Overview

This project solves a **Multi-Class Classification Problem**: predicting the Full Time Result (FTR) of a match.

### The Challenge
Given historical match data and betting odds, can we predict the outcome?
* **Input ($X$):** Home Team, Away Team, Pre-match Odds (Bet365)...
* **Output ($y$):** One of three classes:
    * `0`: Away Win
    * `1`: Draw
    * `2`: Home Win

### Methodology
1.  **Data Collection:** Automated download of historical Premier League data (last 5 seasons) from *Football-Data.co.uk*.
2.  **Preprocessing:** Converting categorical data (Team Names, Results) into numerical formats suitable for ML models.
3.  **Modeling:** Training a **Random Forest Classifier** to learn patterns from past matches.
4.  **Evaluation:** Measuring performance using **Accuracy** and **Confusion Matrices**.

## 🛠️ Tech Stack

* **Language:** Python 3
* **Environment:** VS Code + Jupyter Notebooks (`.ipynb`)
* **Libraries:**
    * `pandas` & `numpy`: Data manipulation and cleaning.
    * `matplotlib` & `seaborn`: Data visualization.
    * `scikit-learn`: Machine Learning models and evaluation metrics.

## 📚 Data Source

Historical match results and betting odds are sourced from the reputable data archive:
* [Football-Data.co.uk](https://www.football-data.co.uk/englandm.php)

---

### 🚀 How to Run

1.  **Install dependencies:**
    ```bash
    pip install pandas numpy matplotlib seaborn scikit-learn jupyter
    ```
2.  **Open the Project:** Launch VS Code in the repository folder.
3.  **Run the Notebook:** Open and execute `Match_Predictor.ipynb`. The code will automatically download the necessary data and train the model.

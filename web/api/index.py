from flask import Flask, request, jsonify
from flask_cors import CORS
import joblib
import pandas as pd
import numpy as np
from scipy.stats import poisson
import os

app = Flask(__name__)
CORS(app)

# Carregar o cérebro
try:
    # Procura o ficheiro na mesma pasta onde este script está (pasta 'api')
    model_path = os.path.join(os.path.dirname(__file__), 'football_brain.pkl')
    artifacts = joblib.load(model_path)
except Exception as e:
    # Se falhar, mostra o erro no log do Vercel para sabermos o que foi
    print(f"ERRO AO CARREGAR MODELO: {e}")
    # Cria um artefacto vazio para não crashar o import, mas vai dar erro na previsão
    artifacts = None

model_multi = artifacts['model_multi']
model_sniper = artifacts['model_sniper']
model_shield = artifacts['model_shield']
xgb_goals_h = artifacts['model_goals_h']
xgb_goals_a = artifacts['model_goals_a']
features_list = artifacts['features']
df_ready = artifacts['history_df']
le_div = artifacts['le_div']
elos = artifacts['elos']

@app.route('/api/index', methods=['POST'])
def predict():
    data = request.json
    
    # 1. Inputs
    home = data.get('home_team')
    away = data.get('away_team')
    div = data.get('division')
    date_str = data.get('date')
    
    try:
        odd_h = float(data['odd_h'])
        odd_d = float(data['odd_d'])
        odd_a = float(data['odd_a'])
        odd_1x = float(data['odd_1x'] or 0)
        odd_x2 = float(data['odd_x2'] or 0)
        odd_12 = float(data['odd_12'] or 0)
    except:
        return jsonify({'error': 'Odds inválidas'}), 400

    match_date = pd.to_datetime(date_str)
    past_data = df_ready[df_ready['Date'] < match_date].copy()

    # 2. Validação de Liga (O teu "Warning")
    warning_msg = None
    if div != 'CL':
        for team in [home, away]:
            team_games = df_ready[(df_ready['HomeTeam'] == team) | (df_ready['AwayTeam'] == team)].tail(20)
            if not team_games.empty:
                leagues = team_games[team_games['Div'] != 'CL']['Div'].value_counts()
                if not leagues.empty:
                    main_league = leagues.index[0]
                    if main_league != div:
                        warning_msg = f"{team} costuma jogar na liga {main_league}, mas selecionaste {div}. Confirma!"

    # 3. Features
    def get_val(team):
        last = past_data[(past_data['HomeTeam']==team)|(past_data['AwayTeam']==team)]
        if not last.empty:
            return last.iloc[-1]['Home_Value'] if last.iloc[-1]['HomeTeam']==team else last.iloc[-1]['Away_Value']
        return 200

    def get_context(team):
        games = past_data[(past_data['HomeTeam']==team)|(past_data['AwayTeam']==team)]
        if games.empty: return 0.5, 10, 7
        last = games.iloc[-1]
        pos = last['Home_Pos'] if last['HomeTeam']==team else last['Away_Pos']
        rest = (match_date - last['Date']).days
        motiv = 1.3 if div == 'CL' else (0.5 if 6 < pos < 16 and len(games) > 28 else 1.2)
        return motiv, pos, rest

    h_motiv, h_pos, h_rest = get_context(home)
    a_motiv, a_pos, a_rest = get_context(away)
    h_val = get_val(home); a_val = get_val(away)
    
    input_data = {}
    input_data['Home_Motiv'] = h_motiv; input_data['Away_Motiv'] = a_motiv
    input_data['Rest_Home'] = h_rest; input_data['Rest_Away'] = a_rest
    input_data['Home_Value'] = h_val; input_data['Away_Value'] = a_val
    input_data['Value_Ratio'] = np.log1p(h_val) - np.log1p(a_val)
    input_data['Is_Cup'] = 1 if div == 'CL' else 0
    
    input_data['HomeElo'] = elos.get(home, 1500)
    input_data['AwayElo'] = elos.get(away, 1500)
    input_data['EloDiff'] = input_data['HomeElo'] - input_data['AwayElo']
    input_data['Home_Pos'] = h_pos; input_data['Away_Pos'] = a_pos
    input_data['Home_Pts'] = 0; input_data['Away_Pts'] = 0 # Simplificação
    
    # Has_xG
    input_data['Has_xG_Data'] = 1 if div in ['E0','D1','SP1','F1','I1','CL'] else 0
    
    try: input_data['Div_Code'] = le_div.transform([div])[0]
    except: input_data['Div_Code'] = 0
    
    input_data['Imp_Home'] = 1/odd_h; input_data['Imp_Draw'] = 1/odd_d; input_data['Imp_Away'] = 1/odd_a

    # Stats Lookup Simplificado
    for f in features_list:
        if f not in input_data: input_data[f] = 0
    
    # 4. Previsão
    X = pd.DataFrame([input_data])[features_list]
    
    probs = model_multi.predict_proba(X)[0] # Away, Draw, Home
    prob_a, prob_d, prob_h = probs[0], probs[1], probs[2]
    
    try: conf_shield = model_shield.predict_proba(X)[0][1]
    except: conf_shield = prob_h + prob_d
    
    xg_h = float(xgb_goals_h.predict(X)[0])
    xg_a = float(xgb_goals_a.predict(X)[0])
    
    # Matriz
    max_goals = 6
    score_matrix = []
    best_score_prob = -1
    best_score_txt = "0-0"
    for h in range(max_goals):
        row = []
        for a in range(max_goals):
            p = poisson.pmf(h, xg_h) * poisson.pmf(a, xg_a)
            row.append(p)
            if p > best_score_prob:
                best_score_prob = p
                best_score_txt = f"{h}-{a}"
        score_matrix.append(row)
        
    # 5. Scanner
    scanner = []
    def analyze(name, odd, prob):
        if not odd or odd <= 1: return
        ev = (prob * odd) - 1
        status = "💎 VALOR!" if ev > 0.05 else ("✅ VALOR" if ev > 0 else ("😐 JUSTO" if ev > -0.05 else "❌ FRACO"))
        scanner.append({'name': name, 'odd': f"{odd:.2f}", 'prob': prob, 'ev': ev, 'status': status})

    analyze(f"Vitoria {home}", odd_h, prob_h)
    analyze("Empate", odd_d, prob_d)
    analyze(f"Vitoria {away}", odd_a, prob_a)
    
    if odd_1x > 1: analyze("DC 1X", odd_1x, ((prob_h+prob_d)+conf_shield)/2)
    if odd_x2 > 1: analyze("DC X2", odd_x2, prob_a+prob_d)
    if odd_12 > 1: analyze("DC 12", odd_12, prob_h+prob_a)
    
    scanner.sort(key=lambda x: x['ev'], reverse=True)
    best = scanner[0]
    likely = sorted(scanner, key=lambda x: x['prob'], reverse=True)[0]
    
    return jsonify({
        'xg': {'home': f"{xg_h:.2f}", 'away': f"{xg_a:.2f}"},
        'score_matrix': score_matrix,
        'most_likely_score': f"{best_score_txt} ({best_score_prob:.1%})",
        'market_scanner': scanner,
        'best_pick': {'name': best['name'], 'odd': best['odd'], 'ev_txt': f"{best['ev']:.1%}"},
        'most_likely': {'name': likely['name'], 'prob_txt': f"{likely['prob']:.1%}"},
        'warning': warning_msg
    })

if __name__ == '__main__':
    app.run(port=5000, debug=True)
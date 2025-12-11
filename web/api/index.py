from flask import Flask, request, jsonify
from flask_cors import CORS
import joblib
import os
import requests
import pandas as pd
import numpy as np
from scipy.stats import poisson
import traceback

app = Flask(__name__)
CORS(app)

API_KEY = "81f8d50f4cac1f4ac373794f18440676" 

# Mapeamento de Ligas (Inclui agora Europa League e Conference League como 'CL')
LEAGUE_MAP = {
    39: 'E0', 78: 'D1', 140: 'SP1', 61: 'F1', 135: 'I1',
    40: 'E1', 79: 'D2', 141: 'SP2', 62: 'F2', 136: 'I2',
    94: 'P1', 88: 'N1', 144: 'B1', 203: 'T1', 197: 'G1', 179: 'SC0',
    2: 'CL',
    # --- NOVAS LIGAS EUROPEIAS ---
    3: 'CL',   # Liga Europa
    848: 'CL'  # Liga Conferência
}

# --- CARREGAMENTO ---
model_path = os.path.join(os.path.dirname(__file__), 'football_brain.pkl')

model_multi = None
xgb_goals_h = None
df_ready = pd.DataFrame()

print(f"\n🔄 A INICIAR SERVIDOR...")
if os.path.exists(model_path):
    try:
        artifacts = joblib.load(model_path)
        model_multi = artifacts.get('model_multi')
        model_shield = artifacts.get('model_shield')
        xgb_goals_h = artifacts.get('xgb_goals_h') or artifacts.get('model_goals_h')
        xgb_goals_a = artifacts.get('xgb_goals_a') or artifacts.get('model_goals_a')
        le_div = artifacts.get('le_div')
        features = artifacts.get('features')
        current_elos = artifacts.get('current_elos', {})
        df_ready = artifacts.get('df_ready', pd.DataFrame())
        print("✅ MODELOS CARREGADOS!")
    except Exception as e:
        print(f"❌ ERRO CRÍTICO: {e}")
else:
    print(f"❌ Ficheiro não encontrado: {model_path}")


# --- ROTA 1: BUSCAR JOGOS ---
@app.route('/api/fixtures', methods=['POST'])
def get_fixtures():
    try:
        data = request.get_json()
        url = "https://v3.football.api-sports.io/fixtures"
        
        # Pede todos os jogos do dia (sem filtrar status)
        params = {'date': data.get('date')}
        headers = {'x-rapidapi-key': API_KEY, 'x-rapidapi-host': "v3.football.api-sports.io"}

        print(f"📡 A pedir jogos à API para data: {data.get('date')}...")
        response = requests.get(url, headers=headers, params=params)
        
        if response.status_code != 200:
            print(f"❌ Erro API Status: {response.status_code}")
            return jsonify([])

        fixtures_data = response.json().get('response', [])
        total_games = len(fixtures_data)
        supported_matches = []

        for f in fixtures_data:
            lid = f['league']['id']
            lname = f['league']['name']
            
            if lid in LEAGUE_MAP:
                supported_matches.append({
                    'id': f['fixture']['id'], # IMPORTANTE: ID necessário para buscar odds
                    'home_team': f['teams']['home']['name'],
                    'away_team': f['teams']['away']['name'],
                    'division': LEAGUE_MAP[lid],
                    'league_name': lname, 
                    'country': f['league']['country'],
                    'match_time': f['fixture']['date'].split('T')[1][:5],
                    'homeTeam': f['teams']['home']['name'],
                    'awayTeam': f['teams']['away']['name'],
                    'status_short': f['fixture']['status']['short']
                })

        supported_matches.sort(key=lambda x: (x['league_name'], x['match_time']))
        
        print(f"✅ Jogos: {total_games} recebidos -> {len(supported_matches)} suportados.")
        return jsonify(supported_matches)

    except Exception as e:
        print(f"❌ Erro API Crítico: {e}")
        traceback.print_exc()
        return jsonify([])


# --- ROTA 2: BUSCAR ODDS (Prioridade: Betclic -> Bet365 -> Qualquer) ---
@app.route('/api/odds', methods=['POST'])
def get_odds():
    try:
        data = request.get_json()
        fid = data.get('fixture_id')
        
        # Não definimos 'bookmaker' no pedido para recebermos a lista de todos
        url = "https://v3.football.api-sports.io/odds"
        params = {'fixture': fid} 
        headers = {'x-rapidapi-key': API_KEY, 'x-rapidapi-host': "v3.football.api-sports.io"}
        
        response = requests.get(url, headers=headers, params=params)
        resp_json = response.json()
        
        if not resp_json.get('response'):
            return jsonify({"error": "Odds indisponíveis"})
            
        all_bookmakers = resp_json['response'][0]['bookmakers']
        if not all_bookmakers: return jsonify({"error": "Sem bookies"})
        
        # --- LÓGICA DE PRIORIDADE ---
        # 1. Tenta encontrar Betclic
        target_bookie = next((b for b in all_bookmakers if "Betclic" in b['name']), None)
        
        # 2. Se não houver Betclic, tenta Bet365
        if not target_bookie:
            target_bookie = next((b for b in all_bookmakers if "Bet365" in b['name']), None)
            
        # 3. Se não houver nenhum, usa o primeiro da lista
        if not target_bookie:
            target_bookie = all_bookmakers[0]

        print(f"✅ Odds obtidas de: {target_bookie['name']}")
        
        bets = target_bookie['bets']
        
        # 1. Mercado 1X2 (ID = 1)
        match_winner = next((b for b in bets if b['id'] == 1), None)
        odds_1x2 = {'h': 0, 'd': 0, 'a': 0}
        
        if match_winner:
            vals = match_winner['values']
            odds_1x2['h'] = next((v['odd'] for v in vals if v['value'] == 'Home'), 0)
            odds_1x2['d'] = next((v['odd'] for v in vals if v['value'] == 'Draw'), 0)
            odds_1x2['a'] = next((v['odd'] for v in vals if v['value'] == 'Away'), 0)

        # 2. Hipótese Dupla (ID = 12)
        double_chance = next((b for b in bets if b['id'] == 12), None)
        odds_dc = {'1x': 0, '12': 0, 'x2': 0}

        if double_chance:
            vals_dc = double_chance['values']
            odds_dc['1x'] = next((v['odd'] for v in vals_dc if v['value'] == 'Home/Draw'), 0)
            odds_dc['12'] = next((v['odd'] for v in vals_dc if v['value'] == 'Home/Away'), 0)
            odds_dc['x2'] = next((v['odd'] for v in vals_dc if v['value'] == 'Draw/Away'), 0)
            
        return jsonify({
            'odd_h': odds_1x2['h'], 'odd_d': odds_1x2['d'], 'odd_a': odds_1x2['a'],
            'odd_1x': odds_dc['1x'], 'odd_12': odds_dc['12'], 'odd_x2': odds_dc['x2']
        })

    except Exception as e:
        print(f"Erro Odds: {e}")
        return jsonify({"error": "Erro servidor"})


# --- ROTA 3: PREVISÃO (COM LÓGICA "LAST 5") ---
@app.route('/api/predict', methods=['POST'])
def predict():
    global model_multi, xgb_goals_h, xgb_goals_a, df_ready
    
    try:
        if model_multi is None: return jsonify({"error": "Modelos offline"}), 500
        data = request.get_json()
        
        # 1. Dados Básicos
        home, away = data.get('home_team'), data.get('away_team')
        div = data.get('division', 'E0')
        date_str = data.get('date')
        
        # --- 2. PREENCHIMENTO DE FEATURES INTELIGENTE (Last 5 Logic) ---
        input_data = {}
        
        # Garante que o histórico está ordenado por data para pegar o último jogo
        if 'Date' in df_ready.columns:
            history = df_ready.sort_values('Date')
        else:
            history = df_ready
            
        # Detecta nomes das colunas de equipas (pode variar dependendo do treino)
        h_col = 'Home' if 'Home' in df_ready.columns else 'HomeTeam'
        a_col = 'Away' if 'Away' in df_ready.columns else 'AwayTeam'
        has_team_cols = (h_col in df_ready.columns) and (a_col in df_ready.columns)

        for f in features:
            val = None
            
            # Se for uma feature dependente da equipa (ex: Home_Goals_Last_5)
            if has_team_cols:
                # Descobre qual a equipa alvo desta feature
                target_team = None
                if f.startswith(('Home', 'H_', 'h_')): target_team = home
                elif f.startswith(('Away', 'A_', 'a_')): target_team = away
                
                if target_team:
                    # Filtra os jogos dessa equipa no histórico
                    team_rows = history[(history[h_col] == target_team) | (history[a_col] == target_team)]
                    
                    if not team_rows.empty:
                        # Pega na ÚLTIMA linha conhecida (o estado mais atual da equipa)
                        last_row = team_rows.iloc[-1]
                        
                        # Verifica se a equipa jogou em Casa ou Fora nesse último jogo
                        was_home_in_last = (last_row[h_col] == target_team)
                        
                        # Lógica de Mapeamento:
                        # Se queremos a feature "Home_XG" para o Benfica (que joga em Casa hoje),
                        # mas no último jogo o Benfica foi Fora, temos de ler a coluna "Away_XG" desse jogo anterior.
                        col_to_read = f
                        if not was_home_in_last:
                            # Inverte o nome da coluna para ler o dado correto do histórico
                            if 'Home' in f: col_to_read = f.replace('Home', 'Away')
                            elif 'H_' in f: col_to_read = f.replace('H_', 'A_')
                            elif 'Away' in f: col_to_read = f.replace('Away', 'Home')
                            elif 'A_' in f: col_to_read = f.replace('A_', 'H_')
                        
                        if col_to_read in last_row:
                            val = last_row[col_to_read]

            # Fallback: Se não encontrou valor específico (equipa nova ou feature genérica), usa a média
            if val is None:
                val = df_ready[f].mean() if not df_ready.empty and f in df_ready else 0
            
            input_data[f] = val

        # ELO Ratings (Sempre Frescos)
        match_date = pd.to_datetime(date_str)
        if not df_ready.empty:
            h_elo = current_elos.get(home, 1500)
            a_elo = current_elos.get(away, 1500)
            input_data['HomeElo'] = h_elo; input_data['AwayElo'] = a_elo
            input_data['EloDiff'] = h_elo - a_elo

        # Odds
        try:
            odd_h = float(data.get('odd_h', 0))
            odd_d = float(data.get('odd_d', 0))
            odd_a = float(data.get('odd_a', 0))
            odd_1x = float(data.get('odd_1x')) if data.get('odd_1x') else None
            odd_12 = float(data.get('odd_12')) if data.get('odd_12') else None
            odd_x2 = float(data.get('odd_x2')) if data.get('odd_x2') else None
        except: return jsonify({"error": "Odds inválidas"}), 400

        if odd_h > 0: input_data['Imp_Home'] = 1/odd_h
        if odd_d > 0: input_data['Imp_Draw'] = 1/odd_d
        if odd_a > 0: input_data['Imp_Away'] = 1/odd_a

        try: input_data['Div_Code'] = le_div.transform([div])[0]
        except: input_data['Div_Code'] = 0

        # 3. Execução do Modelo
        X = pd.DataFrame([input_data])[features]
        exp_h = float(xgb_goals_h.predict(X)[0])
        exp_a = float(xgb_goals_a.predict(X)[0])
        probs = model_multi.predict_proba(X)[0]
        prob_a, prob_d, prob_h = float(probs[0]), float(probs[1]), float(probs[2])
        
        try: conf_shield = float(model_shield.predict_proba(X)[0][1])
        except: conf_shield = prob_h + prob_d

        best_score, best_prob = "0-0", -1
        for h in range(6):
            for a in range(6):
                p = poisson.pmf(h, exp_h) * poisson.pmf(a, exp_a)
                if p > best_prob: best_prob = p; best_score = f"{h} - {a}"

        # 4. Scanner & Análise
        opportunities = [] 

        def add(name, odd, prob):
            if not odd or odd <= 1: return
            ev = (prob * odd) - 1
            implied_prob = 1/odd
            
            if ev > 0.05: status = "💎 MUITO VALOR!"
            elif ev > 0: status = "✅ VALOR"
            elif ev > -0.05: status = "😐 JUSTO"
            else: status = "❌ FRACO"
            
            opportunities.append({
                "name": name, 
                "odd": odd, 
                "odd_prob": f"{implied_prob:.1%}", 
                "prob_raw": prob,
                "prob_txt": f"{prob:.1%}", 
                "fair_odd": f"{1/prob:.2f}" if prob > 0 else "99",
                "ev": ev,
                "status": status
            })

        # ORDEM FIXA
        add(f"Vitoria {home}", odd_h, prob_h)
        add("Empate", odd_d, prob_d)
        add(f"Vitoria {away}", odd_a, prob_a)
        
        p1x = ((prob_h + prob_d) + conf_shield)/2
        if odd_1x: add(f"DC 1X ({home} ou Empate)", odd_1x, p1x)
        if odd_12: add(f"DC 12 ({home} ou {away})", odd_12, prob_h + prob_a)
        if odd_x2: add(f"DC X2 ({away} ou Empate)", odd_x2, prob_a + prob_d)

        sorted_by_ev = sorted(opportunities, key=lambda x: x['ev'], reverse=True)
        rational = sorted_by_ev[0] if sorted_by_ev else None
        
        safe_list = sorted(opportunities, key=lambda x: x['prob_raw'], reverse=True)
        safe = safe_list[0] if safe_list else None

        return jsonify({
            'home': home, 'away': away,
            'xg': {'home': f"{exp_h:.2f}", 'away': f"{exp_a:.2f}"},
            'score': {'placar': best_score, 'prob': f"{best_prob:.1%}"},
            'scanner': opportunities,
            'rational': rational,
            'safe': safe
        })

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
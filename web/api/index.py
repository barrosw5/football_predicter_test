from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import joblib
import os
import requests
import pandas as pd
import numpy as np
from scipy.stats import poisson
import traceback
import time
from datetime import datetime

# --- CONFIGURAÇÃO (RENDER) ---
app = Flask(__name__, static_folder='../public', static_url_path='')
CORS(app)

# --- NOVA API KEY (The Odds API) ---
# No Render, cria a variável: API_KEY_ODDS
# Se testares no PC, substitui a string abaixo pela tua chave nova
API_KEY = os.getenv("API_KEY_ODDS", "COLA_AQUI_A_TUA_CHAVE_SE_TESTARES_LOCAL")

# --- CONFIGURAÇÃO DAS LIGAS (The Odds API Keys) ---
# Estas chaves dizem à API quais as ligas que queremos ver
SUPPORTED_LEAGUES = [
    'soccer_portugal_primeira_liga',
    'soccer_epl',             # Premier League
    'soccer_spain_la_liga',   # La Liga
    'soccer_germany_bundesliga',
    'soccer_italy_serie_a',
    'soccer_france_ligue_one',
    'soccer_uefa_champs_league',
    'soccer_uefa_europa_league'
]

# Mapa para traduzir os nomes da API nova para os códigos do teu modelo .pkl
MODEL_DIV_MAP = {
    'soccer_portugal_primeira_liga': 'P1',
    'soccer_epl': 'E0',
    'soccer_spain_la_liga': 'SP1',
    'soccer_germany_bundesliga': 'D1',
    'soccer_italy_serie_a': 'I1',
    'soccer_france_ligue_one': 'F1',
    'soccer_uefa_champs_league': 'CL',
    'soccer_uefa_europa_league': 'CL' 
}

# --- CACHE (Otimização) ---
# Cache unificada: guarda o JSON completo da API por liga
# Como a API dá jogos para vários dias, guardamos por 6 horas para poupar pedidos
api_cache = {} 
CACHE_DURATION = 21600 # 6 Horas

# --- CARREGAMENTO DO MODELO ---
model_path = os.path.join(os.path.dirname(__file__), 'football_brain.pkl')
model_multi = None
xgb_goals_h = None
df_ready = pd.DataFrame()

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
        print(f"❌ ERRO CRÍTICO MODELO: {e}")

# --- HELPER: Normalizar Nomes ---
# A nova API usa nomes em Inglês (ex: "Sporting Lisbon"), o modelo quer "Sporting CP"
def normalize_name(name):
    name_map = {
        'Sporting Lisbon': 'Sporting CP', 'Sporting': 'Sporting CP',
        'Benfica': 'Benfica', 'FC Porto': 'Porto',
        'Manchester United': 'Man United', 'Manchester City': 'Man City',
        'Paris Saint Germain': 'Paris SG', 'PSG': 'Paris SG',
        'Bayern Munich': 'Bayern Munich', 'Leverkusen': 'Bayer Leverkusen',
        'Inter Milan': 'Inter', 'AC Milan': 'Milan',
        'Atletico Madrid': 'Ath Madrid', 'Real Madrid': 'Real Madrid'
    }
    return name_map.get(name, name)

# --- ROTAS ---

@app.route('/')
def serve_index():
    return send_from_directory(app.static_folder, 'index.html')

@app.route('/api/fixtures', methods=['POST'])
def get_fixtures():
    try:
        data = request.get_json()
        target_date_str = data.get('date') # Ex: "2025-12-12"
        
        all_matches = []
        current_time = time.time()

        # Iterar sobre as ligas configuradas
        for sport_key in SUPPORTED_LEAGUES:
            
            # 1. Verificar Cache para esta liga
            league_data = []
            if sport_key in api_cache and (current_time - api_cache[sport_key]['ts'] < CACHE_DURATION):
                league_data = api_cache[sport_key]['data']
            else:
                # 2. Se não houver cache, pede à API (Gasta 1 crédito)
                print(f"📡 API CALL: Atualizando {sport_key}...")
                url = f"https://api.the-odds-api.com/v4/sports/{sport_key}/odds"
                params = {
                    'apiKey': API_KEY,
                    'regions': 'eu', # Odds Europeias
                    'markets': 'h2h', # Apenas vencedor
                    'oddsFormat': 'decimal'
                }
                res = requests.get(url, params=params)
                if res.status_code == 200:
                    league_data = res.json()
                    # Guarda na cache
                    api_cache[sport_key] = {'data': league_data, 'ts': current_time}
                else:
                    print(f"❌ Erro API {sport_key}: {res.status_code}")

            # 3. Processar jogos e filtrar pela DATA pedida
            for game in league_data:
                # A API devolve datas assim: "2025-12-12T20:00:00Z"
                # Convertemos para YYYY-MM-DD
                game_date = game['commence_time'].split('T')[0]
                
                if game_date == target_date_str:
                    # Extrair Odds (se houver) para mostrar logo na cache depois
                    odds_h, odds_d, odds_a = 0, 0, 0
                    bookmakers = game.get('bookmakers', [])
                    if bookmakers:
                        # Tenta usar a primeira casa disponível
                        markets = bookmakers[0].get('markets', [])
                        if markets:
                            outcomes = markets[0].get('outcomes', [])
                            for out in outcomes:
                                if out['name'] == game['home_team']: odds_h = out['price']
                                elif out['name'] == game['away_team']: odds_a = out['price']
                                elif out['name'] == 'Draw': odds_d = out['price']

                    # Constrói o objeto igual ao que o Frontend espera
                    all_matches.append({
                        'id': game['id'], # ID único da nova API
                        'home_team': normalize_name(game['home_team']),
                        'away_team': normalize_name(game['away_team']),
                        'division': MODEL_DIV_MAP.get(sport_key, 'E0'),
                        'league_name': game['sport_title'],
                        'country': 'World',
                        'match_time': game['commence_time'].split('T')[1][:5],
                        'homeTeam': normalize_name(game['home_team']),
                        'awayTeam': normalize_name(game['away_team']),
                        'status_short': 'NS' # Assumimos Not Started
                    })

        all_matches.sort(key=lambda x: x['match_time'])
        print(f"✅ Jogos encontrados para {target_date_str}: {len(all_matches)}")
        return jsonify(all_matches)

    except Exception as e:
        traceback.print_exc()
        return jsonify([])

@app.route('/api/odds', methods=['POST'])
def get_odds():
    # Com esta nova API, as odds já foram carregadas no 'get_fixtures' e estão na cache!
    # Só precisamos de ir buscá-las à memória.
    try:
        data = request.get_json()
        fid = data.get('fixture_id')
        
        # Procura o jogo em TODAS as caches de ligas
        found_game = None
        for sport_key in api_cache:
            for game in api_cache[sport_key]['data']:
                if game['id'] == fid:
                    found_game = game
                    break
            if found_game: break
            
        if not found_game:
            return jsonify({"error": "Odds não encontradas (Tente recarregar)"})

        # Extrair Odds do jogo encontrado
        odds = {'h': 0, 'd': 0, 'a': 0}
        bookmakers = found_game.get('bookmakers', [])
        
        if bookmakers:
            # Tenta encontrar uma casa conhecida ou usa a primeira
            target_bookie = next((b for b in bookmakers if 'Betclic' in b['title']), None)
            if not target_bookie: target_bookie = bookmakers[0]
            
            markets = target_bookie.get('markets', [])
            for m in markets:
                if m['key'] == 'h2h':
                    for out in m['outcomes']:
                        if out['name'] == found_game['home_team']: odds['h'] = out['price']
                        elif out['name'] == found_game['away_team']: odds['a'] = out['price']
                        elif out['name'] == 'Draw': odds['d'] = out['price']

        return jsonify({
            'odd_h': odds['h'], 'odd_d': odds['d'], 'odd_a': odds['a'],
            'odd_1x': 0, 'odd_12': 0, 'odd_x2': 0 # API Grátis não dá DC, fica a 0 (manual)
        })

    except Exception as e:
        print(f"Erro Odds: {e}")
        return jsonify({"error": "Erro servidor"})

@app.route('/api/predict', methods=['POST'])
def predict():
    global model_multi, xgb_goals_h, xgb_goals_a, df_ready
    
    try:
        if model_multi is None: return jsonify({"error": "Modelos offline"}), 500
        data = request.get_json()
        
        home, away = data.get('home_team'), data.get('away_team')
        div = data.get('division', 'E0')
        date_str = data.get('date')
        
        input_data = {}
        
        # Função auxiliar "Last 5"
        def get_latest_stats(team_name):
            if 'Team' not in df_ready.columns: 
                return {f: df_ready[f].mean() if f in df_ready.columns else 0 for f in features}
            team_history = df_ready[df_ready['Team'] == team_name]
            if team_history.empty: 
                return {f: df_ready[f].mean() if f in df_ready.columns else 0 for f in features}
            return team_history.iloc[-1].to_dict()

        home_stats = get_latest_stats(home)
        away_stats = get_latest_stats(away)

        for f in features:
            if f in home_stats: input_data[f] = home_stats[f]
            else: input_data[f] = df_ready[f].mean() if not df_ready.empty and f in df_ready else 0

        match_date = pd.to_datetime(date_str)
        if not df_ready.empty:
            h_elo = current_elos.get(home, 1500)
            a_elo = current_elos.get(away, 1500)
            input_data['HomeElo'] = h_elo; input_data['AwayElo'] = a_elo
            input_data['EloDiff'] = h_elo - a_elo

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

        X = pd.DataFrame([input_data])[features]
        exp_h = float(xgb_goals_h.predict(X)[0])
        exp_a = float(xgb_goals_a.predict(X)[0])
        probs = model_multi.predict_proba(X)[0]
        prob_a, prob_d, prob_h = float(probs[0]), float(probs[1]), float(probs[2])
        
        try: conf_shield = float(model_shield.predict_proba(X)[0][1])
        except: conf_shield = prob_h + prob_d

        score_matrix = []
        best_score, best_prob = "0-0", -1
        
        for h in range(6):
            row = []
            for a in range(6):
                p = poisson.pmf(h, exp_h) * poisson.pmf(a, exp_a)
                row.append(p)
                if p > best_prob: 
                    best_prob = p; best_score = f"{h} - {a}"
            score_matrix.append(row)

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
                "name": name, "odd": odd, "odd_prob": f"{implied_prob:.1%}", 
                "prob_raw": prob, "prob_txt": f"{prob:.1%}", 
                "fair_odd": f"{1/prob:.2f}" if prob > 0 else "99", "ev": ev, "status": status
            })

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
            'matrix': score_matrix, 
            'scanner': opportunities,
            'rational': rational,
            'safe': safe
        })

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
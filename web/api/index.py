from flask import Flask, request, jsonify
from flask_cors import CORS
import joblib
import os
import requests
import traceback

app = Flask(__name__)
# Permite CORS para qualquer origem durante desenvolvimento
CORS(app)

# --- CONFIGURAÇÃO ---
# ⚠️ IMPORTANTE: Substitui pela tua chave REAL se esta não funcionar.
# A chave no erro anterior parecia inválida ou expirada.
API_KEY = "81f8d50f4cac1f4ac373794f18440676" 

# Mapeamento (IDs da API-Football -> Teus códigos internos)
LEAGUE_MAP = {
    39: 'E0', 78: 'D1', 140: 'SP1', 61: 'F1', 135: 'I1',
    40: 'E1', 79: 'D2', 141: 'SP2', 62: 'F2', 136: 'I2',
    94: 'P1', 88: 'N1', 144: 'B1', 203: 'T1', 197: 'G1', 179: 'SC0',
    2: 'CL' # Champions League (Exemplo, verifica o ID correto)
}

# --- CARREGAR MODELO ---
model_path = os.path.join(os.path.dirname(__file__), 'football_brain.pkl')
if os.path.exists(model_path):
    try:
        artifacts = joblib.load(model_path)
        print("✅ Modelo carregado com sucesso.")
    except Exception as e:
        print(f"⚠️ Erro ao carregar modelo: {e}")
        artifacts = None
else:
    print("⚠️ Modo Simulação Ativo (Modelo não encontrado).")
    artifacts = None

# --- ROTA 1: OBTER JOGOS ---
@app.route('/api/fixtures', methods=['POST'])
def get_fixtures():
    try:
        data = request.json
        date_str = data.get('date')
        
        if not date_str:
            return jsonify({'error': 'Data não fornecida'}), 400

        print(f"\n--- A procurar jogos para: {date_str} ---")

        url = "https://v3.football.api-sports.io/fixtures"
        querystring = {"date": date_str, "timezone": "Europe/Lisbon"}
        
        # Tenta os dois formatos comuns de header para garantir compatibilidade
        headers = {
            "x-rapidapi-key": API_KEY,
            "x-rapidapi-host": "v3.football.api-sports.io"
        }
        # Se tiveres uma conta direta na api-sports (não via RapidAPI), usa antes:
        # headers = {"x-apisports-key": API_KEY}

        response = requests.get(url, headers=headers, params=querystring)
        
        if response.status_code != 200:
            print(f"❌ Erro HTTP API: {response.status_code}")
            return jsonify({'error': f"Erro na API Externa: {response.status_code}"}), 500
            
        api_data = response.json()
        
        # Verificar erros de permissão/quota
        if isinstance(api_data, dict) and api_data.get('errors'):
            # A API por vezes devolve 'errors' como lista ou dict
            print(f"❌ Erro de Lógica API: {api_data['errors']}")
            return jsonify({'error': str(api_data['errors'])}), 403

        raw_list = api_data.get('response', [])
        print(f"✅ Jogos brutos encontrados: {len(raw_list)}")

        matches = []
        for item in raw_list:
            lid = item['league']['id']
            # Filtra apenas se a liga estiver no nosso mapa
            if lid in LEAGUE_MAP:
                matches.append({
                    "id": item['fixture']['id'],
                    "league": item['league']['name'],
                    "div_code": LEAGUE_MAP[lid],
                    "home": item['teams']['home']['name'],
                    "away": item['teams']['away']['name'],
                    # Tenta ir buscar odds reais se existirem, senão zeros
                    "odds": {"h": 0, "d": 0, "a": 0} 
                })

        print(f"✅ Jogos compatíveis filtrados: {len(matches)}")
        return jsonify(matches)

    except Exception as e:
        print("❌ ERRO NO SERVIDOR PYTHON:")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

# --- ROTA 2: PREVISÃO ---
@app.route('/api/predict', methods=['POST']) # Mudei de /api/index para /api/predict (mais claro)
def predict():
    try:
        data = request.json
        print(f"🔮 A prever jogo: {data.get('home_team')} vs {data.get('away_team')}")

        # SIMULAÇÃO (Substituir pela lógica real do teu modelo)
        return jsonify({
            'xg': {'home': '1.85', 'away': '0.92'},
            'most_likely_score': f"{data.get('home_team')} Vence",
            'market_scanner': [
                {'name': 'Vitória Casa', 'odd': data.get('odd_h', '1.5'), 'prob': '65%', 'ev': 0.15, 'status': '💎 Valor'},
                {'name': 'Ambas Marcam', 'odd': '1.90', 'prob': '45%', 'ev': -0.05, 'status': '❌ Fraco'}
            ]
        })
    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(port=5000, debug=True)
import pandas as pd
import numpy as np
import requests
import re
import os
import codecs
import json
import kagglehub
import time
import random
import cloudscraper # <--- O SEGREDO ESTÁ AQUI

# --- CONFIGURAÇÃO DE CONSTANTES ---
DATA_FILE = 'europe_football_full.csv'
XG_FILE = 'europe_football_xg.csv'
MARKET_VALUE_FILE = 'market_values.csv'

def clean_team_name(name):
    name_map = {
        # --- PORTUGAL ---
        'Sp Braga': 'Braga', 'SC Braga': 'Braga',
        'Sp Lisbon': 'Sporting CP', 'Sporting Lisbon': 'Sporting CP', 'Sporting': 'Sporting CP',
        'Benfica': 'Benfica', 'SL Benfica': 'Benfica',
        'FC Porto': 'Porto', 'Porto': 'Porto',
        'Vitoria Guimaraes': 'Vitoria SC', 'Vitoria de Guimaraes': 'Vitoria SC',
        'Rio Ave': 'Rio Ave', 'Rio Ave FC': 'Rio Ave',
        'Estoril': 'Estoril', 'GD Estoril Praia': 'Estoril',
        'Arouca': 'Arouca', 'FC Arouca': 'Arouca',
        'Famalicao': 'Famalicao', 'FC Famalicão': 'Famalicao',
        'Boavista': 'Boavista', 'Boavista FC': 'Boavista',
        'Gil Vicente': 'Gil Vicente', 'Gil Vicente FC': 'Gil Vicente',
        'Estrela': 'Estrela Amadora', 'Estrela Amadora': 'Estrela Amadora',
        'Casa Pia': 'Casa Pia', 'Casa Pia AC': 'Casa Pia',
        'Moreirense': 'Moreirense', 'Moreirense FC': 'Moreirense',
        'Farense': 'Farense', 'SC Farense': 'Farense',
        'Nacional': 'Nacional', 'CD Nacional': 'Nacional',
        'Santa Clara': 'Santa Clara', 'CD Santa Clara': 'Santa Clara',
        'AVS': 'AVS', 'AVS FS': 'AVS',

        # --- HOLANDA ---
        'PSV Eindhoven': 'PSV', 'PSV': 'PSV',
        'Ajax': 'Ajax', 'Ajax Amsterdam': 'Ajax',
        'Feyenoord': 'Feyenoord', 'Feyenoord Rotterdam': 'Feyenoord',
        'AZ Alkmaar': 'AZ Alkmaar', 'AZ': 'AZ Alkmaar',
        'Twente': 'Twente', 'FC Twente': 'Twente',

        # --- BÉLGICA ---
        'Club Brugge': 'Club Brugge', 'Brugge': 'Club Brugge',
        'Anderlecht': 'Anderlecht', 'RSC Anderlecht': 'Anderlecht',
        'Gent': 'Gent', 'KAA Gent': 'Gent',
        'Genk': 'Genk', 'KRC Genk': 'Genk',
        'Union St Gilloise': 'Union SG', 'Royale Union Saint-Gilloise': 'Union SG',

        # --- TURQUIA ---
        'Galatasaray': 'Galatasaray',
        'Fenerbahce': 'Fenerbahce', 'Fenerbahçe': 'Fenerbahce',
        'Besiktas': 'Besiktas', 'Beşiktaş': 'Besiktas',
        'Trabzonspor': 'Trabzonspor',
        'Basaksehir': 'Basaksehir',

        # --- GRÉCIA ---
        'Olympiakos': 'Olympiacos', 'Olympiacos': 'Olympiacos',
        'PAOK': 'PAOK', 'PAOK Salonika': 'PAOK',
        'Panathinaikos': 'Panathinaikos',
        'AEK': 'AEK Athens', 'AEK Athens': 'AEK Athens',

        # --- ESCÓCIA ---
        'Celtic': 'Celtic',
        'Rangers': 'Rangers',

        # --- INGLATERRA ---
        'Manchester United': 'Man United', 'Manchester City': 'Man City',
        'Newcastle United': 'Newcastle', 'West Ham United': 'West Ham', 
        'Wolverhampton Wanderers': 'Wolves', 'Brighton': 'Brighton',
        'Leicester City': 'Leicester', 'Leeds United': 'Leeds',
        'Tottenham Hotspur': 'Tottenham', 'Nottingham Forest': "Nott'm Forest", 
        'Sheffield United': 'Sheffield United', 'Luton': 'Luton', 
        'Brentford': 'Brentford', 'Bournemouth': 'Bournemouth',
        'West Brom': 'West Bromwich Albion', 'West Bromwich': 'West Bromwich Albion',
        'QPR': 'Queens Park Rangers', 'Blackburn': 'Blackburn Rovers',
        'Coventry': 'Coventry City', 'Stoke': 'Stoke City', 'Hull': 'Hull City',
        
        # --- ALEMANHA ---
        'Bayern Munich': 'Bayern Munich', 'Bayern München': 'Bayern Munich',
        'Borussia Dortmund': 'Borussia Dortmund', 'Dortmund': 'Borussia Dortmund',
        'Bayer Leverkusen': 'Bayer Leverkusen', 'Leverkusen': 'Bayer Leverkusen',
        'RB Leipzig': 'RB Leipzig', 'Leipzig': 'RB Leipzig',
        'Borussia Monchengladbach': 'Borussia M.Gladbach', "M'gladbach": 'Borussia M.Gladbach',
        'Eintracht Frankfurt': 'Eintracht Frankfurt', 'Frankfurt': 'Eintracht Frankfurt',
        'Wolfsburg': 'Wolfsburg', 'VfL Wolfsburg': 'Wolfsburg',
        'Mainz 05': 'Mainz 05', 'Mainz': 'Mainz 05',
        'Stuttgart': 'VfB Stuttgart', 'VfB Stuttgart': 'VfB Stuttgart',
        'Freiburg': 'Freiburg', 'SC Freiburg': 'Freiburg',
        'Union Berlin': 'Union Berlin', 'FC Union Berlin': 'Union Berlin',
        'Bochum': 'VfL Bochum', 'VfL Bochum': 'VfL Bochum',
        'Koln': 'FC Koln', 'FC Köln': 'FC Koln',
        'Hertha': 'Hertha Berlin', 'Hertha BSC': 'Hertha Berlin',
        'Schalke 04': 'Schalke 04', 'Schalke': 'Schalke 04',
        'Hamburg': 'Hamburger SV', 'Hamburger': 'Hamburger SV',
        'Hannover': 'Hannover 96', 'Kaiserslautern': 'FC Kaiserslautern',
        'Nurnberg': 'FC Nurnberg', 'Dusseldorf': 'Fortuna Dusseldorf',

        # --- ESPANHA ---
        'Ath Bilbao': 'Athletic Club', 'Athletic Bilbao': 'Athletic Club',
        'Atl Madrid': 'Atletico Madrid', 'Atletico': 'Atletico Madrid',
        'Barcelona': 'Barcelona', 'Real Madrid': 'Real Madrid',
        'Betis': 'Real Betis', 'Real Betis': 'Real Betis',
        'Celta': 'Celta Vigo', 'Celta Vigo': 'Celta Vigo',
        'Espanol': 'Espanyol', 'Espanyol': 'Espanyol',
        'Sociedad': 'Real Sociedad', 'Real Sociedad': 'Real Sociedad',
        'Valencia': 'Valencia', 'Valladolid': 'Real Valladolid', 
        'Villarreal': 'Villarreal', 'Girona': 'Girona',
        'Alaves': 'Alaves', 'Cadiz': 'Cadiz', 'Almeria': 'Almeria',
        'Sp Gijon': 'Sporting Gijon', 'Zaragoza': 'Real Zaragoza',
        'Levante': 'Levante', 'Tenerife': 'Tenerife', 'Eibar': 'Eibar',

        # --- FRANÇA ---
        'Paris SG': 'Paris Saint Germain', 'PSG': 'Paris Saint Germain',
        'Marseille': 'Marseille', 'Lyon': 'Lyon', 'Monaco': 'Monaco',
        'Lille': 'Lille', 'Nice': 'Nice', 'Rennes': 'Rennes',
        'Lens': 'Lens', 'Montpellier': 'Montpellier', 'Nantes': 'Nantes',
        'Reims': 'Reims', 'Strasbourg': 'Strasbourg', 'Toulouse': 'Toulouse',
        'Brest': 'Brest', 'Lorient': 'Lorient', 'Metz': 'Metz',
        'St Etienne': 'Saint-Etienne', 'Saint-Etienne': 'Saint-Etienne',
        'Bordeaux': 'Girondins Bordeaux', 'Auxerre': 'Auxerre',
        'Ajaccio': 'AC Ajaccio', 'Troyes': 'Troyes',

        # --- ITÁLIA ---
        'Inter': 'Inter', 'Internazionale': 'Inter',
        'Milan': 'AC Milan', 'Juventus': 'Juventus', 'Roma': 'Roma', 
        'Lazio': 'Lazio', 'Napoli': 'Napoli', 'Atalanta': 'Atalanta', 
        'Fiorentina': 'Fiorentina', 'Torino': 'Torino', 'Udinese': 'Udinese',
        'Bologna': 'Bologna', 'Verona': 'Verona', 'Hellas Verona': 'Verona',
        'Empoli': 'Empoli', 'Lecce': 'Lecce', 'Sassuolo': 'Sassuolo',
        'Monza': 'Monza', 'Genoa': 'Genoa', 'Salernitana': 'Salernitana',
        'Parma': 'Parma', 'Sampdoria': 'Sampdoria', 'Cremonese': 'Cremonese',
        'Venezia': 'Venezia', 'Palermo': 'Palermo', 'Bari': 'Bari',

        # --- OUTROS (CHAMPIONS LEAGUE) ---
        'Shakhtar Donetsk': 'Shakhtar Donetsk',
        'Salzburg': 'RB Salzburg', 'Red Bull Salzburg': 'RB Salzburg'
    }
    return name_map.get(name, name)

def scrape_understat_season(year, league_name):
    # Proteção: Understat não tem dados futuros
    if year > 2024: return pd.DataFrame()

    print(f"🕷️ A recolher xG ({league_name}) de {year}/{year+1}...")
    url = f"https://understat.com/league/{league_name}/{year}"
    
    # 1. Usar CloudScraper em vez de Requests (Passa pelo Cloudflare)
    scraper = cloudscraper.create_scraper()
    
    # Pausa aleatória para parecer humano
    time.sleep(random.uniform(2, 5)) 

    try:
        response = scraper.get(url)
        
        if response.status_code != 200: 
            print(f"   ❌ Erro HTTP: {response.status_code}")
            return pd.DataFrame()
        
        # 2. Regex Universal: Procura qualquer JSON.parse, não importa as aspas
        # Captura o conteúdo dentro de: JSON.parse('...') ou JSON.parse("...")
        candidates = re.findall(r"JSON\.parse\s*\(\s*(['\"])(.*?)\1\s*\)", response.text, re.DOTALL)
        
        data = None
        
        # Procura nos candidatos encontrados
        for quote, content in candidates:
            try:
                # Descodificar caracteres hexadecimais (\x5B -> [)
                json_string = codecs.decode(content, 'unicode_escape')
                temp_data = json.loads(json_string)
                
                # Validação: É a lista de jogos?
                # Deve ser uma lista e o primeiro item deve ter 'h' (home), 'a' (away) e 'goals'
                if isinstance(temp_data, list) and len(temp_data) > 0:
                    if all(k in temp_data[0] for k in ['h', 'a', 'goals', 'xG']):
                        data = temp_data
                        # print(f"   ✅ Encontrado! ({len(data)} jogos)") # Debug opcional
                        break
            except:
                continue
        
        # Fallback: Se não encontrou com JSON.parse, tenta procurar 'var datesData = [...]' direto
        if not data:
            direct_match = re.search(r"var\s+datesData\s*=\s*(\[.*?\]);", response.text, re.DOTALL)
            if direct_match:
                try:
                    data = json.loads(direct_match.group(1))
                except: pass

        if not data:
            print(f"   ⚠️ Proteção ativa ou dados não encontrados para {league_name}.")
            return pd.DataFrame()
            
        matches = []
        for m in data:
            if m.get('isResult', False):
                matches.append({
                    'Date': m['datetime'][:10],
                    'HomeTeam': m['h']['title'],
                    'AwayTeam': m['a']['title'],
                    'FTHG': int(m['goals']['h']),
                    'FTAG': int(m['goals']['a']),
                    'Home_xG': float(m['xG']['h']),
                    'Away_xG': float(m['xG']['a']),
                    'League': league_name
                })
        return pd.DataFrame(matches)
        
    except Exception as e:
        print(f"   ❌ Erro técnico: {e}")
        return pd.DataFrame()

def get_main_data(start, end):
    if os.path.exists(DATA_FILE):
        print(f"📂 Carregando dados locais: {DATA_FILE}")
        df = pd.read_csv(DATA_FILE)
        df['Date'] = pd.to_datetime(df['Date'], dayfirst=True, errors='coerce')
        return df
    
    print("🌐 A descarregar dados das Ligas (Football-Data)...")
    dfs = []
    base_url = "https://www.football-data.co.uk/mmz4281/{}/{}.csv"
    
    # Lista Completa de Ligas
    divisions = [
        'E0', 'D1', 'SP1', 'F1', 'I1', # Top 5
        'E1', 'D2', 'SP2', 'F2', 'I2', # 2ªs Divisões
        'P1', 'N1', 'B1', 'T1', 'G1', 'SC0' # Outras
    ] 
    
    for year in range(start, end + 1):
        season = f"{str(year)[-2:]}{str(year+1)[-2:]}"
        for div in divisions:
            try:
                time.sleep(0.5)
                url = base_url.format(season, div)
                df = pd.read_csv(url)
                df['Div'] = div
                df['Date'] = pd.to_datetime(df['Date'], dayfirst=True, errors='coerce')
                dfs.append(df)
            except: pass
        
    full_df = pd.concat(dfs, ignore_index=True).dropna(subset=['Date', 'FTR'])
    
    # Limpeza de Nomes
    full_df['HomeTeam'] = full_df['HomeTeam'].apply(clean_team_name)
    full_df['AwayTeam'] = full_df['AwayTeam'].apply(clean_team_name)

    full_df.to_csv(DATA_FILE, index=False)
    print(f"✅ Dados das Ligas (1ª e 2ª Divisões) guardados em: {DATA_FILE}")
    
    return full_df.sort_values('Date').reset_index(drop=True)

def prepare_market_values():
    if os.path.exists(MARKET_VALUE_FILE):
        print(f"📂 Carregando dados locais: {MARKET_VALUE_FILE}")
        return

    print("⬇️ A baixar dados do Transfermarkt via Kagglehub...")
    try:
        path = kagglehub.dataset_download("davidcariboo/player-scores")
        
        valuations = pd.read_csv(os.path.join(path, "player_valuations.csv"))
        clubs = pd.read_csv(os.path.join(path, "clubs.csv"))
        
        valuations['date'] = pd.to_datetime(valuations['date'])
        valuations['Season'] = valuations['date'].apply(lambda x: x.year if x.month > 7 else x.year - 1)
        
        val_merged = valuations.merge(clubs[['club_id', 'name']], left_on='current_club_id', right_on='club_id', how='left')
        squad_values = val_merged.groupby(['name', 'Season'])['market_value_in_eur'].sum().reset_index()
        squad_values.rename(columns={'name': 'Team', 'market_value_in_eur': 'Value'}, inplace=True)
        squad_values['Value'] = squad_values['Value'] / 1_000_000
        
        squad_values['Team'] = squad_values['Team'].apply(clean_team_name)
        
        squad_values.to_csv(MARKET_VALUE_FILE, index=False)
        print(f"✅ 'market_values.csv' criado com sucesso!")
        
    except Exception as e:
        print(f"⚠️ Erro ao processar dados do Kaggle: {e}")

def get_understat_data(start_year, end_year):
    if os.path.exists(XG_FILE):
        print(f"📂 Carregando dados Understat locais: {XG_FILE}")
        df = pd.read_csv(XG_FILE)
        df['Date'] = pd.to_datetime(df['Date']) 
        return df

    print("🌐 A iniciar scraping Understat (com CloudScraper)...")
    dfs = []
    
    for y in range(start_year, end_year + 1):
        dfs.append(scrape_understat_season(y, 'EPL'))
        dfs.append(scrape_understat_season(y, 'Bundesliga'))
        dfs.append(scrape_understat_season(y, 'La_liga'))
        dfs.append(scrape_understat_season(y, 'Ligue_1'))
        dfs.append(scrape_understat_season(y, 'Serie_A'))
        dfs.append(scrape_understat_season(y, 'Champions_League'))
    
    valid_dfs = [d for d in dfs if not d.empty]
    
    if valid_dfs:
        df_final = pd.concat(valid_dfs, ignore_index=True)
        df_final['HomeTeam'] = df_final['HomeTeam'].apply(clean_team_name)
        df_final['AwayTeam'] = df_final['AwayTeam'].apply(clean_team_name)
        
        # GRAVAR LOCALMENTE
        df_final.to_csv(XG_FILE, index=False)
        print(f"✅ Dados Understat guardados.")
        return df_final
    else:
        return pd.DataFrame()
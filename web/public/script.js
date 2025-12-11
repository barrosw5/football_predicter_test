document.addEventListener('DOMContentLoaded', () => {
    const API_BASE = "http://127.0.0.1:5000";
    
    // Elementos do DOM
    const dateInput = document.getElementById('match-date');
    const matchSelect = document.getElementById('quick-match');
    const form = document.getElementById('prediction-form');
    const resultArea = document.getElementById('result-area');
    const dateHidden = document.getElementById('match-date-hidden');
    
    // Caixas de Texto das Equipas (ReadOnly)
    const homeInput = document.getElementById('input-home');
    const awayInput = document.getElementById('input-away');

    // --- CAIXAS DAS ODDS ---
    const getInput = (name) => document.querySelector(`input[name="${name}"]`) || document.getElementById(name);

    const inputH = getInput('odd_h');
    const inputD = getInput('odd_d');
    const inputA = getInput('odd_a');
    const input1X = getInput('odd_1x');
    const input12 = getInput('odd_12');
    const inputX2 = getInput('odd_x2');

    const allOddInputs = [inputH, inputD, inputA, input1X, input12, inputX2];

    // Define a data de hoje
    const today = new Date().toISOString().split('T')[0];
    dateInput.value = today;
    dateHidden.value = today;

    // --- FUNÇÃO DE FORMATAÇÃO FORÇADA (2 CASAS) ---
    const formatOdd = (val) => {
        if (!val || val == 0 || val === "N/A") return "";
        return Number(val).toFixed(2);
    };

    // --- 1. PREENCHIMENTO AUTOMÁTICO ---
    matchSelect.addEventListener('change', async () => {
        const selectedValue = matchSelect.value;
        
        if (selectedValue) {
            try {
                const matchData = JSON.parse(selectedValue);
                
                // Preenche Equipas
                if(homeInput) homeInput.value = matchData.home_team || matchData.homeTeam;
                if(awayInput) awayInput.value = matchData.away_team || matchData.awayTeam;
                
                // Feedback "A carregar..."
                allOddInputs.forEach(el => { 
                    if(el) { el.value = ""; el.placeholder = "A carregar..."; } 
                });

                // Pedir Odds
                if (matchData.id) {
                    console.log(`📡 A pedir odds ID: ${matchData.id}`);
                    
                    const res = await fetch(`${API_BASE}/api/odds`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ fixture_id: matchData.id })
                    });
                    
                    const oddsData = await res.json();
                    
                    if (oddsData.error) {
                        console.warn("Aviso API:", oddsData.error);
                        allOddInputs.forEach(el => { if(el) el.placeholder = "N/A"; });
                    } else {
                        // APLICA A FORMATAÇÃO AQUI
                        if(inputH) inputH.value = formatOdd(oddsData.odd_h);
                        if(inputD) inputD.value = formatOdd(oddsData.odd_d);
                        if(inputA) inputA.value = formatOdd(oddsData.odd_a);
                        
                        if(input1X) input1X.value = formatOdd(oddsData.odd_1x);
                        if(input12) input12.value = formatOdd(oddsData.odd_12);
                        if(inputX2) inputX2.value = formatOdd(oddsData.odd_x2);
                        
                        allOddInputs.forEach(el => el.placeholder = "1.00");
                    }
                }
                
            } catch (e) {
                console.error("Erro:", e);
                allOddInputs.forEach(el => el.placeholder = "Erro");
            }
        } else {
            // Limpar
            if(homeInput) homeInput.value = "";
            if(awayInput) awayInput.value = "";
            allOddInputs.forEach(el => { if(el) { el.value = ""; el.placeholder = "1.00"; } });
        }
    });

    // --- 2. FETCH JOGOS ---
    async function fetchFixtures(date) {
        matchSelect.disabled = true;
        matchSelect.innerHTML = '<option>⏳ A carregar jogos...</option>';
        if(homeInput) homeInput.value = "";
        if(awayInput) awayInput.value = "";

        try {
            const res = await fetch(`${API_BASE}/api/fixtures`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ date: date })
            });
            const matches = await res.json();
            matchSelect.innerHTML = '<option value="">-- Seleciona um Jogo --</option>';

            if (matches.length === 0) {
                matchSelect.innerHTML = '<option value="">⚠️ Sem jogos suportados hoje</option>';
            } else {
                const groups = {};
                matches.forEach(m => {
                    const league = `${m.league_name} (${m.country})`;
                    if (!groups[league]) groups[league] = [];
                    groups[league].push(m);
                });
                for (const [leagueName, games] of Object.entries(groups)) {
                    const group = document.createElement('optgroup');
                    group.label = leagueName;
                    games.forEach(m => {
                        const opt = document.createElement('option');
                        opt.value = JSON.stringify(m);
                        const statusIcon = (m.status_short === 'FT') ? '🏁' : '⏰';
                        opt.textContent = `${m.match_time} ${statusIcon} ${m.home_team} vs ${m.away_team}`;
                        group.appendChild(opt);
                    });
                    matchSelect.appendChild(group);
                }
            }
        } catch (e) {
            console.error(e);
            matchSelect.innerHTML = '<option>❌ Erro de conexão</option>';
        } finally {
            matchSelect.disabled = false;
        }
    }

    dateInput.addEventListener('change', (e) => {
        dateHidden.value = e.target.value;
        fetchFixtures(e.target.value);
    });

    // --- 3. SUBMETER PREVISÃO ---
    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        if (!matchSelect.value) return alert("Seleciona um jogo!");

        const mData = JSON.parse(matchSelect.value);
        
        const payload = {
            date: dateHidden.value,
            home_team: mData.home_team || mData.homeTeam,
            away_team: mData.away_team || mData.awayTeam,
            division: mData.division || 'E0',
            odd_h: parseFloat(inputH.value) || 0, 
            odd_d: parseFloat(inputD.value) || 0, 
            odd_a: parseFloat(inputA.value) || 0,
            odd_1x: parseFloat(input1X.value) || 0, 
            odd_12: parseFloat(input12.value) || 0, 
            odd_x2: parseFloat(inputX2.value) || 0
        };

        resultArea.innerHTML = '<div class="loading">🔮 A consultar os astros do futebol...</div>';

        try {
            const res = await fetch(`${API_BASE}/api/predict`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            const data = await res.json();
            if (data.error) throw new Error(data.error);

            // RENDER HTML
            const formatEV = (val) => (val * 100).toFixed(1) + "%";

            // GERAÇÃO DO SCANNER COM NOVO LAYOUT
            let scannerHTML = data.scanner.map(s => {
                let badgeClass = s.status.includes('MUITO') ? "badge-gem" : 
                                 s.status.includes('VALOR') ? "badge-good" : 
                                 s.status.includes('JUSTO') ? "badge-fair" : "badge-bad";
                let icon = s.status.includes('MUITO') ? "💎 " : 
                           s.status.includes('VALOR') ? "✅ " : 
                           s.status.includes('JUSTO') ? "😐 " : "❌ ";

                // AQUI ESTÁ A MUDANÇA VISUAL PEDIDA:
                return `<div class="scanner-item">
                    <div class="market-name">${s.name}</div>
                    
                    <div class="data-col">
                        <span style="font-weight:bold;">@${s.odd.toFixed(2)}</span>
                        <span style="font-size:0.85em; color:#94a3b8; margin-left:4px;">(${s.odd_prob})</span>
                    </div>
                    
                    <div class="data-col">
                        <span style="font-weight:bold; color:var(--primary)">@${s.fair_odd}</span>
                        <span style="font-size:0.85em; color:#94a3b8; margin-left:4px;">(${s.prob_txt})</span>
                    </div>
                    
                    <div class="status-badge ${badgeClass}">${icon}${s.status.replace(/.* /, '')}</div>
                </div>`;
            }).join('');

            // CABEÇALHO ATUALIZADO
            resultArea.innerHTML = `
                <h3>${data.home} vs ${data.away}</h3>
                <div style="text-align:center; font-size:1.5em; margin:10px 0;">${data.score.placar}</div>
                
                <div class="scanner-container">
                    <div class="scanner-header">
                        <div>Mercado</div>
                        <div style="text-align:center;">Casa de Apostas</div>
                        <div style="text-align:center;">IA (Modelo)</div>
                        <div style="text-align:center;">Valor</div>
                    </div>
                    ${scannerHTML}
                </div>

                <div style="margin-top:25px;">
                    ${data.rational ? `
                    <div style="background: rgba(16, 185, 129, 0.1); padding: 15px; border-left: 4px solid #10b981; margin-bottom: 10px; border-radius: 4px;">
                        <h4 style="margin:0; color: #10b981;">🏆 Racional: ${data.rational.name}</h4>
                        <div>EV: +${formatEV(data.rational.ev)}</div>
                    </div>` : ''}
                    
                    ${data.safe ? `
                    <div style="background: rgba(59, 130, 246, 0.1); padding: 15px; border-left: 4px solid #3b82f6; border-radius: 4px;">
                        <h4 style="margin:0; color: #3b82f6;">🛡️ Seguro: ${data.safe.name}</h4>
                        <div>Confiança: ${data.safe.prob_txt}</div>
                    </div>` : ''}
                </div>
            `;

        } catch (err) {
            resultArea.innerHTML = `<div class="error-box">❌ ${err.message}</div>`;
        }
    });

    fetchFixtures(dateInput.value);
});
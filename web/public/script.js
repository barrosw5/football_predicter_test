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
    // Função auxiliar para encontrar o input pelo Name ou ID
    const getInput = (name) => document.querySelector(`input[name="${name}"]`) || document.getElementById(name);

    const inputH = getInput('odd_h');
    const inputD = getInput('odd_d');
    const inputA = getInput('odd_a');
    const input1X = getInput('odd_1x');
    const input12 = getInput('odd_12');
    const inputX2 = getInput('odd_x2');

    // Array com todos os inputs para facilitar limpar/preencher em loop
    const allOddInputs = [inputH, inputD, inputA, input1X, input12, inputX2];

    // Define a data de hoje
    const today = new Date().toISOString().split('T')[0];
    dateInput.value = today;
    dateHidden.value = today;

    // --- FUNÇÃO AUXILIAR: FORMATAR ODDS (2 Casas Decimais) ---
    const formatOdd = (val) => {
        if (!val || val === 0 || val === "0" || val === "N/A") return "";
        // Converte para float e fixa em 2 casas (ex: 1.5 -> "1.50")
        return parseFloat(val).toFixed(2);
    };

    // --- 1. PREENCHIMENTO AUTOMÁTICO (EQUIPAS + ODDS) ---
    matchSelect.addEventListener('change', async () => {
        const selectedValue = matchSelect.value;
        
        if (selectedValue) {
            try {
                const matchData = JSON.parse(selectedValue);
                
                // A. Preenche Nomes das Equipas
                if(homeInput) homeInput.value = matchData.home_team || matchData.homeTeam;
                if(awayInput) awayInput.value = matchData.away_team || matchData.awayTeam;
                
                // B. Feedback Visual: Coloca placeholder "A carregar..." e limpa valor
                allOddInputs.forEach(el => { 
                    if(el) { 
                        el.value = ""; 
                        el.placeholder = "A carregar..."; 
                    } 
                });

                // C. Vai buscar as ODDS à API
                if (matchData.id) {
                    console.log(`📡 A pedir odds para o jogo ID: ${matchData.id}`);
                    
                    const res = await fetch(`${API_BASE}/api/odds`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ fixture_id: matchData.id })
                    });
                    
                    const oddsData = await res.json();
                    console.log("📦 Odds recebidas:", oddsData);
                    
                    if (oddsData.error) {
                        console.warn("Aviso API:", oddsData.error);
                        // Se der erro (ex: limite atingido), põe "N/A" no placeholder
                        allOddInputs.forEach(el => { if(el) el.placeholder = "N/A"; });
                    } else {
                        // D. Preenche os valores com formatação (1.50)
                        if(inputH) inputH.value = formatOdd(oddsData.odd_h);
                        if(inputD) inputD.value = formatOdd(oddsData.odd_d);
                        if(inputA) inputA.value = formatOdd(oddsData.odd_a);
                        
                        if(input1X) input1X.value = formatOdd(oddsData.odd_1x);
                        if(input12) input12.value = formatOdd(oddsData.odd_12);
                        if(inputX2) inputX2.value = formatOdd(oddsData.odd_x2);
                        
                        // Restaura o placeholder normal
                        allOddInputs.forEach(el => el.placeholder = "1.00");
                    }
                }
                
            } catch (e) {
                console.error("Erro ao processar dados:", e);
                allOddInputs.forEach(el => el.placeholder = "Erro");
            }
        } else {
            // Limpa tudo se desmarcar o jogo
            if(homeInput) homeInput.value = "";
            if(awayInput) awayInput.value = "";
            allOddInputs.forEach(el => { if(el) { el.value = ""; el.placeholder = "1.00"; } });
        }
    });

    // --- 2. FETCH JOGOS DA API ---
    async function fetchFixtures(date) {
        matchSelect.disabled = true;
        matchSelect.innerHTML = '<option>⏳ A carregar jogos...</option>';
        
        // Limpar inputs de equipas
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
                // Agrupar por Liga
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
                        const home = m.home_team || m.homeTeam;
                        const away = m.away_team || m.awayTeam;
                        opt.textContent = `${m.match_time} ${statusIcon} ${home} vs ${away}`;
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

    // Atualizar lista quando muda a data
    dateInput.addEventListener('change', (e) => {
        dateHidden.value = e.target.value;
        fetchFixtures(e.target.value);
    });

    // --- 3. SUBMETER PREVISÃO ---
    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        if (!matchSelect.value) return alert("Seleciona um jogo!");

        const mData = JSON.parse(matchSelect.value);
        
        // Usamos os valores diretos dos inputs (inputH.value)
        // Isto permite que a previsão funcione mesmo que tenhas escrito as odds à mão
        const payload = {
            date: dateHidden.value,
            home_team: mData.home_team || mData.homeTeam,
            away_team: mData.away_team || mData.awayTeam,
            division: mData.division || 'E0',
            odd_h: inputH ? inputH.value : 0, 
            odd_d: inputD ? inputD.value : 0, 
            odd_a: inputA ? inputA.value : 0,
            odd_1x: input1X ? input1X.value : 0, 
            odd_12: input12 ? input12.value : 0, 
            odd_x2: inputX2 ? inputX2.value : 0
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

            // --- RENDER HTML ---
            const formatEV = (val) => (val * 100).toFixed(1) + "%";

            let scannerHTML = data.scanner.map(s => {
                let badgeClass = s.status.includes('MUITO') ? "badge-gem" : 
                                 s.status.includes('VALOR') ? "badge-good" : 
                                 s.status.includes('JUSTO') ? "badge-fair" : "badge-bad";
                let icon = s.status.includes('MUITO') ? "💎 " : 
                           s.status.includes('VALOR') ? "✅ " : 
                           s.status.includes('JUSTO') ? "😐 " : "❌ ";

                return `<div class="scanner-item">
                    <div class="market-name">${s.name}</div>
                    <div class="data-col"><span class="data-val">@${s.odd.toFixed(2)}</span></div>
                    <div class="data-col"><span class="data-val" style="color:var(--primary)">@${s.fair_odd}</span></div>
                    <div class="status-badge ${badgeClass}">${icon}${s.status.replace(/.* /, '')}</div>
                </div>`;
            }).join('');

            let rationalHTML = data.rational ? `
                <div style="background: rgba(16, 185, 129, 0.1); padding: 15px; border-left: 4px solid #10b981; margin-bottom: 10px; border-radius: 4px;">
                    <h4 style="margin:0; color: #10b981;">🏆 Racional: ${data.rational.name}</h4>
                    <div>EV: +${formatEV(data.rational.ev)}</div>
                </div>` : '';
            
            let safeHTML = data.safe ? `
                <div style="background: rgba(59, 130, 246, 0.1); padding: 15px; border-left: 4px solid #3b82f6; border-radius: 4px;">
                    <h4 style="margin:0; color: #3b82f6;">🛡️ Seguro: ${data.safe.name}</h4>
                    <div>Confiança: ${data.safe.prob_txt}</div>
                </div>` : '';

            resultArea.innerHTML = `
                <h3>${data.home} vs ${data.away}</h3>
                <div style="text-align:center; font-size:1.5em; margin:10px 0;">${data.score.placar}</div>
                <div class="scanner-container">${scannerHTML}</div>
                ${rationalHTML}
                ${safeHTML}
            `;

        } catch (err) {
            resultArea.innerHTML = `<div class="error-box">❌ ${err.message}</div>`;
        }
    });

    // Iniciar a busca de jogos ao carregar a página
    fetchFixtures(dateInput.value);
});
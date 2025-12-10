document.addEventListener('DOMContentLoaded', () => {
    const API_BASE = "http://127.0.0.1:5000";
    
    // Elementos
    const dateInput = document.getElementById('match-date');
    const matchSelect = document.getElementById('quick-match');
    const form = document.getElementById('prediction-form');
    const resultArea = document.getElementById('result-area');
    const sysStatus = document.getElementById('sys-status');

    // Inicializar data com hoje
    dateInput.value = new Date().toISOString().split('T')[0];

    // Função para obter jogos da API Python
    async function fetchFixtures(date) {
        matchSelect.disabled = true;
        matchSelect.innerHTML = '<option>⏳ A carregar jogos...</option>';
        matchSelect.style.opacity = "0.5";

        try {
            const res = await fetch(`${API_BASE}/api/fixtures`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ date: date })
            });

            if (!res.ok) {
                const errData = await res.json();
                throw new Error(errData.error || 'Erro no servidor');
            }

            const matches = await res.json();

            if (matches.length === 0) {
                matchSelect.innerHTML = '<option>⚠️ Sem jogos suportados hoje</option>';
                return;
            }

            // Limpar e preencher
            matchSelect.innerHTML = '<option value="">👇 Seleciona um jogo da lista</option>';
            matchSelect.disabled = false;
            matchSelect.style.opacity = "1";

            // Agrupar por Liga
            const grouped = matches.reduce((acc, curr) => {
                (acc[curr.league] = acc[curr.league] || []).push(curr);
                return acc;
            }, {});

            for (const [league, games] of Object.entries(grouped)) {
                const group = document.createElement('optgroup');
                group.label = league;
                games.forEach(g => {
                    const opt = document.createElement('option');
                    opt.value = JSON.stringify(g);
                    opt.textContent = `${g.home} vs ${g.away}`;
                    group.appendChild(opt);
                });
                matchSelect.appendChild(group);
            }
            
            sysStatus.style.color = "#4ade80"; // Verde se conectou bem

        } catch (error) {
            console.error(error);
            matchSelect.innerHTML = `<option>❌ Erro: ${error.message}</option>`;
            sysStatus.style.color = "#f87171"; // Vermelho
        }
    }

    // Event Listener: Mudança de Data
    dateInput.addEventListener('change', (e) => fetchFixtures(e.target.value));

    // Event Listener: Selecionar Jogo
    matchSelect.addEventListener('change', (e) => {
        if (!e.target.value) return;
        const game = JSON.parse(e.target.value);

        // Preencher formulário
        document.getElementById('home_team').value = game.home;
        document.getElementById('away_team').value = game.away;
        document.getElementById('division').value = game.div_code;
        
        // Simular odds se vierem a 0 (apenas para UX, idealmente a API trazia odds)
        document.getElementById('odd_h').value = game.odds.h || 1.90;
        document.getElementById('odd_d').value = game.odds.d || 3.20;
        document.getElementById('odd_a').value = game.odds.a || 2.80;

        // Animação de foco
        form.classList.add('highlight-pulse');
        setTimeout(() => form.classList.remove('highlight-pulse'), 500);
    });

    // Event Listener: Submeter Previsão
    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        // UI de Loading
        resultArea.innerHTML = `
            <div class="loading-card">
                <div class="spinner"></div>
                <p>A inteligência artificial está a analisar o jogo...</p>
            </div>
        `;

        const formData = new FormData(form);
        const data = Object.fromEntries(formData.entries());

        try {
            const res = await fetch(`${API_BASE}/api/predict`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });

            const prediction = await res.json();

            if (prediction.error) throw new Error(prediction.error);

            // Renderizar Resultado
            renderResult(prediction, data);

        } catch (error) {
            resultArea.innerHTML = `<div class="error-card">❌ Erro na previsão: ${error.message}</div>`;
        }
    });

    // Função de Renderização HTML
    function renderResult(pred, inputs) {
        resultArea.innerHTML = `
            <div class="result-card fade-in">
                <div class="result-header">
                    <h3>${inputs.home_team} vs ${inputs.away_team}</h3>
                    <div class="badge-league">${inputs.division}</div>
                </div>
                
                <div class="main-prediction">
                    <span class="label">Previsão Principal</span>
                    <div class="prediction-value">${pred.most_likely_score}</div>
                </div>

                <div class="stats-grid">
                    <div class="stat-item">
                        <span>xG Casa</span>
                        <strong>${pred.xg.home}</strong>
                    </div>
                    <div class="stat-item">
                        <span>xG Fora</span>
                        <strong>${pred.xg.away}</strong>
                    </div>
                </div>

                <div class="scanner-list">
                    <h4>Scanner de Mercado</h4>
                    ${pred.market_scanner.map(s => `
                        <div class="scanner-row ${s.status.includes('Valor') ? 'positive' : ''}">
                            <div class="market-name">${s.name}</div>
                            <div class="market-data">
                                <span class="tag-odd">@${s.odd}</span>
                                <span class="tag-prob">${s.prob}</span>
                            </div>
                            <div class="market-status">${s.status}</div>
                        </div>
                    `).join('')}
                </div>
            </div>
        `;
    }

    // Carregar inicial
    fetchFixtures(dateInput.value);
});
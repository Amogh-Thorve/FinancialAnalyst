document.addEventListener('DOMContentLoaded', () => {
    // Element References
    const groqKeyInput = document.getElementById('groq-key');
    const avKeyInput = document.getElementById('av-key');
    const initBtn = document.getElementById('init-btn');
    const resetBtn = document.getElementById('reset-btn');
    const exportBtn = document.getElementById('export-btn');

    const uploadBtnTrigger = null; // Removed
    const fileInput = null;
    const fileInfo = document.getElementById('file-info');
    const fileNameDisplay = document.getElementById('filename');

    const tickerInput = document.getElementById('ticker-input');
    const analyzeBtn = document.getElementById('analyze-btn');
    const welcomeTickerInput = document.getElementById('welcome-ticker-input');
    const welcomeAnalyzeBtn = document.getElementById('welcome-analyze-btn');

    const userInput = document.getElementById('user-input');
    const sendBtn = document.getElementById('send-btn');
    const chatMessages = document.getElementById('chat-messages');

    const statusDot = document.getElementById('status-dot');
    const statusText = document.getElementById('status-text');

    const heroCard = document.getElementById('hero-card');
    const toggleHeroBtn = document.getElementById('toggle-hero');

    // const pdfUpload = document.getElementById('pdf-upload'); // Removed where used
    // const uploadBtn = document.getElementById('upload-btn'); // Removed where used

    // Tab Elements
    const tabBtns = document.querySelectorAll('.tab-btn');
    const tabPanels = document.querySelectorAll('.tab-panel');
    const kpiHeader = document.getElementById('kpi-header');
    const exportBtnTop = document.getElementById('export-pdf-top');

    // Sidebar Collapse
    const sidebar = document.getElementById('sidebar');
    const collapseBtn = document.getElementById('collapse-sidebar');
    const appContainer = document.querySelector('.app-container');

    if (collapseBtn) {
        collapseBtn.addEventListener('click', () => {
            sidebar.classList.toggle('collapsed');
            if (appContainer) appContainer.classList.toggle('sidebar-collapsed');
        });
    }

    const expandBtnFloating = document.getElementById('expand-sidebar-floating');
    if (expandBtnFloating) {
        expandBtnFloating.addEventListener('click', () => {
            sidebar.classList.remove('collapsed');
        });
    }

    // Floating Chatbot
    const chatbotPanel = document.getElementById('chatbot-panel');
    const chatbotToggleBtn = document.getElementById('chatbot-toggle-btn');
    const closeChatBtn = document.getElementById('close-chat');
    const notificationDot = chatbotToggleBtn?.querySelector('.notification-dot');

    if (chatbotToggleBtn) {
        chatbotToggleBtn.addEventListener('click', () => {
            chatbotPanel.classList.toggle('hidden');
            if (notificationDot) notificationDot.classList.add('hidden');
        });
    }

    if (closeChatBtn) {
        closeChatBtn.addEventListener('click', () => {
            chatbotPanel.classList.add('hidden');
        });
    }

    // Hero Card Action Buttons (will be set up after upload)
    let fullAnalysisBtn, viewForecastBtn;

    // State
    let currentMetrics = null;
    let isInitialized = false;
    let isProcessing = false;

    // Chart Instances (Global scope for destruction)
    let revenueChart2024 = null;
    let revenueChart2023 = null;
    let radarBenchmarkChart = null;
    let sentimentTrendChart = null;
    let riskRadarMainChart = null;
    let stabilityChart = null;

    // Helper: Dynamic Color based on Score (0-100)
    function getColorByScore(score) {
        score = parseFloat(score);
        if (isNaN(score)) return '#94a3b8'; // Neutral
        if (score <= 40) return '#10b981'; // Low Risk / Success
        if (score <= 70) return '#f59e0b'; // Medium Risk / Warning
        return '#ef4444'; // High Risk / Danger
    }

    // Helper: Format Percentage
    function formatPercent(val, addPlus = false) {
        if (val === null || val === undefined || val === 'N/A') return 'N/A';
        let num = parseFloat(String(val).replace(/[^0-9.-]/g, ''));
        if (isNaN(num)) return String(val);
        // If it looks like a decimal (e.g., 0.13), convert to percentage
        if (Math.abs(num) < 2 && !String(val).includes('%')) num *= 100;
        const sign = addPlus && num > 0 ? '+' : '';
        return `${sign}${num.toFixed(1)}%`;
    }

    // Helper: Format Large Numbers (Market Cap)
    function formatLargeNumber(val) {
        if (val === null || val === undefined || val === 'N/A') return 'N/A';
        let num = parseFloat(String(val).replace(/[^0-9.-]/g, ''));
        if (isNaN(num)) return String(val);
        if (num >= 1e12) return `${(num / 1e12).toFixed(2)}T`;
        if (num >= 1e9) return `${(num / 1e9).toFixed(2)}B`;
        if (num >= 1e6) return `${(num / 1e6).toFixed(2)}M`;
        return num.toLocaleString();
    }

    // Helper: Calculate Deterministic Risk Scores
    // This ensures consistent outputs regardless of LLM variability
    function calculateRiskScores(metrics) {
        const cr = parseFloat(metrics.current_ratio) || 0;
        const beta = parseFloat(metrics.beta) || 1;
        const de = parseFloat(metrics.debt_equity) || 0;
        const own = parseFloat(metrics.ownership) || 0;

        // Liquidity Risk: Lower current ratio = higher risk
        // Target: 1.5 (100% health), 0 = 100% risk
        const liquidityRisk = Math.max(0, Math.min(100, 100 - (cr / 1.5) * 100));

        // Market Risk: Higher beta = higher risk
        // Target: Beta of 1 = 50 risk, Beta of 2 = 100 risk
        const marketRisk = Math.max(0, Math.min(100, beta * 50));

        // Credit Risk: Higher D/E = higher risk
        // Target: D/E of 3 = 100% risk
        const creditRisk = Math.max(0, Math.min(100, (de / 3) * 100));

        // Governance Risk: Lower insider ownership = higher risk
        // Target: 20% ownership = 0 risk
        const governanceRisk = Math.max(0, Math.min(100, 100 - (own / 20) * 100));

        return {
            liquidity_risk: Math.round(liquidityRisk),
            market_risk: Math.round(marketRisk),
            credit_risk: Math.round(creditRisk),
            governance_risk: Math.round(governanceRisk)
        };
    }

    // Auto-fill Keys & Auto-Init
    (async () => {
        try {
            console.log("Fetching API keys from /api/env...");
            const res = await fetch('/api/env');
            if (res.ok) {
                const data = await res.json();
                console.log("API keys fetched:", data);

                let hasGroq = false;
                let hasAV = false;

                if (data.groq_api_key && groqKeyInput) {
                    groqKeyInput.value = data.groq_api_key;
                    hasGroq = true;
                }
                if (data.alpha_vantage_key && avKeyInput) {
                    avKeyInput.value = data.alpha_vantage_key;
                    hasAV = true;
                }

                if (hasGroq) {
                    // console.log("API Keys pre-filled from environment.");
                    // Auto-initialize if keys are available
                    await initializeAgent(data.groq_api_key, data.alpha_vantage_key || "demo");
                }
            }
        } catch (e) {
            console.error('Env fetch/auto-init failed', e);
        }
    })();

    // Tab Switching Logic
    tabBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            const targetTab = btn.getAttribute('data-tab');

            tabBtns.forEach(b => b.classList.remove('active'));
            tabPanels.forEach(p => p.classList.remove('active'));

            btn.classList.add('active');
            const targetPanel = document.getElementById(`tab-${targetTab}`);
            if (targetPanel) {
                targetPanel.classList.add('active');
                // Redraw charts if switching to risks or financials to ensure proper dimensions
                if (targetTab === 'risks' && currentMetrics) {
                    populateRisks(currentMetrics);
                } else if (targetTab === 'financials' && currentMetrics) {
                    populateFinancials(currentMetrics);
                }
            }
        });
    });

    if (exportBtnTop) {
        exportBtnTop.addEventListener('click', () => {
            // Reuse existing export functionality if it exists, or trigger a simple PDF download
            if (exportBtn) exportBtn.click();
            else alert("Please upload a report first to export the analysis.");
        });
    }

    async function initializeAgent(groqKey, avKey) {
        try {
            const res = await fetch('/api/init', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ groq_api_key: groqKey, alpha_vantage_key: avKey })
            });

            if (!res.ok) throw new Error((await res.json()).detail);

            isInitialized = true;
            statusDot.classList.add('connected');
            statusText.textContent = 'CONNECTED';

        } catch (e) {
            console.error('Initialization failed:', e);
            addMessage('Agent initialization failed: ' + e.message, 'system');
        }
    }

    // Helper: Add Message
    function addMessage(content, type) {
        const msgDiv = document.createElement('div');
        msgDiv.className = `message ${type}`;
        const contentDiv = document.createElement('div');
        contentDiv.className = 'content';

        if (type === 'ai' && typeof content === 'object') {
            contentDiv.innerHTML = marked.parse(content.text || '');
            if (content.chart_data) {
                const chartContainer = document.createElement('div');
                chartContainer.style.marginTop = '1rem';
                chartContainer.style.height = '400px';
                const canvas = document.createElement('canvas');
                chartContainer.appendChild(canvas);
                contentDiv.appendChild(chartContainer);
                const ctx = canvas.getContext('2d');
                new Chart(ctx, {
                    type: 'line',
                    data: {
                        labels: content.chart_data.dates,
                        datasets: [{
                            label: `${content.chart_data.ticker} Price`,
                            data: content.chart_data.prices,
                            borderColor: '#5b68f5',
                            borderWidth: 2,
                            tension: 0.4,
                            fill: false
                        }]
                    },
                    options: { responsive: true, maintainAspectRatio: false }
                });

                if (content.chart_data.metrics) {
                    const m = content.chart_data.metrics;
                    const metricsDiv = document.createElement('div');
                    metricsDiv.style.display = 'flex';
                    metricsDiv.style.gap = '1rem';
                    metricsDiv.style.marginTop = '1rem';
                    metricsDiv.innerHTML = `
                        <div style="background:rgba(30,41,59,0.5); padding:0.5rem 1rem; border-radius:0.5rem;">
                            <span style="color:#94a3b8;">PE Ratio:</span>
                            <span style="color:#f8fafc; font-weight:600;"> ${m.pe_ratio || 'N/A'}</span>
                        </div>
                        <div style="background:rgba(30,41,59,0.5); padding:0.5rem 1rem; border-radius:0.5rem;">
                            <span style="color:#94a3b8;">Market Cap:</span>
                            <span style="color:#f8fafc; font-weight:600;"> ${m.market_cap || 'N/A'}</span>
                        </div>
                        <div style="background:rgba(30,41,59,0.5); padding:0.5rem 1rem; border-radius:0.5rem;">
                            <span style="color:#94a3b8;">Div Yield:</span>
                            <span style="color:#f8fafc; font-weight:600;"> ${m.dividend_yield || 'N/A'}</span>
                        </div>
                    `;
                    contentDiv.appendChild(metricsDiv);
                }
            }
        } else {
            contentDiv.innerHTML = type === 'ai' ? marked.parse(content) : content;
        }

        msgDiv.appendChild(contentDiv);
        if (type === 'ai' && chatbotPanel && chatbotPanel.classList.contains('hidden')) {
            if (notificationDot) notificationDot.classList.remove('hidden');
        }

        chatMessages.appendChild(msgDiv);
        chatMessages.scrollTop = chatMessages.scrollHeight;
        return msgDiv;
    }

    // Helper: Populate Dashboard
    function populateDashboard(metrics) {
        if (!metrics) return;

        try {
            // Use backend-provided risk scores directly (from Alpha Vantage API)
            currentMetrics = metrics;

            const welcomeOverlay = document.getElementById('dashboard-welcome');
            if (welcomeOverlay) welcomeOverlay.classList.add('hidden');

            kpiHeader.classList.remove('hidden');
            document.getElementById('dashboard-content').classList.remove('hidden');

            // New KPI Header (Golden Corner)
            const ticker = metrics.ticker ? ` (${metrics.ticker})` : '';
            document.getElementById('kpi-company-name').textContent = (metrics.company_name || 'Company Name');
            document.getElementById('kpi-ticker-tag').textContent = metrics.ticker || 'TICKER';

            const revGrowth = formatPercent(metrics.revenue_growth, true);
            const isRevPositive = String(revGrowth).startsWith('+');
            const kpiRev = document.getElementById('kpi-rev-growth');
            kpiRev.textContent = revGrowth;
            kpiRev.className = 'kpi-value ' + (isRevPositive ? 'positive' : 'negative');

            const profitMargin = formatPercent(metrics.profit_margin);
            const profitVal = parseFloat(String(profitMargin).replace('%', ''));
            const isProfitHealthy = !isNaN(profitVal) && profitVal >= 0;
            const kpiProfit = document.getElementById('kpi-profit-margin');
            kpiProfit.textContent = profitMargin;
            kpiProfit.className = 'kpi-value ' + (isProfitHealthy ? 'positive' : 'negative');

            const riskScore = parseFloat(metrics.risk_score) || 0;
            const riskColor = getColorByScore(riskScore * 10); // risk_score is 0-10, scale to 100
            document.getElementById('kpi-risk-score').textContent = riskScore.toFixed(1);
            document.getElementById('kpi-risk-score').style.color = riskColor;
            document.getElementById('kpi-risk-fill').style.width = `${(riskScore / 10) * 100}%`;
            document.getElementById('kpi-risk-fill').style.backgroundColor = riskColor;

            document.getElementById('summary-fy').textContent = metrics.fiscal_year || 'FY 2024';
            document.getElementById('summary-desc').textContent = metrics.company_description || 'Analysis extracting detailed insights from the report...';

            // Draw Charts (Protected)
            try { drawRevenueDeepDive(metrics); } catch (e) { console.error("Revenue Chart Error:", e); addMessage("Revenue Chart Error: " + e.message, 'system'); }
            try { drawSentimentTrend(metrics.sentiment_trend, metrics.sentiment?.sentiment_score); } catch (e) { console.error("Sentiment Chart Error:", e); }

            // Draw Mini Sparklines in KPI Header
            // Consistent Color Logic: Match the text color (Green if Positive/Healthy)
            drawMiniSparkline('kpi-rev-sparkline', metrics.history?.revenue || [10, 12, 11, 14, 15], isRevPositive ? '#10b981' : '#ef4444');
            drawMiniSparkline('kpi-profit-sparkline', metrics.history?.net_income || [5, 4, 6, 5, 8], isProfitHealthy ? '#10b981' : '#ef4444');

            // Populate Financials Tab
            try { populateFinancials(metrics); } catch (e) { console.error("Financials Error:", e); }

            // Populate Risks Tab
            try { populateRisks(metrics); } catch (e) { console.error("Risks Error:", e); }

            // Populate News Tab
            populateNews(metrics.sentiment?.news);

            // Legacy/Backup Logic (Hidden but kept for some background logic if needed)
            const revIcon = document.getElementById('revenue-icon');
            if (revIcon) revIcon.className = String(revGrowth).startsWith('+') ? 'fa-solid fa-arrow-trend-up' : 'fa-solid fa-arrow-trend-down';

            const profitEl = document.getElementById('hero-profit');
            if (profitEl) {
                profitEl.textContent = profitMargin;
                profitEl.className = 'value ' + (isProfitHealthy ? 'positive' : 'negative');
            }

            const profitIcon = document.getElementById('profit-icon');
            if (profitIcon) profitIcon.className = metrics.profit_trend === 'positive' ? 'fa-solid fa-arrow-trend-up' : 'fa-solid fa-arrow-trend-down';

            document.getElementById('hero-vol1').textContent = metrics.volatility || 'Low';

            const heroRisk = document.getElementById('hero-risk');
            if (heroRisk) {
                heroRisk.textContent = riskScore.toFixed(1);
                heroRisk.style.color = riskColor;
            }

            const riskMeterFill = document.getElementById('risk-meter-fill');
            if (riskMeterFill) {
                riskMeterFill.style.width = `${(riskScore / 10) * 100}%`;
                riskMeterFill.style.background = riskColor;
            }


            const flagsPanel = document.getElementById('red-flags-panel');
            if (metrics.red_flags && metrics.red_flags.length > 0) {
                flagsPanel.innerHTML = metrics.red_flags.map(flag =>
                    `<div class="flag-item"><i class="fa-solid fa-triangle-exclamation"></i> <span>${flag}</span></div>`
                ).join('');
            } else {
                flagsPanel.innerHTML = '<div class="flag-item"><i class="fa-solid fa-check-circle"></i> <span>No critical issues</span></div>';
            }

            // Show Live Insights Card
            const liveInsightsCard = document.querySelector('.live-insights-card');
            if (liveInsightsCard) {
                liveInsightsCard.classList.remove('hidden');
            }




            // Live Insights - Net Margin
            const liveMarginEl = document.getElementById('live-margin');
            if (liveMarginEl) {
                liveMarginEl.textContent = profitMargin;
                liveMarginEl.className = 'metric-value ' + (isProfitHealthy ? 'positive' : 'negative');
            }

            const liveMarginChange = document.getElementById('live-margin-change');
            if (liveMarginChange && metrics.previous_margin) {
                const direction = metrics.profit_trend === 'positive' ? '↑' : '↓';
                liveMarginChange.textContent = `${direction} from ${metrics.previous_margin}`;
            }

            // Live Insights - Red Flag
            const liveFlagEl = document.getElementById('live-flag');
            if (liveFlagEl) {
                liveFlagEl.textContent = (metrics.red_flags && metrics.red_flags[0]) || 'No issues detected';
            }

            // Live Insights - Volatility
            const liveVolatilityEl = document.getElementById('live-volatility');
            if (liveVolatilityEl) {
                liveVolatilityEl.textContent = metrics.volatility || 'Low';
                liveVolatilityEl.className = 'metric-value';
            }

            const liveVolRange = document.getElementById('live-volatility-range');
            if (liveVolRange && metrics.volatility_range) {
                liveVolRange.textContent = `(${metrics.volatility_range})`;
            }

            // Draw Red Flag Sparkline
            drawFlagSparkline();

            // Key Metrics
            const keyMetrics = ['eps', 'pe', 'cagr', 'roe', 'debt', 'cap'];
            keyMetrics.forEach(key => {
                const elId = `metric-${key}`;
                let val = metrics[key];

                if (key === 'pe') val = metrics.pe_ratio;
                if (key === 'cagr') val = metrics.revenue_cagr;
                if (key === 'debt') val = metrics.debt_equity;
                if (key === 'cap') val = formatLargeNumber(metrics.market_cap);

                document.getElementById(elId).textContent = val || (key === 'cap' ? '—' : '0.00');

                // Validation indicators
                const confIconId = `conf-${key}`;
                const confIcon = document.getElementById(confIconId);

                // Map the key to what validator uses
                let validationKey = key;
                if (key === 'debt') validationKey = 'debt_equity';
                if (key === 'pe') validationKey = 'pe_ratio';
                if (key === 'cap') validationKey = 'market_cap';

                if (confIcon) {
                    // 1. Prioritize "VERIFIED" status from realtime API
                    const statusKey = `${validationKey}_status`;
                    const confKey = `${validationKey}_confidence`;

                    if (metrics[statusKey] === "VERIFIED" || metrics[confKey] === "HIGH") {
                        confIcon.className = 'fa-solid fa-circle-check confidence-icon high';
                        confIcon.title = metrics[statusKey] === "VERIFIED" ? "Verified from live API data" : "Verified against PDF data";
                        confIcon.classList.remove('hidden');
                    }
                    // 2. Fallback to PDF validation results
                    else if (metrics._validation && metrics._validation.validations[validationKey]) {
                        const validation = metrics._validation.validations[validationKey];
                        const confStatus = validation.confidence.toLowerCase();
                        confIcon.className = `fa-solid fa-${confStatus === 'medium' ? 'circle-info' : 'circle-exclamation'} confidence-icon ${confStatus}`;
                        confIcon.title = validation.message;
                        confIcon.classList.remove('hidden');
                    } else {
                        confIcon.classList.add('hidden');
                    }
                }
            });

            // Draw Key Metrics Sparklines
            drawKeyMetricsSparklines(metrics);

            // Show LIVE badge if any metrics are verified from API
            const liveBadge = document.getElementById('metrics-live-badge');
            if (liveBadge) {
                const hasVerifiedData = ['eps', 'pe_ratio', 'roe', 'market_cap', 'debt_equity', 'revenue_cagr'].some(
                    key => metrics[`${key}_status`] === 'VERIFIED'
                );
                if (hasVerifiedData) {
                    liveBadge.classList.remove('hidden');
                } else {
                    liveBadge.classList.add('hidden');
                }
            }

            // Rate Limit Warning
            if (statusText) {
                if (metrics.rate_limit) {
                    statusText.textContent = 'RATE LIMITED (Pacing API...)';
                    statusText.style.color = '#f59e0b';
                    statusDot.className = 'dot warning';
                } else {
                    statusText.textContent = 'CONNECTED';
                    statusText.style.color = '';
                    statusDot.className = 'dot connected';
                }
            }

            // Risk Radar
            drawRadarBenchmark(metrics);

            // Flag Sparkline
            drawFlagSparkline(metrics);

            // Sentiment Data
            if (metrics.sentiment) {
                const s = metrics.sentiment;
                const scoreEl = document.getElementById('sentiment-score');
                const labelEl = document.getElementById('sentiment-label');
                const headlinesEl = document.getElementById('sentiment-headlines');

                if (scoreEl) {
                    scoreEl.textContent = s.sentiment_score;
                    // Add color class
                    scoreEl.className = 'sentiment-value ' + s.sentiment_label.toLowerCase();
                }
                if (labelEl) labelEl.textContent = s.sentiment_label;

                if (headlinesEl && s.news && s.news.length > 0) {
                    headlinesEl.innerHTML = s.news.map(n => `
                    <a href="${n.url}" target="_blank" class="news-item">
                        <div class="news-meta">
                            <span>${n.source}</span>
                            <span>${new Date(n.published_at).toLocaleDateString()}</span>
                        </div>
                        <div class="news-title">
                            <span class="sentiment-badge ${n.sentiment_score > 0.05 ? 'positive' : (n.sentiment_score < -0.05 ? 'negative' : 'neutral')}"></span>
                            ${n.title}
                        </div>
                    </a>
                `).join('');
                } else if (headlinesEl) {
                    headlinesEl.innerHTML = '<span style="font-size:0.8rem; color:var(--text-secondary);">No relevant news found.</span>';
                }
            }

            // Set up action button listeners (only once per load)
            if (!fullAnalysisBtn) {
                fullAnalysisBtn = document.querySelector('.btn-primary');
                viewForecastBtn = document.querySelector('.btn-secondary');

                if (fullAnalysisBtn) {
                    fullAnalysisBtn.addEventListener('click', () => {
                        userInput.value = 'Provide a comprehensive financial analysis covering revenue trends, profitability, risks, and key metrics from the report.';
                        sendMessage();
                    });
                }

                if (viewForecastBtn) {
                    viewForecastBtn.addEventListener('click', () => {
                        userInput.value = 'Generate a forecast for the next quarter based on historical data and current trends.';
                        sendMessage();
                    });
                }
            }
        } catch (e) {
            console.error("Dashboard Render Error:", e);
            addMessage("CRITICAL DASHBOARD ERROR: " + e.message, 'system');
            addMessage("Please report this to support.", 'system');
        }
    }

    // Helper: Draw Red Flag Sparkline
    function drawFlagSparkline() {
        const canvas = document.getElementById('flag-sparkline');
        if (!canvas) return;

        const ctx = canvas.getContext('2d');
        const width = canvas.offsetWidth;
        const height = 30;

        canvas.width = width;
        canvas.height = height;

        // Sample data for sparkline (debt-to-equity trend)
        const data = [1.8, 1.9, 2.0, 2.2, 2.3];
        const max = Math.max(...data);
        const min = Math.min(...data);
        const range = max - min;

        ctx.clearRect(0, 0, width, height);

        // Draw line
        ctx.beginPath();
        ctx.strokeStyle = '#ef4444';
        ctx.lineWidth = 1.5;

        data.forEach((val, i) => {
            const x = (i / (data.length - 1)) * width;
            const y = height - ((val - min) / range) * (height - 4) - 2;

            if (i === 0) {
                ctx.moveTo(x, y);
            } else {
                ctx.lineTo(x, y);
            }
        });

        ctx.stroke();

        // Draw points
        ctx.fillStyle = '#ef4444';
        data.forEach((val, i) => {
            const x = (i / (data.length - 1)) * width;
            const y = height - ((val - min) / range) * (height - 4) - 2;

            ctx.beginPath();
            ctx.arc(x, y, 2, 0, Math.PI * 2);
            ctx.fill();
        });
    }

    // Helper: Draw Key Metrics Sparklines
    function drawKeyMetricsSparklines(metrics) {
        const history = metrics.history;
        const colors = {
            green: '#10b981',
            red: '#ef4444',
            yellow: '#f59e0b',
            neutral: '#94a3b8'
        };

        // Helper: Get color based on financial logic
        function getMetricColor(key, val, data) {
            if (!data || data.length < 2) return colors.green; // Default

            const first = data[0];
            const last = data[data.length - 1];
            const numVal = parseFloat(String(val).replace(/[^0-9.-]/g, ''));

            switch (key) {
                case 'eps':
                    return last > first ? colors.green : colors.red;

                case 'pe':
                    if (numVal > 25) return colors.red;
                    if (numVal < 5) return colors.yellow;
                    return colors.green;

                case 'cagr':
                    return numVal > 0 ? colors.green : colors.red;

                case 'roe':
                    if (numVal > 15) return colors.green;
                    if (numVal < 10) return colors.red;
                    return colors.yellow;

                case 'debt':
                    if (numVal < 1.0) return colors.green;
                    if (numVal > 1.5) return colors.red;
                    return colors.yellow;

                case 'cap':
                    if (Math.abs(last - first) < (first * 0.01)) return colors.neutral;
                    return last > first ? colors.green : colors.red;

                default:
                    return colors.green;
            }
        }

        // Define sparkline data for each metric, using real history if available
        const sparklineData = {
            'spark-eps': {
                data: (history && history.eps && history.eps.length > 0) ? history.eps : [3.8, 3.9, 4.0, 4.1, 4.12],
                key: 'eps',
                val: metrics.eps
            },
            'spark-pe': {
                data: [19.5, 20.2, 20.8, 21.3, 21.8],
                key: 'pe',
                val: metrics.pe_ratio
            },
            'spark-cagr': {
                data: (history && history.revenue && history.revenue.length > 0) ? history.revenue : [7.2, 7.6, 8.0, 8.3, 8.5],
                key: 'cagr',
                val: metrics.revenue_cagr
            },
            'spark-roe': {
                data: [17.5, 18.1, 18.6, 19.0, 19.2],
                key: 'roe',
                val: metrics.roe
            },
            'spark-debt': {
                data: [2.0, 2.1, 2.15, 2.25, 2.3],
                key: 'debt',
                val: metrics.debt_equity
            },
            'spark-cap': {
                data: [550, 570, 590, 600, 610],
                key: 'cap',
                val: metrics.market_cap
            }
        };

        Object.keys(sparklineData).forEach(canvasId => {
            const canvas = document.getElementById(canvasId);
            if (!canvas) return;

            const ctx = canvas.getContext('2d');
            const container = canvas.parentElement;
            const width = container.offsetWidth;
            const height = 20;

            canvas.width = width;
            canvas.height = height;

            const { data, key, val } = sparklineData[canvasId];
            const color = getMetricColor(key, val, data);
            const max = Math.max(...data);
            const min = Math.min(...data);
            const range = max - min || 1;

            ctx.clearRect(0, 0, width, height);

            // Draw line
            ctx.beginPath();
            ctx.strokeStyle = color;
            ctx.lineWidth = 1;
            ctx.lineCap = 'round';
            ctx.lineJoin = 'round';

            data.forEach((val, i) => {
                const x = (i / (data.length - 1)) * width;
                const y = height - ((val - min) / range) * (height - 6) - 3;

                if (i === 0) {
                    ctx.moveTo(x, y);
                } else {
                    ctx.lineTo(x, y);
                }
            });

            ctx.stroke();
        });
    }

    function drawFlagSparkline(metrics) {
        const canvas = document.getElementById('flag-sparkline');
        if (!canvas) return;
        const data = metrics?.history?.debt_equity || [1.8, 1.9, 2.0, 2.2, 2.3]; // Real data or fallback simulation
        drawMiniSparkline('flag-sparkline', data, '#ef4444');
    }

    // NEW: Risk Radar Benchmark Chart
    function drawRadarBenchmark(metrics) {
        const canvas = document.getElementById('risk-radar-chart');
        if (!canvas) return;

        const ctx = canvas.getContext('2d');
        if (riskRadarMainChart) riskRadarMainChart.destroy();

        const risks = metrics.risk_details || {};
        const getHealth = (r) => {
            if (!r) return 5;
            if (r.impact !== undefined) return 10 - parseFloat(r.impact);
            return 5;
        };

        const labels = ['Liquidity', 'Market', 'Credit', 'Governance', 'Operational'];
        const companyData = [
            getHealth(risks.liquidity),
            getHealth(risks.market),
            getHealth(risks.credit),
            getHealth(risks.governance),
            7.5
        ];

        const industryData = [6, 5, 7, 8, 7];

        riskRadarMainChart = new Chart(ctx, {
            type: 'radar',
            data: {
                labels: labels,
                datasets: [{
                    label: metrics.ticker || 'Company',
                    data: companyData,
                    backgroundColor: `${getColorByScore(metrics.risk_score * 10)}33`, // 20% opacity
                    borderColor: getColorByScore(metrics.risk_score * 10),
                    pointBackgroundColor: getColorByScore(metrics.risk_score * 10),
                    borderWidth: 2
                }, {
                    label: 'Industry Avg',
                    data: industryData,
                    backgroundColor: 'rgba(148, 163, 184, 0.2)',
                    borderColor: '#94a3b8',
                    pointBackgroundColor: '#94a3b8',
                    borderWidth: 1,
                    borderDash: [5, 5]
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    r: {
                        angleLines: { color: 'rgba(255, 255, 255, 0.1)' },
                        grid: { color: 'rgba(255, 255, 255, 0.1)' },
                        pointLabels: {
                            color: '#e2e8f0',
                            font: { size: 12 }
                        },
                        ticks: { display: false, max: 10, min: 0 }
                    }
                },
                plugins: {
                    legend: {
                        position: 'top',
                        labels: { color: '#cbd5e1' }
                    }
                }
            }
        });
    }

    // NEW: Revenue Deep Dive (Dual Donut + Custom Legend + Table)
    function drawRevenueDeepDive(data) {
        if (!data) return;
        const segments = data.revenue_segments || {};
        const prevData = data.revenue_comparison?.previous_segments || {};

        const colors = ['#5b68f5', '#10b981', '#f59e0b', '#ef4444', '#94a3b8', '#8b5cf6', '#ec4899'];

        // Register DataLabels plugin
        if (typeof ChartDataLabels !== 'undefined') Chart.register(ChartDataLabels);

        // Draw FY 2024
        const canvas24 = document.getElementById('revenue-donut-chart-2024');
        if (!canvas24) return;
        const ctx24 = canvas24.getContext('2d');
        if (revenueChart2024) revenueChart2024.destroy();

        const labels = Object.keys(segments);
        const values24 = Object.values(segments).map(s => s.weight);

        revenueChart2024 = new Chart(ctx24, {
            type: 'doughnut',
            data: {
                labels: labels,
                datasets: [{
                    data: values24,
                    backgroundColor: colors,
                    borderWidth: 0,
                    hoverOffset: 15
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                cutout: '65%',
                plugins: {
                    legend: { display: false },
                    datalabels: {
                        color: '#fff',
                        font: { weight: 'bold', size: 12 },
                        formatter: (val) => val > 5 ? `${val}%` : ''
                    }
                },
                onClick: (e, elements) => {
                    if (elements.length > 0) {
                        const index = elements[0].index;
                        highlightSegmentInTable(index);
                    }
                }
            }
        });

        // Draw FY 2023 (Comparison)
        const canvas23 = document.getElementById('revenue-donut-chart-2023');
        if (canvas23) {
            const ctx23 = canvas23.getContext('2d');
            if (revenueChart2023) revenueChart2023.destroy();

            const values23 = labels.map(l => prevData[l] || (100 / (labels.length || 1)));

            revenueChart2023 = new Chart(ctx23, {
                type: 'doughnut',
                data: {
                    labels: labels,
                    datasets: [{
                        data: values23,
                        backgroundColor: colors.map(c => c + '40'), // 25% opacity
                        borderWidth: 0
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    cutout: '75%',
                    plugins: {
                        legend: { display: false },
                        datalabels: { display: false }
                    }
                }
            });
        }

        // Populate Legend & Table
        populateRevenueLegend(segments, colors);
        populateRevenueTable(segments);

        // Set AI Insight
        const insightEl = document.getElementById('revenue-ai-insight');
        if (insightEl) insightEl.textContent = data.segment_insight || "Revenue mix remains stable with significant growth in core segments.";
    }

    function populateRevenueLegend(segments, colors) {
        const legend = document.getElementById('revenue-segment-legend');
        if (!legend) return;
        legend.innerHTML = '';

        Object.entries(segments).forEach(([name, data], i) => {
            const item = document.createElement('div');
            item.className = 'legend-item';

            const isUp = (data.yoy_growth || '').startsWith('+');
            const trendClass = isUp ? 'trend-up' : 'trend-down';
            const arrow = isUp ? '↑' : '↓';

            item.innerHTML = `
                <div class="legend-color" style="background: ${colors[i % colors.length]}"></div>
                <div class="legend-info">
                    <span class="legend-label">${name}</span>
                    <span class="legend-values">${data.actual_value || 'N/A'} (${data.weight || 0}%)</span>
                </div>
                <div class="legend-trend ${trendClass}">
                    ${arrow} ${data.yoy_growth || '0%'}
                </div>
                <div class="sparkline-wrapper">
                    <canvas id="rev-spark-${i}"></canvas>
                </div>
            `;
            legend.appendChild(item);

            // Draw Sparkline
            setTimeout(() => {
                drawSegmentSparkline(`rev-spark-${i}`, data.history || [10, 12, 11, 14], colors[i % colors.length]);
            }, 100);
        });
    }

    function drawSegmentSparkline(id, data, color) {
        const canvas = document.getElementById(id);
        if (!canvas) return;
        const ctx = canvas.getContext('2d');
        new Chart(ctx, {
            type: 'line',
            data: {
                labels: data.map((_, i) => i),
                datasets: [{
                    data: data,
                    borderColor: color,
                    borderWidth: 1.5,
                    pointRadius: 0,
                    tension: 0.4,
                    fill: false
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: { x: { display: false }, y: { display: false } },
                plugins: {
                    legend: { display: false },
                    tooltip: { enabled: false },
                    datalabels: { display: false }
                }
            }
        });
    }

    function populateRevenueTable(segments) {
        const tbody = document.getElementById('segment-table-body');
        if (!tbody) return;
        tbody.innerHTML = '';

        Object.entries(segments).forEach(([name, data]) => {
            const row = document.createElement('tr');
            const isUp = (data.yoy_growth || '').startsWith('+');

            row.innerHTML = `
                <td><strong>${name}</strong></td>
                <td>${data.actual_value || 'N/A'}</td>
                <td>${data.weight || 0}%</td>
                <td class="${isUp ? 'positive' : 'negative'}">${data.yoy_growth || '0%'}</td>
                <td><small>${data.insight || 'Steady performance'}</small></td>
            `;
            tbody.appendChild(row);
        });
    }

    function highlightSegmentInTable(index) {
        const rows = document.querySelectorAll('#segment-table-body tr');
        rows.forEach((row, i) => {
            if (i === index) {
                row.style.background = 'rgba(91, 104, 245, 0.2)';
                row.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
            } else {
                row.style.background = 'transparent';
            }
        });
    }

    function drawSentimentTrend(trendData, currentScore) {
        const ctx = document.getElementById('sentiment-trend-chart').getContext('2d');
        if (sentimentTrendChart) sentimentTrendChart.destroy();

        const scoreEl = document.getElementById('current-sentiment-score');
        if (scoreEl) {
            scoreEl.textContent = (currentScore || 0).toFixed(2);
            scoreEl.style.color = currentScore > 0.05 ? '#10b981' : (currentScore < -0.05 ? '#ef4444' : '#f8fafc');
        }

        const data = trendData || [0.5, 0.55, 0.48, 0.6, 0.7, 0.65, currentScore || 0.74];
        const labels = ['D-6', 'D-5', 'D-4', 'D-3', 'D-2', 'D-1', 'Today'];

        const sentimentColor = currentScore > 0.05 ? '#10b981' : (currentScore < -0.05 ? '#ef4444' : '#5b68f5');

        sentimentTrendChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [{
                    data: data,
                    borderColor: sentimentColor,
                    borderWidth: 2,
                    tension: 0.4,
                    fill: true,
                    backgroundColor: `${sentimentColor}11`,
                    pointRadius: 4,
                    pointBackgroundColor: sentimentColor
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    x: { display: false },
                    y: {
                        display: true,
                        min: -1,
                        max: 1,
                        grid: { color: 'rgba(148, 163, 184, 0.05)' },
                        ticks: { color: '#64748b', font: { size: 9 } }
                    }
                },
                plugins: {
                    legend: { display: false },
                    datalabels: { display: false }
                }
            }
        });
    }

    // Risk Radar Chart (Legacy - Keep for reference or remove if fully replaced)
    // let riskRadarChart = null;
    // ... removed ...

    // NEW: Mini Sparkline Helper
    function drawMiniSparkline(canvasId, data, color) {
        const ctx = document.getElementById(canvasId).getContext('2d');
        new Chart(ctx, {
            type: 'line',
            data: {
                labels: data.map((_, i) => i),
                datasets: [{
                    data: data,
                    borderColor: color,
                    borderWidth: 2,
                    pointRadius: 0,
                    tension: 0.4,
                    fill: false
                }]
            },
            options: {
                responsive: false,
                maintainAspectRatio: false,
                scales: { x: { display: false }, y: { display: false } },
                plugins: {
                    legend: { display: false },
                    tooltip: { enabled: false },
                    datalabels: { display: false }
                }
            }
        });
    }

    // Global chart instances for Financials tab
    let historicalPerformanceChart = null;
    let marginTrendsChart = null;

    function populateFinancials(m) {
        if (!m) return;

        // Helper: Create metric item (simplified - no industry comparison)
        const createMetricItem = (label, value) => {
            return `
                <div class="financials-metric-item">
                    <span class="metric-label">${label}</span>
                    <div class="metric-value-row">
                        <span class="metric-value">${value || 'N/A'}</span>
                    </div>
                </div>
            `;
        };

        // Populate Valuation
        document.getElementById('metrics-valuation').innerHTML =
            createMetricItem('P/E Ratio', m.pe_ratio) +
            createMetricItem('Market Cap', m.market_cap) +
            createMetricItem('EPS', m.eps);

        // Populate Efficiency
        document.getElementById('metrics-efficiency').innerHTML =
            createMetricItem('ROE', m.roe) +
            createMetricItem('Profit Margin', m.profit_margin) +
            createMetricItem('Rev Growth', m.revenue_growth);

        // Populate Solvency
        document.getElementById('metrics-solvency').innerHTML =
            createMetricItem('Debt/Equity', m.debt_equity) +
            createMetricItem('Dividend Yield', m.dividend_yield) +
            createMetricItem('Volatility', m.volatility);

        // Draw Charts
        drawHistoricalPerformance(m);
        drawMarginTrends(m);

        // Populate Key Metrics Grid
        populateKeyMetricsFinancials(m);
    }

    // Draw Historical Performance Chart (Revenue & Net Income)
    function drawHistoricalPerformance(metrics) {
        const ctx = document.getElementById('historical-performance-chart');
        if (!ctx) return;

        if (historicalPerformanceChart) historicalPerformanceChart.destroy();

        const history = metrics.history || {};
        const revenueData = history.revenue || [];
        const netIncomeData = history.net_income || [];

        // Generate labels (quarters or years)
        const labels = revenueData.length > 0 ?
            revenueData.map((_, i) => `-${revenueData.length - 1 - i}Q`) :
            ['-20/30', '20/30', '30/30', '20/30', '20/30'];

        historicalPerformanceChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: labels.reverse(), // Oldest to newest
                datasets: [
                    {
                        label: 'Revenue ($B)',
                        data: revenueData.length > 0 ? revenueData.map(v => v / 1e9) : [10, 20, 30, 40, 50],
                        borderColor: '#10b981',
                        backgroundColor: 'rgba(16, 185, 129, 0.1)',
                        borderWidth: 2,
                        tension: 0.4,
                        fill: true,
                        pointRadius: 4,
                        pointBackgroundColor: '#10b981'
                    },
                    {
                        label: 'Net Income ($B)',
                        data: netIncomeData.length > 0 ? netIncomeData.map(v => v / 1e9) : [5, 10, 15, 20, 25],
                        borderColor: '#5b68f5',
                        backgroundColor: 'rgba(91, 104, 245, 0.1)',
                        borderWidth: 2,
                        tension: 0.4,
                        fill: true,
                        pointRadius: 4,
                        pointBackgroundColor: '#5b68f5'
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    x: {
                        grid: { color: 'rgba(148, 163, 184, 0.05)' },
                        ticks: { color: '#64748b', font: { size: 10 } }
                    },
                    y: {
                        grid: { color: 'rgba(148, 163, 184, 0.05)' },
                        ticks: { color: '#64748b', font: { size: 12 } }
                    }
                },
                plugins: {
                    legend: {
                        position: 'top',
                        labels: { color: '#94a3b8', font: { size: 11 }, padding: 15 }
                    },
                    datalabels: { display: false }
                }
            }
        });
    }

    // Draw Margin Trends Chart
    function drawMarginTrends(metrics) {
        const ctx = document.getElementById('margin-trends-chart');
        if (!ctx) return;

        if (marginTrendsChart) marginTrendsChart.destroy();

        const history = metrics.history || {};

        // Calculate gross margin if we have revenue and net income
        let marginData = [];
        if (history.revenue && history.net_income && history.revenue.length > 0) {
            marginData = history.revenue.map((rev, i) => {
                const netIncome = history.net_income[i] || 0;
                return rev > 0 ? (netIncome / rev) * 100 : 0;
            });
        } else {
            // Fallback sample data
            marginData = [20, 40, 60, 100, 120, 140, 180, 200];
        }

        const labels = marginData.map((_, i) => `-${marginData.length - 1 - i}Q`);

        marginTrendsChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: labels.reverse(),
                datasets: [{
                    label: 'Gross Margin (%)',
                    data: marginData,
                    borderColor: '#10b981',
                    backgroundColor: 'rgba(16, 185, 129, 0.1)',
                    borderWidth: 2,
                    tension: 0.4,
                    fill: true,
                    pointRadius: 4,
                    pointBackgroundColor: '#10b981'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    x: {
                        grid: { color: 'rgba(148, 163, 184, 0.05)' },
                        ticks: { color: '#64748b', font: { size: 12 } }
                    },
                    y: {
                        grid: { color: 'rgba(148, 163, 184, 0.05)' },
                        ticks: { color: '#64748b', font: { size: 12 } },
                        min: 0
                    }
                },
                plugins: {
                    legend: { display: false },
                    datalabels: { display: false }
                }
            }
        });
    }

    // Populate Key Metrics Grid (Bottom section)
    function populateKeyMetricsFinancials(m) {
        const grid = document.getElementById('key-metrics-grid');
        if (!grid) return;

        const keyMetrics = [
            { label: 'Free Cash Flow (FCF)', value: m.free_cash_flow || 'N/A' },
            { label: 'Price to Book (P/B)', value: m.price_to_book || 'N/A' }
        ];

        grid.innerHTML = keyMetrics.map(metric => `
            <div class="key-metric-box">
                <span class="key-metric-label">${metric.label}</span>
                <span class="key-metric-value">${metric.value}</span>
            </div>
        `).join('');
    }

    function drawRiskRadarMain(metrics) {
        const ctx = document.getElementById('risk-radar-main');
        if (!ctx) return;
        if (riskRadarMainChart) riskRadarMainChart.destroy();

        const riskData = [
            metrics.liquidity_risk || 0,
            metrics.market_risk || 0,
            metrics.credit_risk || 0,
            metrics.governance_risk || 0
        ];

        const industryData = metrics.sector_benchmarks ? [
            metrics.sector_benchmarks.liquidity || 30,
            metrics.sector_benchmarks.market || 45,
            metrics.sector_benchmarks.credit || 25,
            metrics.sector_benchmarks.governance || 40
        ] : [30, 45, 25, 40];

        riskRadarMainChart = new Chart(ctx, {
            type: 'radar',
            data: {
                labels: ['Liquidity', 'Market', 'Credit', 'Governance'],
                datasets: [
                    {
                        label: 'Company Profile',
                        data: riskData,
                        backgroundColor: 'rgba(91, 104, 245, 0.4)',
                        borderColor: '#5b68f5',
                        borderWidth: 2,
                        pointBackgroundColor: '#5b68f5'
                    },
                    {
                        label: 'Industry Avg',
                        data: industryData,
                        backgroundColor: 'rgba(148, 163, 184, 0.1)',
                        borderColor: 'rgba(148, 163, 184, 0.5)',
                        borderWidth: 1,
                        borderDash: [5, 5],
                        pointRadius: 0
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    r: {
                        angleLines: { color: 'rgba(148, 163, 184, 0.1)' },
                        grid: { color: 'rgba(148, 163, 184, 0.1)' },
                        pointLabels: { color: '#f8fafc', font: { size: 11, weight: '600' } },
                        ticks: { display: false, max: 100, min: 0 }
                    }
                },
                plugins: {
                    legend: { position: 'bottom', labels: { color: '#94a3b8', font: { size: 10 } } },
                    datalabels: { display: false }
                }
            }
        });
    }

    function drawStabilityBenchmarking(m) {
        const ctx = document.getElementById('stability-score-chart');
        if (!ctx) return;
        if (stabilityChart) stabilityChart.destroy();

        // Raw values
        const cr = parseFloat(m.current_ratio) || 0;
        const de = parseFloat(m.debt_equity) || 0;
        const beta = parseFloat(m.beta) || 0;
        const own = parseFloat(m.ownership) || 0;

        // Normalization Logic (Goal: Healthy Target = 60 Score)
        const crScore = Math.max(5, Math.min(100, (cr / 1.2) * 60));

        let deScore = 0;
        if (de <= 2.0) deScore = 60 + ((2.0 - de) / 2.0) * 40;
        else deScore = Math.max(5, 60 - ((de - 2.0) / 2.0) * 60);

        let betaScore = 0;
        if (beta <= 1.3) betaScore = 60 + ((1.3 - beta) / 1.3) * 40;
        else betaScore = Math.max(5, 60 - ((beta - 1.3) / 1.3) * 60);

        const ownScore = Math.max(5, Math.min(100, (own / 10) * 60));

        stabilityChart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: [
                    `Liquidity: ${cr.toFixed(2)}`,
                    `Solvency: ${de.toFixed(2)}`,
                    `Beta: ${beta.toFixed(2)}`,
                    `Insider Ownership: ${own.toFixed(0)}%`
                ],
                datasets: [
                    {
                        label: 'Stability Score',
                        data: [crScore, deScore, betaScore, ownScore],
                        backgroundColor: (ctx) => {
                            const val = ctx.raw;
                            if (val >= 60) return '#10b981'; // Healthy
                            if (val >= 40) return '#f59e0b'; // Warning
                            return '#ef4444'; // Risk
                        },
                        borderRadius: 4,
                        barThickness: 24
                    },
                    {
                        label: 'Healthy Threshold',
                        data: [60, 60, 60, 60],
                        type: 'line',
                        borderColor: 'rgba(255, 255, 255, 0.4)',
                        borderDash: [5, 5],
                        showLine: false,
                        pointStyle: 'rectRot',
                        pointRadius: 6,
                        pointBackgroundColor: '#fff'
                    }
                ]
            },
            options: {
                indexAxis: 'y',
                layout: {
                    padding: { left: 90, right: 20, top: 10, bottom: 10 }
                },
                plugins: {
                    legend: { display: false },
                    datalabels: { display: false },
                    tooltip: {
                        callbacks: {
                            label: (ctx) => `Stability Score: ${ctx.raw.toFixed(0)}/100`,
                            afterLabel: (ctx) => {
                                const targets = ["> 1.20 Target", "< 2.00 Target", "< 1.30 Target", "> 10% Target"];
                                return `Ref: ${targets[ctx.dataIndex]}`;
                            }
                        }
                    }
                },
                scales: {
                    x: {
                        min: 0,
                        max: 100,
                        grid: { color: 'rgba(148, 163, 184, 0.05)', drawBorder: false },
                        ticks: {
                            color: '#64748b',
                            font: { size: 12 },
                            callback: (val) => val === 60 ? 'TARGET' : (val % 20 === 0 ? val : '')
                        }
                    },
                    y: {
                        grid: { display: false },
                        ticks: {
                            color: '#f8fafc',
                            padding: 10,
                            font: { family: 'Inter', size: 14, weight: '600' }
                        }
                    }
                },
                responsive: true,
                maintainAspectRatio: false
            }
        });
    }

    function populateRisks(m) {
        const cardsGrid = document.getElementById('detailed-risk-cards');
        if (!cardsGrid) return;

        const risks = m.risk_details || {};
        const timestamp = document.getElementById('risk-timestamp');
        if (timestamp) timestamp.textContent = new Date().toLocaleTimeString();

        drawRiskRadarMain(m);
        drawStabilityBenchmarking(m);

        cardsGrid.innerHTML = Object.entries(risks).map(([key, data], i) => {
            const cleanKey = key.toLowerCase();
            const displayTitle = cleanKey.charAt(0).toUpperCase() + cleanKey.slice(1);

            const quantitative = cleanKey === 'liquidity' ? `Ratio: ${data.ratio || m.current_ratio || 'N/A'}` :
                cleanKey === 'market' ? `Beta: ${data.beta || m.beta || 'N/A'}` :
                    cleanKey === 'governance' ? `Ownership: ${data.ownership || m.ownership || 'N/A'}` :
                        `Score: ${data.score || 'N/A'}`;

            const trend = data.trend || 'neutral';
            const arrow = trend === 'positive' ? '↑' : (trend === 'negative' ? '↓' : '—');
            const trendClass = trend;

            return `
                <div class="risk-card-detailed" onclick="this.classList.toggle('expanded')">
                    <div class="risk-card-header" style="justify-content: center;">
                        <div class="risk-title-group" style="text-align: center; width: 100%;">
                            <h4>${displayTitle} Risk</h4>
                            <span class="quantitative-metric" style="display: block; margin-top: 4px;">${quantitative}</span>
                        </div>
                    </div>
                    
                    <p class="risk-content-summary" style="text-align: center; color: ${data.critical_red_flags && !data.critical_red_flags.includes('No critical') ? '#ef4444' : 'inherit'}">
                         ${(data.critical_red_flags && !data.critical_red_flags.includes('No critical')) ?
                    `<i class="fa-solid fa-triangle-exclamation"></i> ` + data.critical_red_flags :
                    (data.summary || 'No detailed analysis available.')}
                    </p>
                    
                    <div class="peer-benchmarking" style="justify-content: center;">
                        <span class="peer-label">Industry Avg:</span>
                        <span class="peer-value">${data.industry_avg || 'N/A'}</span>
                    </div>

                    <div class="risk-drill-down">
                        <div>
                            <span class="factors-title">Key Factors:</span>
                            <ul class="risk-factors-detailed">
                                ${(data.factors || []).map(f => `<li>${f}</li>`).join('')}
                            </ul>
                        </div>
                        <div class="red-flag-block">
                            <span class="red-flag-title">Analysis Summary:</span>
                            <p class="red-flag-text">${data.summary || 'N/A'}</p>
                        </div>
                    </div>
                </div>
            `;
        }).join('');

        // Removed sparkline drawing logic as UI elements were removed
    }

    function populateNews(news) {
        const container = document.getElementById('news-tab-list');
        container.innerHTML = '';
        if (!news || news.length === 0) {
            container.innerHTML = '<p class="description-text">No recent market news found.</p>';
            return;
        }

        news.forEach(article => {
            const div = document.createElement('div');
            div.className = 'news-item-tab';
            div.innerHTML = `
                <span class="source-meta">${article.source} • ${new Date(article.published_at).toLocaleDateString()}</span>
                <h4><a href="${article.url}" target="_blank">${article.title}</a></h4>
            `;
            container.appendChild(div);
        });
    }

    function showRiskDetails(category, metrics, riskInsights) {
        const riskInsightPanel = document.getElementById('risk-insight-panel');
        const insightTitle = document.getElementById('insight-title');
        const insightContent = document.getElementById('insight-content');

        const titleMap = {
            liquidity: 'Liquidity Risk Details',
            market: 'Market Risk Exposure',
            credit: 'Credit & Debt Analysis',
            governance: 'Governance & Structure'
        };

        insightTitle.innerText = titleMap[category];
        insightContent.innerHTML = riskInsights[category](metrics);
        riskInsightPanel.classList.remove('hidden');
    }

    // Ticker Analysis Logic
    if (analyzeBtn) {
        analyzeBtn.addEventListener('click', () => {
            if (tickerInput && tickerInput.value.trim()) {
                analyzeTicker(tickerInput.value.trim());
            } else {
                alert("Please enter a stock ticker.");
            }
        });
    }

    if (tickerInput) {
        tickerInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter' && tickerInput.value.trim()) {
                analyzeTicker(tickerInput.value.trim());
            }
        });
    }

    if (welcomeAnalyzeBtn) {
        welcomeAnalyzeBtn.addEventListener('click', () => {
            if (welcomeTickerInput && welcomeTickerInput.value.trim()) {
                analyzeTicker(welcomeTickerInput.value.trim());
            } else {
                alert("Please enter a stock ticker.");
            }
        });
    }

    if (welcomeTickerInput) {
        welcomeTickerInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter' && welcomeTickerInput.value.trim()) {
                analyzeTicker(welcomeTickerInput.value.trim());
            }
        });
    }

    async function analyzeTicker(ticker) {
        if (!isInitialized) {
            await initializeAgent("", "demo");
        }

        try {
            addMessage(`Analyzing ticker ${ticker}...`, 'system');

            // UI Feedback
            if (analyzeBtn) analyzeBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Analyzing...';
            if (welcomeAnalyzeBtn) welcomeAnalyzeBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Analyzing...';

            const res = await fetch('/api/analyze', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ ticker: ticker })
            });

            if (!res.ok) throw new Error((await res.json()).detail);

            const data = await res.json();

            // Hide welcome, show dashboard
            const welcomeOverlay = document.getElementById('dashboard-welcome');
            if (welcomeOverlay) welcomeOverlay.classList.add('hidden');

            // Populate
            populateDashboard(data.metrics);
            addMessage(`Analysis complete for ${ticker}.`, 'system');

        } catch (e) {
            console.error('Analysis failed:', e);
            addMessage(`Error analyzing ${ticker}: ${e.message}`, 'error');
            alert(`Analysis failed: ${e.message}`);
        } finally {
            if (analyzeBtn) analyzeBtn.innerHTML = 'Analyze <i class="fa-solid fa-arrow-right"></i>';
            if (welcomeAnalyzeBtn) welcomeAnalyzeBtn.innerHTML = '<i class="fa-solid fa-bolt"></i> Analyze';
        }
    }



    // Chat Logic
    async function sendMessage() {
        const text = userInput.value.trim();
        if (!text || !isInitialized || isProcessing) return;

        addMessage(text, 'user');
        userInput.value = '';
        userInput.style.height = 'auto';
        isProcessing = true;
        sendBtn.disabled = true;

        try {
            const res = await fetch('/api/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message: text })
            });

            if (!res.ok) throw new Error((await res.json()).detail);

            const aiMsg = addMessage('', 'ai');
            const contentDiv = aiMsg.querySelector('.content');
            let fullText = "";
            let buffer = "";

            const reader = res.body.getReader();
            const decoder = new TextDecoder();

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;

                const chunk = decoder.decode(value, { stream: true });
                buffer += chunk;

                const jsonStart = buffer.indexOf('__JSON_START__');
                const jsonEnd = buffer.indexOf('__JSON_END__');

                if (jsonStart !== -1 && jsonEnd !== -1) {
                    const jsonStr = buffer.substring(jsonStart + 14, jsonEnd);
                    try {
                        const jsonObj = JSON.parse(jsonStr);
                        fullText += buffer.substring(0, jsonStart);
                        contentDiv.innerHTML = marked.parse(fullText);

                        // Render chart similar to addMessage
                        if (jsonObj.chart_data) {
                            const chartContainer = document.createElement('div');
                            chartContainer.style.marginTop = '1rem';
                            chartContainer.style.height = '400px';
                            const canvas = document.createElement('canvas');
                            chartContainer.appendChild(canvas);
                            contentDiv.appendChild(chartContainer);

                            const ctx = canvas.getContext('2d');
                            new Chart(ctx, {
                                type: 'line',
                                data: {
                                    labels: jsonObj.chart_data.dates,
                                    datasets: [{
                                        label: `${jsonObj.chart_data.ticker} Price`,
                                        data: jsonObj.chart_data.prices,
                                        borderColor: '#5b68f5',
                                        borderWidth: 2,
                                        tension: 0.4
                                    }]
                                },
                                options: { responsive: true, maintainAspectRatio: false }
                            });

                            if (jsonObj.chart_data.metrics) {
                                const m = jsonObj.chart_data.metrics;
                                const metricsDiv = document.createElement('div');
                                metricsDiv.style.display = 'flex';
                                metricsDiv.style.gap = '1rem';
                                metricsDiv.style.marginTop = '1rem';
                                metricsDiv.innerHTML = `
                                    <div style="background:rgba(30,41,59,0.5); padding:0.5rem 1rem; border-radius:0.5rem;">
                                        <span style="color:#94a3b8;">PE:</span> <span style="color:#f8fafc; font-weight:600;">${m.pe_ratio || 'N/A'}</span>
                                    </div>
                                    <div style="background:rgba(30,41,59,0.5); padding:0.5rem 1rem; border-radius:0.5rem;">
                                        <span style="color:#94a3b8;">Market Cap:</span> <span style="color:#f8fafc; font-weight:600;">${m.market_cap || 'N/A'}</span>
                                    </div>
                                    <div style="background:rgba(30,41,59,0.5); padding:0.5rem 1rem; border-radius:0.5rem;">
                                        <span style="color:#94a3b8;">Div:</span> <span style="color:#f8fafc; font-weight:600;">${m.dividend_yield || 'N/A'}</span>
                                    </div>
                                `;
                                contentDiv.appendChild(metricsDiv);
                            }
                        }

                        buffer = buffer.substring(jsonEnd + 12);
                    } catch (e) {
                        console.error("JSON Parse error:", e);
                    }
                } else if (jsonStart === -1) {
                    fullText += buffer;
                    contentDiv.innerHTML = marked.parse(fullText);
                    buffer = "";
                    chatMessages.scrollTop = chatMessages.scrollHeight;
                }
            }

        } catch (e) {
            addMessage('Error: ' + e.message, 'system');
        } finally {
            isProcessing = false;
            sendBtn.disabled = false;
        }
    }

    sendBtn.addEventListener('click', sendMessage);
    userInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });

    userInput.addEventListener('input', function () {
        this.style.height = 'auto';
        this.style.height = (this.scrollHeight) + 'px';
    });

    // Reset
    resetBtn.addEventListener('click', async () => {
        if (!confirm("Clear conversation?")) return;
        try {
            await fetch('/api/reset', { method: 'POST' });
            chatMessages.innerHTML = '';
            addMessage('Conversation cleared.', 'system');
        } catch (e) {
            console.error(e);
        }
    });

    // Export
    exportBtn.addEventListener('click', async () => {
        if (!isInitialized) {
            alert("No conversation to export.");
            return;
        }
        try {
            exportBtn.disabled = true;
            exportBtn.textContent = 'Exporting...';
            const res = await fetch('/api/export_pdf');
            if (res.ok) {
                const blob = await res.blob();
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = "financial_report.pdf";
                document.body.appendChild(a);
                a.click();
                a.remove();
                window.URL.revokeObjectURL(url);
            } else {
                alert("Export failed.");
            }
        } catch (e) {
            console.error(e);
            alert("Export error: " + e.message);
        } finally {
            exportBtn.disabled = false;
            exportBtn.textContent = 'Export PDF';
            exportBtn.innerHTML = '<i class="fa-solid fa-file-export"></i>';
        }
    });

    // Quick Actions
    document.querySelectorAll('.quick-action-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const query = btn.getAttribute('data-query');
            if (query) {
                userInput.value = query;
                sendMessage();
            }
        });
    });

    // Chatbot Resize Logic (Top-Left Handle)
    const resizeHandle = document.querySelector('.chatbot-resize-handle');
    const panelEl = document.getElementById('chatbot-panel');

    if (resizeHandle && panelEl) {
        let isResizing = false;
        let startX, startY, startWidth, startHeight;

        resizeHandle.addEventListener('mousedown', (e) => {
            isResizing = true;
            startX = e.clientX;
            startY = e.clientY;
            startWidth = parseInt(document.defaultView.getComputedStyle(panelEl).width, 10);
            startHeight = parseInt(document.defaultView.getComputedStyle(panelEl).height, 10);
            e.preventDefault();

            // Add listeners to document to handle drag outside element
            document.addEventListener('mousemove', doDrag, false);
            document.addEventListener('mouseup', stopDrag, false);
        });

        function doDrag(e) {
            if (!isResizing) return;

            // Calculate new dimensions
            // Moving LEFT (negative delta) increases width
            // Moving UP (negative delta) increases height
            const width = startWidth - (e.clientX - startX);
            const height = startHeight - (e.clientY - startY);

            if (width > 300 && width < 800) {
                panelEl.style.width = width + 'px';
            }
            if (height > 350 && height < window.innerHeight - 100) {
                panelEl.style.height = height + 'px';
            }
        }

        function stopDrag(e) {
            isResizing = false;
            document.removeEventListener('mousemove', doDrag, false);
            document.removeEventListener('mouseup', stopDrag, false);
        }
    }



    // Risk Insight Close Button
    const closeInsightBtn = document.getElementById('close-insight');
    const riskInsightPanel = document.getElementById('risk-insight-panel');

    if (closeInsightBtn) {
        closeInsightBtn.addEventListener('click', () => {
            riskInsightPanel.classList.add('hidden');
        });
    }

    // === Resizable Panels ===
    const sidebarResizer = document.getElementById('sidebar-resizer');
    const heroResizer = document.getElementById('hero-resizer');

    // Load saved dimensions
    const savedSidebarWidth = localStorage.getItem('sidebarWidth');
    const savedHeroHeight = localStorage.getItem('heroHeight');

    if (savedSidebarWidth) {
        appContainer.style.setProperty('--sidebar-width', `${savedSidebarWidth}px`);
    }
    if (savedHeroHeight) {
        heroCard.style.height = `${savedHeroHeight}px`;
    }

    function initResizer(resizer, axis) {
        let isDragging = false;

        resizer.addEventListener('mousedown', (e) => {
            isDragging = true;
            resizer.classList.add('active');
            document.body.classList.add('dragging');
            e.preventDefault();
        });

        document.addEventListener('mousemove', (e) => {
            if (!isDragging) return;

            if (axis === 'horizontal') {
                const newWidth = window.innerWidth - e.clientX;
                if (newWidth >= 200 && newWidth <= 600) {
                    appContainer.style.setProperty('--sidebar-width', `${newWidth}px`);
                    localStorage.setItem('sidebarWidth', newWidth);
                }
            } else if (axis === 'vertical') {
                const rect = heroCard.getBoundingClientRect();
                const newHeight = e.clientY - rect.top;
                if (newHeight >= 150 && newHeight <= 800) {
                    heroCard.style.height = `${newHeight}px`;
                    localStorage.setItem('heroHeight', newHeight);
                }
            }
        });

        document.addEventListener('mouseup', () => {
            if (isDragging) {
                isDragging = false;
                resizer.classList.remove('active');
                document.body.classList.remove('dragging');
            }
        });
    }

    if (sidebarResizer) initResizer(sidebarResizer, 'horizontal');
    if (heroResizer) initResizer(heroResizer, 'vertical');

    // === Hero Card Toggle ===
    if (toggleHeroBtn && heroCard) {
        // Load saved visibility state
        const heroState = localStorage.getItem('heroVisible');
        if (heroState === 'false') {
            heroCard.classList.add('hero-collapsed');
            toggleHeroBtn.classList.add('active');
        }

        toggleHeroBtn.addEventListener('click', () => {
            const isCollapsed = heroCard.classList.toggle('hero-collapsed');
            toggleHeroBtn.classList.toggle('active');
            localStorage.setItem('heroVisible', !isCollapsed);
        });
    }
});

document.addEventListener('DOMContentLoaded', () => {
    const runBtn = document.getElementById('runBtn');
    const agentIdInput = document.getElementById('agentId');
    const sqlQueryInput = document.getElementById('sqlQuery');
    
    const errorBox = document.getElementById('errorBox');
    const errorMsg = document.getElementById('errorMsg');
    
    const resultsContent = document.getElementById('resultsContent');
    const emptyState = document.querySelector('.empty-state');
    const securityMetrics = document.getElementById('securityMetrics');
    
    const maskedTags = document.getElementById('maskedTags');
    const rewrittenSql = document.getElementById('rewrittenSql');
    
    const tableHead = document.getElementById('tableHead');
    const tableBody = document.getElementById('tableBody');

    runBtn.addEventListener('click', async () => {
        const agentId = agentIdInput.value.trim();
        const sql = sqlQueryInput.value.trim();

        if (!agentId || !sql) {
            showError("Agent ID and SQL Query cannot be empty.");
            return;
        }

        // Reset UI state
        setLoading(true);
        hideError();
        
        try {
            const response = await fetch('http://localhost:8000/query', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    agent_id: agentId,
                    sql: sql
                })
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.detail || "An unknown error occurred.");
            }

            renderSuccess(data);

        } catch (err) {
            showError(err.message);
            hideSuccess();
        } finally {
            setLoading(false);
        }
    });

    function setLoading(isLoading) {
        if (isLoading) {
            runBtn.disabled = true;
            runBtn.innerHTML = `
                <svg class="spinner" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="animation: spin 1s linear infinite;">
                    <circle cx="12" cy="12" r="10" stroke-dasharray="31.4 31.4" stroke-dashoffset="0"></circle>
                </svg>
                Executing...
            `;
        } else {
            runBtn.disabled = false;
            runBtn.innerHTML = `
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="5 3 19 12 5 21 5 3"></polygon></svg>
                Execute Query
            `;
        }
    }

    function showError(message) {
        errorMsg.textContent = message;
        errorBox.classList.remove('hidden');
    }

    function hideError() {
        errorBox.classList.add('hidden');
    }

    function hideSuccess() {
        emptyState.classList.remove('hidden');
        securityMetrics.classList.add('hidden');
    }

    function renderSuccess(data) {
        emptyState.classList.add('hidden');
        securityMetrics.classList.remove('hidden');

        // Render masked tags
        maskedTags.innerHTML = '';
        if (data.masked_columns && data.masked_columns.length > 0) {
            data.masked_columns.forEach(col => {
                const span = document.createElement('span');
                span.className = 'tag';
                span.textContent = col;
                maskedTags.appendChild(span);
            });
        } else {
            const span = document.createElement('span');
            span.className = 'tag safe';
            span.textContent = 'None';
            maskedTags.appendChild(span);
        }

        // Render rewritten SQL
        rewrittenSql.textContent = data.rewritten_sql;

        // Render Table
        tableHead.innerHTML = '';
        tableBody.innerHTML = '';

        if (data.rows && data.rows.length > 0) {
            // Since proxy.py returns list of tuples, we don't have column names easily accessible in rows 
            // unless we parse them or the backend provides them. For now, we just index them.
            const colCount = data.rows[0].length;
            
            for (let i = 0; i < colCount; i++) {
                const th = document.createElement('th');
                th.textContent = `Col ${i + 1}`;
                tableHead.appendChild(th);
            }

            data.rows.forEach(row => {
                const tr = document.createElement('tr');
                row.forEach(cell => {
                    const td = document.createElement('td');
                    td.textContent = cell !== null ? cell : 'NULL';
                    tr.appendChild(td);
                });
                tableBody.appendChild(tr);
            });
        } else {
            const tr = document.createElement('tr');
            const td = document.createElement('td');
            td.textContent = 'No rows returned.';
            tr.appendChild(td);
            tableBody.appendChild(tr);
        }
    }
});

// CSS animation dynamically added for spinner
const style = document.createElement('style');
style.textContent = `
    @keyframes spin {
        100% { transform: rotate(360deg); }
    }
`;
document.head.appendChild(style);

/**
 * API通信モジュール
 * FastAPIエンドポイントとの通信を担当
 */

class API {
    constructor(baseURL = 'http://localhost:8000') {
        this.baseURL = baseURL;
    }

    /**
     * ベースURLを設定
     */
    setBaseURL(url) {
        this.baseURL = url;
    }

    /**
     * ヘルスチェック
     */
    async checkHealth() {
        try {
            const response = await fetch(`${this.baseURL}/health`, {
                method: 'GET',
                mode: 'cors',
                cache: 'no-cache'
            });
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            const data = await response.json();
            return { success: true, data };
        } catch (error) {
            // CORSエラーやネットワークエラーの詳細を取得
            let errorMessage = error.message;
            if (error.message.includes('Failed to fetch') || error.message.includes('NetworkError')) {
                errorMessage = `APIサーバーに接続できません。\n\n考えられる原因:\n1. APIサーバーが起動していない\n2. ローカルファイルから開いている場合、CORSエラーが発生する可能性があります\n\n解決方法:\n1. APIサーバーを起動: python run_api_server.py\n2. ローカルWebサーバーを使用: cd gui && python -m http.server 8080\n3. ブラウザで http://localhost:8080 にアクセス`;
            }
            return { success: false, error: errorMessage };
        }
    }

    /**
     * リサーチを開始
     */
    /**
     * リサーチを開始
     * @param {string} theme - 調査テーマ
     * @param {number} maxIterations - 最大イテレーション数
     * @param {boolean} enableHumanIntervention - 人間介入を有効にするか
     * @param {string} [previousReportsContext] - 同一チャット内の既存調査レポート（考慮して計画を作成する場合）
     */
    async createResearch(theme, maxIterations = 5, enableHumanIntervention = false, previousReportsContext = null) {
        try {
            const body = {
                theme,
                max_iterations: maxIterations,
                enable_human_intervention: enableHumanIntervention,
                checkpointer_type: 'memory'
            };
            if (previousReportsContext && previousReportsContext.trim()) {
                body.previous_reports_context = previousReportsContext.trim();
            }
            const response = await fetch(`${this.baseURL}/research`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                mode: 'cors',
                body: JSON.stringify(body)
            });

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
            }

            const data = await response.json();
            return { success: true, data };
        } catch (error) {
            return { success: false, error: error.message };
        }
    }

    /**
     * 永続化済みリサーチの履歴一覧を取得（サーバー再起動後の復元用）
     */
    async getResearchHistory() {
        try {
            const response = await fetch(`${this.baseURL}/research/history`, {
                method: 'GET',
                mode: 'cors',
                cache: 'no-cache'
            });
            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
            }
            const data = await response.json();
            return { success: true, items: data.items || [] };
        } catch (error) {
            return { success: false, items: [], error: error.message };
        }
    }

    /**
     * リサーチ結果を取得
     */
    async getResearch(researchId) {
        try {
            const response = await fetch(`${this.baseURL}/research/${researchId}`, {
                method: 'GET',
                mode: 'cors',
                cache: 'no-cache'
            });

            if (response.status === 422) {
                // 処理中の場合はnullを返す
                return { success: true, data: null, processing: true };
            }

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                const msg = (errorData.detail && errorData.detail.message) || errorData.detail || `HTTP error! status: ${response.status}`;
                const err = typeof msg === 'string' ? msg : (msg.message || JSON.stringify(msg));
                return { success: false, error: err, notFound: response.status === 404 };
            }

            const data = await response.json();
            return { success: true, data, processing: false };
        } catch (error) {
            return { success: false, error: error.message, notFound: false };
        }
    }

    /**
     * リサーチのステータスを取得
     */
    async getResearchStatus(researchId) {
        try {
            const response = await fetch(`${this.baseURL}/research/${researchId}/status`, {
                method: 'GET',
                mode: 'cors',
                cache: 'no-cache'
            });

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
            }

            const data = await response.json();
            return { success: true, data };
        } catch (error) {
            return { success: false, error: error.message };
        }
    }

    /**
     * 中断されたリサーチを再開
     * @param {string} researchId - リサーチID
     * @param {string} humanInput - 人間からの入力（調査開始では任意、再計画では指示に使用）
     * @param {string} action - "resume"=調査再開, "replan"=計画再作成して再度HumanInLoop
     */
    async resumeResearch(researchId, humanInput, action = 'resume') {
        try {
            const response = await fetch(`${this.baseURL}/research/${researchId}/resume`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                mode: 'cors',
                body: JSON.stringify({
                    human_input: humanInput || '',
                    action: action || 'resume'
                })
            });

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
            }

            const data = await response.json();
            return { success: true, data };
        } catch (error) {
            return { success: false, error: error.message };
        }
    }

    /**
     * リサーチを削除
     */
    async deleteResearch(researchId) {
        try {
            const response = await fetch(`${this.baseURL}/research/${researchId}`, {
                method: 'DELETE',
                mode: 'cors'
            });

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
            }

            const data = await response.json();
            return { success: true, data };
        } catch (error) {
            return { success: false, error: error.message };
        }
    }

    /**
     * Content-Disposition ヘッダーからファイル名を取得（RFC 5987 filename*=UTF-8'' 対応）
     */
    _parseContentDispositionFilename(header) {
        if (!header) return null;
        const utf8Match = header.match(/filename\*=UTF-8''([^;\s]+)/i);
        if (utf8Match && utf8Match[1]) {
            try {
                return decodeURIComponent(utf8Match[1].replace(/"/g, ''));
            } catch (_) {
                // ignore
            }
        }
        const asciiMatch = header.match(/filename="([^"]*)"/);
        return asciiMatch ? asciiMatch[1].trim() : null;
    }

    /**
     * 参照ソースからPDFを生成
     */
    async generateSourcePdf(source, theme = '参照ソース') {
        try {
            const response = await fetch(`${this.baseURL}/source/pdf`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                mode: 'cors',
                body: JSON.stringify({
                    ...source,
                    theme: theme
                })
            });

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
            }

            const contentType = response.headers.get('Content-Type') || '';
            if (contentType.includes('application/json')) {
                const data = await response.json();
                return { success: true, saved: !!data.saved, path: data.path };
            }
            const blob = await response.blob();
            const contentDisposition = response.headers.get('Content-Disposition');
            const filename = this._parseContentDispositionFilename(contentDisposition);
            return { success: true, blob, filename };
        } catch (error) {
            return { success: false, error: error.message };
        }
    }

    /**
     * レポートMarkdownをサーバー側のダウンロード保存先に保存する（DOWNLOAD_SAVE_DIR が設定されている場合のみ）
     */
    async exportReport(researchId, content, filename) {
        try {
            const response = await fetch(`${this.baseURL}/research/export-report`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                mode: 'cors',
                body: JSON.stringify({
                    research_id: researchId,
                    content: content,
                    filename: filename || ''
                })
            });
            const data = await response.json().catch(() => ({}));
            if (!response.ok) {
                return { success: false, saved: false, error: data.detail || response.status };
            }
            return { success: true, saved: !!data.saved, path: data.path };
        } catch (error) {
            return { success: false, saved: false, error: error.message };
        }
    }
}

// グローバルAPIインスタンス
const api = new API();

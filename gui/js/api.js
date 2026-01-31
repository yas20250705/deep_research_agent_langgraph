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
    async createResearch(theme, maxIterations = 5, enableHumanIntervention = false) {
        try {
            const response = await fetch(`${this.baseURL}/research`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                mode: 'cors',
                body: JSON.stringify({
                    theme,
                    max_iterations: maxIterations,
                    enable_human_intervention: enableHumanIntervention,
                    checkpointer_type: 'memory'
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
                throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
            }

            const data = await response.json();
            return { success: true, data, processing: false };
        } catch (error) {
            return { success: false, error: error.message };
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
     */
    async resumeResearch(researchId, humanInput) {
        try {
            const response = await fetch(`${this.baseURL}/research/${researchId}/resume`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                mode: 'cors',
                body: JSON.stringify({
                    human_input: humanInput
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

            const blob = await response.blob();
            const contentDisposition = response.headers.get('Content-Disposition');
            const filename = this._parseContentDispositionFilename(contentDisposition);
            return { success: true, blob, filename };
        } catch (error) {
            return { success: false, error: error.message };
        }
    }
}

// グローバルAPIインスタンス
const api = new API();

(function () {
    "use strict";

    const BASE_URL = "/api";

    async function request(path, options = {}) {
        const url = `${BASE_URL}${path.startsWith("/") ? path : `/${path}`}`;
        let response;
        try {
            response = await fetch(url, {
                ...options,
                headers: { "Content-Type": "application/json", ...(options.headers || {}) },
            });
        } catch (error) {
            throw new Error("Không thể kết nối máy chủ. Hãy kiểm tra ứng dụng đang chạy và thử lại.");
        }

        let payload = null;
        if (response.status !== 204) {
            const text = await response.text();
            if (text) {
                try { payload = JSON.parse(text); }
                catch (_) { payload = { detail: text }; }
            }
        }
        if (!response.ok) {
            const detail = payload?.detail;
            const message = Array.isArray(detail)
                ? detail.map((item) => item.msg).join(", ")
                : detail || `Yêu cầu thất bại (HTTP ${response.status}).`;
            const error = new Error(message);
            error.status = response.status;
            throw error;
        }
        return payload;
    }

    window.api = {
        apiGet: (path) => request(path),
        apiPost: (path, data) => request(path, { method: "POST", body: JSON.stringify(data) }),
        apiPut: (path, data) => request(path, { method: "PUT", body: JSON.stringify(data) }),
        apiDelete: (path) => request(path, { method: "DELETE" }),
    };
})();


(function () {
    "use strict";

    const pages = {
        dashboard: "Tổng quan",
        vocabulary: "Từ vựng HSK1",
        flashcard: "Flashcard",
        matching: "Nối từ",
        sentences: "Luyện câu",
        progress: "Tiến độ",
    };
    let cleanupCurrentPage = null;
    let navigationOptions = {};

    const statusLabels = {
        new: "Chưa học", learning: "Đang học", review: "Cần ôn", mastered: "Đã thuộc",
    };

    function escapeHTML(value = "") {
        return String(value).replace(/[&<>'"]/g, (character) => ({
            "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;",
        })[character]);
    }

    function formatDate(value, includeTime = true) {
        if (!value) return "Chưa hoàn tất";
        const date = new Date(value);
        if (Number.isNaN(date.getTime())) return value;
        return new Intl.DateTimeFormat("vi-VN", {
            day: "2-digit", month: "2-digit", year: "numeric",
            ...(includeTime ? { hour: "2-digit", minute: "2-digit" } : {}),
        }).format(date);
    }

    function showToast(message, type = "success") {
        const region = document.getElementById("toast-region");
        const toast = document.createElement("div");
        toast.className = `toast ${type}`;
        toast.textContent = message;
        region.appendChild(toast);
        window.setTimeout(() => toast.remove(), 3200);
    }

    function renderError(container, message, retry) {
        container.innerHTML = `<div class="state-card"><div><span>!</span><h3>Không tải được dữ liệu</h3><p>${escapeHTML(message)}</p><button class="button button-primary" type="button">Thử lại</button></div></div>`;
        container.querySelector("button").addEventListener("click", retry);
    }

    function setButtonLoading(button, loading, label = "Đang xử lý...") {
        if (loading) {
            button.dataset.originalLabel = button.innerHTML;
            button.disabled = true;
            button.textContent = label;
        } else {
            button.disabled = false;
            if (button.dataset.originalLabel) button.innerHTML = button.dataset.originalLabel;
        }
    }

    async function loadPage(pageName) {
        const page = pages[pageName] ? pageName : "dashboard";
        if (cleanupCurrentPage) {
            cleanupCurrentPage();
            cleanupCurrentPage = null;
        }
        document.querySelectorAll(".main-nav a").forEach((link) => {
            link.classList.toggle("active", link.dataset.page === page);
        });
        document.getElementById("page-title").textContent = pages[page];
        document.title = `${pages[page]} · Chinese Study`;
        const content = document.getElementById("page-content");
        content.innerHTML = '<div class="page-loading"><span class="spinner"></span><p>Đang mở trang...</p></div>';
        closeSidebar();
        try {
            const response = await fetch(`/frontend/pages/${page}.html`);
            if (!response.ok) throw new Error(`Không thể tải giao diện (HTTP ${response.status}).`);
            content.innerHTML = await response.text();
            content.focus({ preventScroll: true });
            const controller = window.PageControllers?.[page];
            if (controller) cleanupCurrentPage = (await controller(navigationOptions)) || null;
            navigationOptions = {};
        } catch (error) {
            renderError(content, error.message, () => loadPage(page));
        }
    }

    function currentPageFromHash() {
        return window.location.hash.replace(/^#/, "").split("?")[0] || "dashboard";
    }

    function navigateTo(page, options = {}) {
        navigationOptions = options;
        if (currentPageFromHash() === page) loadPage(page);
        else window.location.hash = page;
    }

    function closeSidebar() {
        document.getElementById("sidebar").classList.remove("open");
        document.getElementById("sidebar-overlay").classList.remove("open");
    }

    window.PageControllers = window.PageControllers || {};
    window.App = { escapeHTML, formatDate, showToast, renderError, setButtonLoading, statusLabels };
    window.navigateTo = navigateTo;

    document.getElementById("menu-toggle").addEventListener("click", () => {
        document.getElementById("sidebar").classList.toggle("open");
        document.getElementById("sidebar-overlay").classList.toggle("open");
    });
    document.getElementById("sidebar-overlay").addEventListener("click", closeSidebar);
    window.addEventListener("hashchange", () => loadPage(currentPageFromHash()));
    loadPage(currentPageFromHash());
})();

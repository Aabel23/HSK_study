(function () {
    "use strict";

    window.PageControllers = window.PageControllers || {};
    window.PageControllers.matching = async function (options = {}) {
        let session = null;
        let selectedLeft = null;
        let selectedRight = null;
        let correctAttempts = 0;
        let incorrectAttempts = 0;
        let resolving = false;
        let startedAt = null;
        let elapsedSeconds = 0;
        let timerId = null;
        const setup = document.getElementById("matching-setup");
        const sessionView = document.getElementById("matching-session");
        const resultView = document.getElementById("matching-result");
        const liveStats = document.getElementById("matching-live-stats");
        const state = document.getElementById("matching-state");
        const startButton = document.getElementById("start-matching");

        startButton.addEventListener("click", startSession);
        document.getElementById("restart-matching").addEventListener("click", startSession);
        document.getElementById("change-mode").addEventListener("click", () => {
            resultView.hidden = true; setup.hidden = false; liveStats.hidden = true;
        });
        document.querySelectorAll("[data-go-dashboard]").forEach((button) => button.addEventListener("click", () => window.navigateTo("dashboard")));

        async function startSession() {
            clearTimer();
            selectedLeft = null; selectedRight = null; correctAttempts = 0; incorrectAttempts = 0; resolving = false;
            setup.hidden = true; sessionView.hidden = true; resultView.hidden = true; liveStats.hidden = true; state.hidden = false;
            state.innerHTML = '<div class="page-loading"><span class="spinner"></span><p>Đang xáo trộn các cặp từ...</p></div>';
            window.App.setButtonLoading(startButton, true, "Đang tạo vòng...");
            const mode = document.querySelector('input[name="matching-mode"]:checked').value;
            try {
                session = await window.api.apiPost("/matching/session", { mode, count: 6 });
                renderBoard();
                state.hidden = true; sessionView.hidden = false; liveStats.hidden = false;
                startedAt = Date.now(); elapsedSeconds = 0; updateLiveStats();
                timerId = window.setInterval(updateTimer, 1000);
            } catch (error) {
                window.App.renderError(state, error.message, startSession);
                setup.hidden = false;
            } finally { window.App.setButtonLoading(startButton, false); }
        }

        function renderBoard() {
            document.getElementById("right-label").textContent = session.mode === "meaning" ? "Nghĩa tiếng Việt" : "Pinyin";
            const makeButton = (item, side) => `<button class="match-item ${side}" data-id="${item.vocabulary_id}" type="button">${window.App.escapeHTML(item.text)}</button>`;
            const left = document.getElementById("left-column");
            const right = document.getElementById("right-column");
            left.innerHTML = session.left_items.map((item) => makeButton(item, "left")).join("");
            right.innerHTML = session.right_items.map((item) => makeButton(item, "right")).join("");
            left.querySelectorAll("button").forEach((button) => button.addEventListener("click", () => selectItem("left", button)));
            right.querySelectorAll("button").forEach((button) => button.addEventListener("click", () => selectItem("right", button)));
        }

        function selectItem(side, button) {
            if (resolving || button.disabled || button.classList.contains("correct")) return;
            const current = side === "left" ? selectedLeft : selectedRight;
            if (current) current.classList.remove("selected");
            button.classList.add("selected");
            if (side === "left") selectedLeft = button; else selectedRight = button;
            if (selectedLeft && selectedRight) resolvePair();
        }

        async function resolvePair() {
            resolving = true;
            const left = selectedLeft;
            const right = selectedRight;
            const isCorrect = left.dataset.id === right.dataset.id;
            try {
                await window.api.apiPost("/matching/attempt", {
                    session_id: session.session_id,
                    vocabulary_id: Number(left.dataset.id),
                    mode: session.mode,
                    is_correct: isCorrect,
                });
                if (isCorrect) {
                    correctAttempts += 1;
                    [left, right].forEach((item) => { item.classList.remove("selected"); item.classList.add("correct"); item.disabled = true; });
                    selectedLeft = null; selectedRight = null; resolving = false; updateLiveStats();
                    if (correctAttempts === session.left_items.length) await finishSession();
                } else {
                    incorrectAttempts += 1; updateLiveStats();
                    [left, right].forEach((item) => { item.classList.remove("selected"); item.classList.add("wrong"); });
                    window.setTimeout(() => {
                        [left, right].forEach((item) => item.classList.remove("wrong"));
                        selectedLeft = null; selectedRight = null; resolving = false;
                    }, 620);
                }
            } catch (error) {
                window.App.showToast(error.message, "error");
                [left, right].forEach((item) => item.classList.remove("selected"));
                selectedLeft = null; selectedRight = null; resolving = false;
            }
        }

        function updateTimer() {
            elapsedSeconds = Math.floor((Date.now() - startedAt) / 1000);
            document.getElementById("matching-timer").textContent = formatTime(elapsedSeconds);
        }
        function updateLiveStats() {
            document.getElementById("matching-correct").textContent = correctAttempts;
            document.getElementById("matching-incorrect").textContent = incorrectAttempts;
            document.getElementById("matching-timer").textContent = formatTime(elapsedSeconds);
        }
        function formatTime(seconds) {
            return `${String(Math.floor(seconds / 60)).padStart(2, "0")}:${String(seconds % 60).padStart(2, "0")}`;
        }
        function clearTimer() { if (timerId) { window.clearInterval(timerId); timerId = null; } }

        async function finishSession() {
            clearTimer(); updateTimer();
            try {
                await window.api.apiPost(`/matching/session/${session.session_id}/complete`, {
                    total_items: session.left_items.length,
                    correct_items: correctAttempts,
                    incorrect_items: incorrectAttempts,
                });
            } catch (error) {
                sessionView.hidden = true;
                state.hidden = false;
                window.App.renderError(state, `Chưa thể lưu tổng kết: ${error.message}`, finishSession);
                resolving = false;
                return;
            }
            const attempts = correctAttempts + incorrectAttempts;
            const accuracy = attempts ? Math.round(correctAttempts / attempts * 100) : 0;
            state.hidden = true; sessionView.hidden = true; liveStats.hidden = true; resultView.hidden = false;
            document.getElementById("matching-result-stats").innerHTML = `
                <div><strong>${session.left_items.length}</strong><small>Tổng số cặp</small></div>
                <div><strong>${correctAttempts}</strong><small>Lần chọn đúng</small></div>
                <div><strong>${incorrectAttempts}</strong><small>Lần chọn sai</small></div>
                <div><strong>${accuracy}%</strong><small>Độ chính xác</small></div>
                <div><strong>${formatTime(elapsedSeconds)}</strong><small>Thời gian</small></div>`;
        }

        if (options.autoStart) await startSession();
        return clearTimer;
    };
})();

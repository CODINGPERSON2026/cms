/**
 * Notify — Unified Centered Modal Card Notification System
 * Used across the entire software for success, error, warning, and info popups.
 * Automatically intercepts standard browser alert() calls.
 *
 * Usage:
 *   Notify.success("Item saved successfully!");
 *   Notify.error("Failed to update record.");
 *   Notify.warning("Please verify all fields.");
 *   Notify.info("System notification.");
 */
(function () {
    const STYLE_ID = "notify-card-modal-styles";
    const OVERLAY_ID = "notify-card-overlay";

    const CONFIG = {
        success: { icon: "fa-solid fa-circle-check", color: "#10b981", bg: "rgba(16, 185, 129, 0.12)", title: "Success" },
        error: { icon: "fa-solid fa-circle-exclamation", color: "#ef4444", bg: "rgba(239, 68, 68, 0.12)", title: "Error" },
        warning: { icon: "fa-solid fa-triangle-exclamation", color: "#f59e0b", bg: "rgba(245, 158, 11, 0.12)", title: "Warning" },
        info: { icon: "fa-solid fa-circle-info", color: "#2563eb", bg: "rgba(37, 99, 235, 0.12)", title: "Notice" }
    };

    function injectStyles() {
        if (document.getElementById(STYLE_ID)) return;

        const style = document.createElement("style");
        style.id = STYLE_ID;
        style.textContent = `
            #${OVERLAY_ID} {
                position: fixed;
                top: 0;
                left: 0;
                width: 100vw;
                height: 100vh;
                background: rgba(15, 23, 42, 0.5);
                backdrop-filter: blur(6px);
                -webkit-backdrop-filter: blur(6px);
                z-index: 9999999;
                display: flex;
                align-items: center;
                justify-content: center;
                padding: 20px;
                opacity: 0;
                pointer-events: none;
                transition: opacity 0.25s ease;
            }

            #${OVERLAY_ID}.active {
                opacity: 1;
                pointer-events: auto;
            }

            .notify-card-box {
                background: #ffffff;
                border: 1px solid #e2e8f0;
                border-radius: 20px;
                width: 100%;
                max-width: 400px;
                padding: 32px 28px 24px;
                text-align: center;
                box-shadow: 0 25px 50px -12px rgba(15, 23, 42, 0.25), 0 0 0 1px rgba(0,0,0,0.03);
                transform: scale(0.9) translateY(12px);
                transition: transform 0.25s cubic-bezier(0.16, 1, 0.3, 1);
            }

            #${OVERLAY_ID}.active .notify-card-box {
                transform: scale(1) translateY(0);
            }

            .notify-card-icon-frame {
                width: 68px;
                height: 68px;
                margin: 0 auto 20px;
                border-radius: 50%;
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 2.2rem;
                animation: popCardIcon 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);
            }

            @keyframes popCardIcon {
                0% { transform: scale(0.5); opacity: 0; }
                100% { transform: scale(1); opacity: 1; }
            }

            .notify-card-title {
                font-size: 1.3rem;
                font-weight: 700;
                color: #0f172a;
                margin-bottom: 8px;
                letter-spacing: -0.3px;
            }

            .notify-card-msg {
                font-size: 0.92rem;
                color: #475569;
                line-height: 1.5;
                margin-bottom: 26px;
                word-break: break-word;
            }

            .notify-card-btn {
                width: 100%;
                height: 46px;
                border: none;
                border-radius: 12px;
                font-size: 0.95rem;
                font-weight: 600;
                color: #ffffff;
                background: #2563eb;
                cursor: pointer;
                box-shadow: 0 4px 14px rgba(37, 99, 235, 0.2);
                transition: all 0.2s ease;
            }

            .notify-card-btn:hover {
                transform: translateY(-1px);
                box-shadow: 0 6px 18px rgba(37, 99, 235, 0.3);
            }

            .notify-card-btn:active {
                transform: translateY(0);
            }
        `;
        document.head.appendChild(style);
    }

    function createOverlay() {
        let overlay = document.getElementById(OVERLAY_ID);
        if (!overlay) {
            overlay = document.createElement("div");
            overlay.id = OVERLAY_ID;
            overlay.innerHTML = `
                <div class="notify-card-box">
                    <div class="notify-card-icon-frame" id="notifyCardIconFrame">
                        <i id="notifyCardIcon"></i>
                    </div>
                    <h3 class="notify-card-title" id="notifyCardTitle">Notice</h3>
                    <p class="notify-card-msg" id="notifyCardMsg"></p>
                    <button type="button" class="notify-card-btn" id="notifyCardBtn">OK</button>
                </div>
            `;
            document.body.appendChild(overlay);
        }
        return overlay;
    }

    function showCardModal(type, message, options) {
        injectStyles();
        const overlay = createOverlay();

        const conf = CONFIG[type] || CONFIG.info;
        const opts = Object.assign({
            title: conf.title,
            btnText: "OK",
            onClose: null
        }, options || {});

        const iconFrame = document.getElementById("notifyCardIconFrame");
        const iconElem = document.getElementById("notifyCardIcon");
        const titleElem = document.getElementById("notifyCardTitle");
        const msgElem = document.getElementById("notifyCardMsg");
        const btnElem = document.getElementById("notifyCardBtn");

        iconFrame.style.background = conf.bg;
        iconFrame.style.color = conf.color;
        iconElem.className = conf.icon;

        btnElem.style.background = conf.color;
        btnElem.style.boxShadow = `0 4px 14px ${conf.bg}`;

        titleElem.textContent = opts.title;
        msgElem.textContent = message || "";
        btnElem.textContent = opts.btnText;

        function dismiss() {
            overlay.classList.remove("active");
            if (typeof opts.onClose === "function") {
                opts.onClose();
            }
        }

        btnElem.onclick = dismiss;
        overlay.onclick = function(e) {
            if (e.target === overlay) dismiss();
        };

        // Keypress ESC or Enter dismisses
        const keyHandler = function(e) {
            if (e.key === "Escape" || e.key === "Enter") {
                document.removeEventListener("keydown", keyHandler);
                dismiss();
            }
        };
        document.addEventListener("keydown", keyHandler);

        requestAnimationFrame(() => {
            overlay.classList.add("active");
            btnElem.focus();
        });
    }

    // Global Export
    window.Notify = {
        success: (message, options) => showCardModal("success", message, options),
        error: (message, options) => showCardModal("error", message, options),
        warning: (message, options) => showCardModal("warning", message, options),
        info: (message, options) => showCardModal("info", message, options),
        alert: (message, options) => showCardModal("info", message, options)
    };

    // Global Override for window.alert so ALL browser alerts across the software use this single card modal
    const _originalAlert = window.alert;
    window.alert = function (message) {
        if (!message) return;
        const msgStr = String(message).toLowerCase();

        if (msgStr.includes("success") || msgStr.includes("saved") || msgStr.includes("updated") || msgStr.includes("added") || msgStr.includes("created")) {
            window.Notify.success(message);
        } else if (msgStr.includes("fail") || msgStr.includes("error") || msgStr.includes("invalid") || msgStr.includes("required") || msgStr.includes("incorrect")) {
            window.Notify.error(message);
        } else {
            window.Notify.info(message);
        }
    };

    // Auto-convert any inline banner alerts (.alert-success / .alert-danger) into centered card popup modals
    document.addEventListener("DOMContentLoaded", function() {
        setTimeout(() => {
            document.querySelectorAll(".alert-success, .alert.alert-success").forEach(el => {
                const text = el.innerText.replace(/[\n\r]+/g, ' ').trim();
                if (text && el.offsetWidth > 0 && el.offsetHeight > 0) {
                    el.style.display = "none";
                    window.Notify.success(text, { title: "Success" });
                }
            });
            document.querySelectorAll(".alert-danger, .alert.alert-danger").forEach(el => {
                const text = el.innerText.replace(/[\n\r]+/g, ' ').trim();
                if (text && el.offsetWidth > 0 && el.offsetHeight > 0) {
                    el.style.display = "none";
                    window.Notify.error(text, { title: "Error" });
                }
            });
        }, 100);
    });
})();

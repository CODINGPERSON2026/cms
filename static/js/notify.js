/**
 * Notify — lightweight toast popup module
 * Usage:
 *   Notify.success("Item recorded successfully.");
 *   Notify.error("Failed to save item.");
 *   Notify.info("Heads up...");
 *   Notify.warning("Check this field.");
 *
 * Include once in base.html:
 *   <script src="{{ url_for('static', filename='js/notify.js') }}"></script>
 */
(function () {
    const STYLE_ID = "notify-module-styles";
    const CONTAINER_ID = "notify-container";
    const DEFAULT_DURATION = 4000;

    const ICONS = {
        success: "fa-solid fa-circle-check",
        error: "fa-solid fa-circle-xmark",
        warning: "fa-solid fa-triangle-exclamation",
        info: "fa-solid fa-circle-info"
    };

    function injectStyles() {
        if (document.getElementById(STYLE_ID)) return;

        const style = document.createElement("style");
        style.id = STYLE_ID;
        style.textContent = `
            #${CONTAINER_ID} {
                position: fixed;
                top: 22px;
                right: 22px;
                z-index: 99999;
                display: flex;
                flex-direction: column;
                gap: 12px;
                max-width: 380px;
                pointer-events: none;
            }

            .notify-toast {
                display: flex;
                align-items: flex-start;
                gap: 12px;
                padding: 14px 16px;
                border-radius: 12px;
                background: var(--bg-surface, #1e1e1e);
                border: 1px solid var(--border-dim, rgba(255,255,255,0.1));
                box-shadow: 0 8px 28px rgba(0,0,0,0.28);
                pointer-events: auto;
                opacity: 0;
                transform: translateX(40px);
                transition: opacity 0.25s ease, transform 0.25s ease;
                position: relative;
                overflow: hidden;
            }

            .notify-toast.notify-show {
                opacity: 1;
                transform: translateX(0);
            }

            .notify-toast.notify-hide {
                opacity: 0;
                transform: translateX(40px);
            }

            .notify-icon {
                flex-shrink: 0;
                width: 30px;
                height: 30px;
                border-radius: 8px;
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 0.95rem;
                margin-top: 1px;
            }

            .notify-toast.notify-success .notify-icon {
                background: rgba(34, 197, 94, 0.15);
                color: #22c55e;
            }
            .notify-toast.notify-error .notify-icon {
                background: rgba(239, 68, 68, 0.15);
                color: var(--danger, #ef4444);
            }
            .notify-toast.notify-warning .notify-icon {
                background: rgba(245, 158, 11, 0.15);
                color: #f59e0b;
            }
            .notify-toast.notify-info .notify-icon {
                background: var(--accent-muted, rgba(59,130,246,0.15));
                color: var(--accent, #3b82f6);
            }

            .notify-content {
                flex: 1;
                min-width: 0;
            }

            .notify-title {
                font-size: 0.85rem;
                font-weight: 700;
                color: var(--text-primary, #fff);
                margin: 0 0 2px;
            }

            .notify-message {
                font-size: 0.8rem;
                color: var(--text-secondary, #aaa);
                margin: 0;
                line-height: 1.4;
                word-break: break-word;
            }

            .notify-close {
                flex-shrink: 0;
                background: transparent;
                border: none;
                color: var(--text-muted, #888);
                font-size: 0.85rem;
                cursor: pointer;
                padding: 2px;
                line-height: 1;
                border-radius: 4px;
                transition: color 0.2s;
            }

            .notify-close:hover {
                color: var(--text-primary, #fff);
            }

            .notify-progress {
                position: absolute;
                bottom: 0;
                left: 0;
                height: 3px;
                background: currentColor;
                opacity: 0.35;
                width: 100%;
                transform-origin: left;
            }

            .notify-toast.notify-success .notify-progress { color: #22c55e; }
            .notify-toast.notify-error .notify-progress { color: var(--danger, #ef4444); }
            .notify-toast.notify-warning .notify-progress { color: #f59e0b; }
            .notify-toast.notify-info .notify-progress { color: var(--accent, #3b82f6); }

            @keyframes notify-shrink {
                from { transform: scaleX(1); }
                to { transform: scaleX(0); }
            }

            @media (max-width: 576px) {
                #${CONTAINER_ID} {
                    top: 12px;
                    right: 12px;
                    left: 12px;
                    max-width: none;
                }
            }
        `;
        document.head.appendChild(style);
    }

    function getContainer() {
        let container = document.getElementById(CONTAINER_ID);
        if (!container) {
            container = document.createElement("div");
            container.id = CONTAINER_ID;
            document.body.appendChild(container);
        }
        return container;
    }

    function show(type, message, options) {
        injectStyles();
        const container = getContainer();
        const opts = Object.assign({
            title: type.charAt(0).toUpperCase() + type.slice(1),
            duration: DEFAULT_DURATION
        }, options || {});

        const toast = document.createElement("div");
        toast.className = `notify-toast notify-${type}`;
        toast.innerHTML = `
            <div class="notify-icon"><i class="${ICONS[type] || ICONS.info}"></i></div>
            <div class="notify-content">
                <p class="notify-title">${opts.title}</p>
                <p class="notify-message"></p>
            </div>
            <button type="button" class="notify-close" aria-label="Dismiss">
                <i class="fa-solid fa-xmark"></i>
            </button>
            <div class="notify-progress"></div>
        `;
        // Set message via textContent to avoid HTML injection from dynamic error strings
        toast.querySelector(".notify-message").textContent = message;

        container.appendChild(toast);
        requestAnimationFrame(() => toast.classList.add("notify-show"));

        const progressBar = toast.querySelector(".notify-progress");
        progressBar.style.animation = `notify-shrink ${opts.duration}ms linear forwards`;

        let dismissTimer = setTimeout(() => dismiss(toast), opts.duration);

        function dismiss(el) {
            clearTimeout(dismissTimer);
            el.classList.remove("notify-show");
            el.classList.add("notify-hide");
            setTimeout(() => el.remove(), 250);
        }

        toast.querySelector(".notify-close").addEventListener("click", () => dismiss(toast));
        toast.addEventListener("mouseenter", () => {
            clearTimeout(dismissTimer);
            progressBar.style.animationPlayState = "paused";
        });
        toast.addEventListener("mouseleave", () => {
            progressBar.style.animationPlayState = "running";
            dismissTimer = setTimeout(() => dismiss(toast), 1200);
        });

        return toast;
    }

    window.Notify = {
        success: (message, options) => show("success", message, options),
        error: (message, options) => show("error", message, options),
        warning: (message, options) => show("warning", message, options),
        info: (message, options) => show("info", message, options)
    };
})();
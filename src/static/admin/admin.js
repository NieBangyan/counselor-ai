let selectedAlert = null;
let selectedConversation = null;


// ============================================================
// Elements
// ============================================================


const alertList =
    document.getElementById("alertList");

const alertCount =
    document.getElementById("alertCount");

const refreshButton =
    document.getElementById("refreshButton");

const emptyConversation =
    document.getElementById("emptyConversation");

const conversationContent =
    document.getElementById("conversationContent");

const studentTitle =
    document.getElementById("studentTitle");

const riskBadge =
    document.getElementById("riskBadge");

const handoffBadge =
    document.getElementById("handoffBadge");

const acceptButton =
    document.getElementById("acceptButton");

const resolveButton =
    document.getElementById("resolveButton");

const messageList =
    document.getElementById("messageList");

const replyPanel =
    document.getElementById("replyPanel");

const replyInput =
    document.getElementById("replyInput");

const characterCount =
    document.getElementById("characterCount");

const sendButton =
    document.getElementById("sendButton");

const toast =
    document.getElementById("toast");


// ============================================================
// API
// ============================================================


async function apiRequest(
    url,
    options = {},
) {
    const fetchOptions = {
        ...options,
        headers: {
            ...(options.headers || {}),
        },
    };

    if (
        options.body !== undefined
        && !fetchOptions.headers[
            "Content-Type"
        ]
    ) {
        fetchOptions.headers[
            "Content-Type"
        ] = "application/json";
    }

    const response = await fetch(
        url,
        fetchOptions,
    );

    let data = null;

    try {
        data = await response.json();
    } catch {
        data = null;
    }

    if (!response.ok) {
        const detail =
            data?.detail
            || `HTTP ${response.status}`;

        throw new Error(detail);
    }

    return data;
}


// ============================================================
// Alerts
// ============================================================


async function loadAlerts() {
    alertList.innerHTML = `
        <div class="empty-state">
            正在加载告警……
        </div>
    `;

    try {
        const data = await apiRequest(
            "/admin/alerts",
        );

        const alerts =
            Array.isArray(data?.alerts)
                ? data.alerts
                : [];

        alertCount.textContent =
            `${alerts.length} 条处理中`;

        renderAlerts(alerts);

    } catch (error) {
        console.error(
            "loadAlerts failed:",
            error,
        );

        alertCount.textContent =
            "加载失败";

        alertList.innerHTML = `
            <div class="empty-state">
                告警加载失败
            </div>
        `;

        showToast(
            `加载失败：${error.message}`,
        );
    }
}


function renderAlerts(alerts) {
    alertList.innerHTML = "";

    if (!alerts.length) {
        alertList.innerHTML = `
            <div class="empty-state">
                当前没有处理中风险告警
            </div>
        `;

        return;
    }

    for (const alert of alerts) {
        const card =
            document.createElement("div");

        card.className =
            "alert-card";

        if (
            selectedAlert
            && selectedAlert.id === alert.id
        ) {
            card.classList.add(
                "active",
            );
        }

        const time =
            formatTime(
                alert.created_at,
            );

        const status =
            escapeHtml(
                alert.handoff_status
                || "UNKNOWN",
            );

        const message =
            escapeHtml(
                alert.message || "",
            );

        const riskLevel =
            escapeHtml(
                (
                    alert.risk_level
                    || "crisis"
                ).toUpperCase(),
            );

        card.innerHTML = `
            <div class="alert-card-header">
                <span class="alert-card-title">
                    高风险学生
                </span>

                <span class="badge danger">
                    ${riskLevel}
                </span>
            </div>

            <div class="alert-card-message">
                ${message}
            </div>

            <div class="alert-card-time">
                ${time} · ${status}
            </div>
        `;

        card.addEventListener(
            "click",
            () => {
                selectAlert(alert);
            },
        );

        alertList.appendChild(
            card
        );
    }
}


// ============================================================
// Select Alert
// ============================================================


async function selectAlert(alert) {
    selectedAlert = alert;

    emptyConversation
        .classList
        .add("hidden");

    conversationContent
        .classList
        .remove("hidden");

    studentTitle.textContent =
        `学生 ${shortId(
            alert.conversation_id
        )}`;

    riskBadge.textContent =
        (
            alert.risk_level
            || "crisis"
        ).toUpperCase();

    // 重新画左侧，
    // 让当前选中的卡片显示 active。
    const cards =
        alertList.querySelectorAll(
            ".alert-card"
        );

    cards.forEach(
        card => {
            card.classList.remove(
                "active"
            );
        }
    );

    await loadConversation(
        alert.conversation_id,
    );
}


// ============================================================
// Conversation
// ============================================================


async function loadConversation(
    conversationId,
) {
    try {
        const data = await apiRequest(
            `/admin/conversations/${
                encodeURIComponent(
                    conversationId
                )
            }`,
        );

        selectedConversation = data;

        renderConversation(data);

    } catch (error) {
        console.error(
            "loadConversation failed:",
            error,
        );

        showToast(
            `会话加载失败：${error.message}`,
        );
    }
}


function renderConversation(data) {
    const status =
        data.handoff_status || "AI";

    handoffBadge.textContent =
        status;

    handoffBadge.className =
        "badge";

    if (status === "HUMAN_PENDING") {
        handoffBadge
            .classList
            .add("pending");
    }

    if (status === "HUMAN_ACTIVE") {
        handoffBadge
            .classList
            .add("active");
    }

    if (status === "RESOLVED") {
        handoffBadge
            .classList
            .add("resolved");
    }

    updateActions(status);

    renderMessages(
        data.messages || [],
    );
}


function updateActions(status) {
    if (status === "HUMAN_PENDING") {
        acceptButton
            .classList
            .remove("hidden");

        resolveButton
            .classList
            .add("hidden");

        replyPanel
            .classList
            .add("hidden");

        return;
    }

    if (status === "HUMAN_ACTIVE") {
        acceptButton
            .classList
            .add("hidden");

        resolveButton
            .classList
            .remove("hidden");

        replyPanel
            .classList
            .remove("hidden");

        return;
    }

    acceptButton
        .classList
        .add("hidden");

    resolveButton
        .classList
        .add("hidden");

    replyPanel
        .classList
        .add("hidden");
}


function renderMessages(messages) {
    messageList.innerHTML = "";

    if (!messages.length) {
        messageList.innerHTML = `
            <div class="empty-state">
                暂无会话消息
            </div>
        `;

        return;
    }

    for (const item of messages) {
        const row =
            document.createElement("div");

        const role =
            item.role === "user"
                ? "user"
                : "assistant";

        row.className =
            `message-row ${role}`;

        const bubble =
            document.createElement("div");

        bubble.className =
            "message";

        const label =
            document.createElement("span");

        label.className =
            "message-label";

        label.textContent =
            role === "user"
                ? "学生"
                : "AI / 辅导员";

        const content =
            document.createElement("div");

        content.textContent =
            item.content || "";

        bubble.appendChild(
            label
        );

        bubble.appendChild(
            content
        );

        row.appendChild(
            bubble
        );

        messageList.appendChild(
            row
        );
    }

    messageList.scrollTop =
        messageList.scrollHeight;
}


// ============================================================
// Accept
// ============================================================


async function acceptConversation() {
    if (!selectedAlert) {
        return;
    }

    acceptButton.disabled = true;

    try {
        const data = await apiRequest(
            `/admin/alerts/${
                encodeURIComponent(
                    selectedAlert.id
                )
            }/accept`,
            {
                method: "POST",
            },
        );

        showToast(
            data?.already_accepted
                ? "该会话已由辅导员接入"
                : "已接入学生会话",
        );

        await loadConversation(
            selectedAlert.conversation_id,
        );

        await loadAlerts();

    } catch (error) {
        console.error(
            "accept failed:",
            error,
        );

        showToast(
            `接入失败：${error.message}`,
        );

    } finally {
        acceptButton.disabled = false;
    }
}


// ============================================================
// Send Human Message
// ============================================================


async function sendHumanMessage() {
    if (
        !selectedAlert
        || !selectedConversation
    ) {
        return;
    }

    const content =
        replyInput.value.trim();

    if (!content) {
        showToast(
            "请输入回复内容",
        );

        return;
    }

    sendButton.disabled = true;

    try {
        await apiRequest(
            `/admin/conversations/${
                encodeURIComponent(
                    selectedAlert.conversation_id
                )
            }/messages`,
            {
                method: "POST",
                body: JSON.stringify({
                    content,
                }),
            },
        );

        replyInput.value = "";

        updateCharacterCount();

        showToast(
            "消息已发送给学生",
        );

        await loadConversation(
            selectedAlert.conversation_id,
        );

    } catch (error) {
        console.error(
            "send failed:",
            error,
        );

        showToast(
            `发送失败：${error.message}`,
        );

    } finally {
        sendButton.disabled = false;
    }
}


// ============================================================
// Resolve
// ============================================================


async function resolveConversation() {
    if (!selectedAlert) {
        return;
    }

    const confirmed =
        window.confirm(
            "确认该风险事件已经处理完成？"
        );

    if (!confirmed) {
        return;
    }

    resolveButton.disabled = true;

    try {
        await apiRequest(
            `/admin/alerts/${
                encodeURIComponent(
                    selectedAlert.id
                )
            }/resolve`,
            {
                method: "POST",
            },
        );

        showToast(
            "风险事件已处理完成",
        );

        selectedAlert = null;
        selectedConversation = null;

        conversationContent
            .classList
            .add("hidden");

        emptyConversation
            .classList
            .remove("hidden");

        await loadAlerts();

    } catch (error) {
        console.error(
            "resolve failed:",
            error,
        );

        showToast(
            `处理失败：${error.message}`,
        );

    } finally {
        resolveButton.disabled = false;
    }
}


// ============================================================
// Utilities
// ============================================================


function updateCharacterCount() {
    if (
        !replyInput
        || !characterCount
    ) {
        return;
    }

    characterCount.textContent =
        `${replyInput.value.length} / 1800`;
}


function shortId(value) {
    if (!value) {
        return "未知";
    }

    if (value.length <= 12) {
        return value;
    }

    return (
        value.slice(0, 6)
        + "..."
        + value.slice(-4)
    );
}


function formatTime(value) {
    if (!value) {
        return "";
    }

    const date =
        new Date(value);

    if (
        Number.isNaN(
            date.getTime()
        )
    ) {
        return value;
    }

    return date.toLocaleString(
        "zh-CN",
        {
            hour12: false,
        },
    );
}


function escapeHtml(value) {
    const div =
        document.createElement("div");

    div.textContent =
        String(value ?? "");

    return div.innerHTML;
}


let toastTimer = null;


function showToast(message) {
    if (!toast) {
        console.log(
            "[TOAST]",
            message,
        );

        return;
    }

    toast.textContent =
        message;

    toast.classList.remove(
        "hidden",
    );

    if (toastTimer) {
        clearTimeout(
            toastTimer
        );
    }

    toastTimer = setTimeout(
        () => {
            toast.classList.add(
                "hidden",
            );
        },
        3000,
    );
}


// ============================================================
// Events
// ============================================================


refreshButton.addEventListener(
    "click",
    () => {
        loadAlerts();
    },
);


acceptButton.addEventListener(
    "click",
    () => {
        acceptConversation();
    },
);


resolveButton.addEventListener(
    "click",
    () => {
        resolveConversation();
    },
);


sendButton.addEventListener(
    "click",
    () => {
        sendHumanMessage();
    },
);


replyInput.addEventListener(
    "input",
    () => {
        updateCharacterCount();
    },
);


replyInput.addEventListener(
    "keydown",
    event => {
        if (
            event.key === "Enter"
            && (
                event.ctrlKey
                || event.metaKey
            )
        ) {
            event.preventDefault();

            sendHumanMessage();
        }
    },
);


// ============================================================
// Start
// ============================================================


console.log(
    "[ADMIN UI] initialized"
);

updateCharacterCount();

loadAlerts();
const ws = new WebSocket("ws://" + location.host + "/ws"); //websocket接続を作成
const immichCard = document.getElementById("immich-card");
const immichToggle = document.getElementById("immich-toggle");
const nextcloudCard = document.getElementById("nextcloud-card");
const nextcloudToggle = document.getElementById("nextcloud-toggle");
const storageCard = document.getElementById("storage-card");
const powerCard = document.getElementById("power-card");
const desktopHoverQuery = window.matchMedia("(hover: hover) and (pointer: fine)");

const severityClasses = [
    "severity-critical",
    "severity-warning",
    "severity-info",
    "severity-healthy",
    "severity-neutral",
];

function setSeverity(element, severityClass) {
    if (!element) {
        return;
    }
    element.classList.remove(...severityClasses);
    element.classList.add(severityClass);
}

function updateStorageCard(data) {
    const storageElement = document.getElementById("storage");
    if (!storageElement || !storageCard) {
        return;
    }

    const total = Number(data.total_gb) || 0;
    const used = Number(data.used_gb) || 0;
    const free = Number(data.free_gb) || 0;
    const usedPercent = total > 0 ? (used / total) * 100 : 0;

    storageElement.textContent =
        "ストレージ: " +
        "合計 " + total + "GB / " +
        "使用 " + used + "GB (" + usedPercent.toFixed(1) + "%) / " +
        "空き " + free + "GB";

    if (usedPercent >= 90) {
        setSeverity(storageCard, "severity-critical");
    } else if (usedPercent >= 80) {
        setSeverity(storageCard, "severity-warning");
    } else {
        setSeverity(storageCard, "severity-healthy");
    }
}

function updatePowerCard(data) {
    const powerElement = document.getElementById("power");
    if (!powerElement || !powerCard) {
        return;
    }

    if (data.ac_connected) {
        powerElement.textContent = "電源: AC接続中";
        setSeverity(powerCard, "severity-healthy");
    } else {
        powerElement.textContent = "電源: バッテリー駆動中";
        setSeverity(powerCard, "severity-critical");
    }
}

function setupExpandableCard(cardElement, toggleElement) {
    let isPinnedOpen = false;
    let isHovering = false;

    function syncDetailsState() {
        if (!cardElement || !toggleElement) {
            return;
        }

        const isOpen = isPinnedOpen || (desktopHoverQuery.matches && isHovering);

        cardElement.classList.toggle("expanded", isOpen);
        toggleElement.setAttribute("aria-expanded", isOpen ? "true" : "false");
    }

    if (cardElement && toggleElement) {
        toggleElement.addEventListener("click", function () {
            isPinnedOpen = !isPinnedOpen;
            syncDetailsState();
        });

        cardElement.addEventListener("pointerenter", function () {
            isHovering = true;
            syncDetailsState();
        });

        cardElement.addEventListener("pointerleave", function () {
            isHovering = false;
            syncDetailsState();
        });

        desktopHoverQuery.addEventListener("change", function () {
            if (!desktopHoverQuery.matches) {
                isHovering = false;
            }
            syncDetailsState();
        });

        syncDetailsState();
    }

    return {
        syncDetailsState,
    };
}

setupExpandableCard(immichCard, immichToggle);
setupExpandableCard(nextcloudCard, nextcloudToggle);

function updateVersionCard(prefix, data) {
    const statusElement = document.getElementById(prefix + "-status");
    const currentElement = document.getElementById(prefix + "-current");
    const latestElement = document.getElementById(prefix + "-latest");
    const cardElement = statusElement && statusElement.parentElement ? statusElement.parentElement.parentElement : null;

    if (!statusElement || !currentElement || !latestElement || !cardElement) {
        return;
    }

    currentElement.textContent =
        "現在: " + (data[prefix + "_current_version"] || "取得失敗");

    latestElement.textContent =
        "最新: " + (data[prefix + "_latest_version"] || "取得失敗");

    statusElement.classList.remove("status-error", "status-ok", "status-update");

    if (data[prefix + "_error"]) {
        statusElement.textContent =
            "❌ " + (prefix === "immich" ? "Immich" : "Nextcloud") + "バージョンAPI取得エラー: " + data[prefix + "_error"];
        statusElement.classList.add("status-error");
        setSeverity(cardElement, "severity-critical");
    } else if (data[prefix + "_current_version"] && data[prefix + "_latest_version"]) {
        if (data[prefix + "_current_version"] !== data[prefix + "_latest_version"]) {
            statusElement.textContent = (prefix === "immich" ? "Immich" : "Nextcloud") + ": 更新あり";
            statusElement.classList.add("status-update");
            setSeverity(cardElement, "severity-info");
        } else {
            statusElement.textContent = (prefix === "immich" ? "Immich" : "Nextcloud") + ": 最新";
            statusElement.classList.add("status-ok");
            setSeverity(cardElement, "severity-healthy");
        }
    } else {
        statusElement.textContent = (prefix === "immich" ? "Immich" : "Nextcloud") + ": バージョン判定待ち";
        setSeverity(cardElement, "severity-neutral");
    }
}

ws.onmessage = function (event) { //function () {...} という構成の郵便受けをws.onmessageとして作成しているイメージ。eventは手紙のイメージ
    const data = JSON.parse(event.data); //event中のjsonデータをjsのオブジェクトに変換する

    updateStorageCard(data);
    updatePowerCard(data);

    updateVersionCard("immich", data);
    updateVersionCard("nextcloud", data);

    const now = new Date();
    document.getElementById("last-updated").textContent =
        "最終更新: " + now.toLocaleString("ja-JP");
};

// ============================
// 概览页 - JS
// ============================

// ----- 通用工具 -----
function escapeHTML(str) {
    return str
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;");
}

function countDirs(nodes) {
    let count = 0;
    nodes.forEach(n => {
        count += 1;
        if (n.children) count += countDirs(n.children);
    });
    return count;
}

function countFiles(nodes) {
    let count = 0;
    nodes.forEach(n => {
        if (!n.children || n.children.length === 0) count += 1;
        if (n.children) count += countFiles(n.children);
    });
    return count;
}

// ----- 渲染学科分布表格 -----
function formatName(name) {
    const parts = name.split("_");
    return parts.length > 1 ? parts.slice(1).join(" ") : name;
}

function renderOverview(data, path, includeFiles) {
    document.getElementById("stat_dirs").textContent = countDirs(data);
    document.getElementById("stat_files").textContent = countFiles(data);
    document.getElementById("stat_top_level").textContent = data.length;
    document.getElementById("overview").style.display = "block";

    const tbody = document.getElementById("subject_table_body");
    let html = "";

    data.forEach((l1, l1i) => {
        const l1Name = formatName(l1.name);
        const hasL2 = l1.children && l1.children.length > 0;

        html += `<tr class="l1-row open" data-l1="${l1i}">
            <td>${escapeHTML(l1Name)}</td>
            <td class="num">${l1.paper_count}</td>
        </tr>`;

        if (hasL2) {
            l1.children.forEach((l2, l2i) => {
                const l2Name = formatName(l2.name);
                const hasL3 = l2.children && l2.children.length > 0;

                html += `<tr class="l2-row show" data-l1="${l1i}" data-l2="${l2i}">
                    <td>${escapeHTML(l2Name)}</td>
                    <td class="num">${l2.paper_count}</td>
                </tr>`;

                if (hasL3) {
                    l2.children.forEach((l3) => {
                        html += `<tr class="l3-row show" data-l1="${l1i}" data-l2="${l2i}">
                            <td>${escapeHTML(formatName(l3.name))}</td>
                            <td class="num">${l3.paper_count}</td>
                        </tr>`;
                    });
                }
            });
        }
    });

    tbody.innerHTML = html;

    // 点击一级行
    tbody.querySelectorAll("tr.l1-row").forEach(row => {
        row.addEventListener("click", function() {
            const l1 = this.dataset.l1;
            const isOpen = this.classList.contains("open");
            tbody.querySelectorAll(`tr[data-l1="${l1}"]`).forEach(r => {
                if (r !== this) r.classList.toggle("show", !isOpen);
            });
            this.classList.toggle("open", !isOpen);
        });
    });

    // 点击二级行
    tbody.querySelectorAll("tr.l2-row").forEach(row => {
        row.addEventListener("click", function() {
            const l1 = this.dataset.l1;
            const l2 = this.dataset.l2;
            const isOpen = this.classList.contains("show");
            tbody.querySelectorAll(`tr[data-l1="${l1}"][data-l2="${l2}"]`).forEach(r => {
                if (r !== this) r.classList.toggle("show", !isOpen);
            });
        });
    });

    document.getElementById("subject_overview").style.display = "block";
    sessionStorage.setItem("last_path", path);
    sessionStorage.setItem("last_include_files", String(includeFiles));
}

// ----- 初始化 -----
function init() {
    const pathInput = document.getElementById("path_input");
    const loadBtn = document.getElementById("load_btn");
    const includeFilesCheckbox = document.getElementById("include_files");
    const errorMsg = document.getElementById("error_msg");

    // 恢复上次路径
    const savedPath = sessionStorage.getItem("last_path");
    const savedInclude = sessionStorage.getItem("last_include_files");
    if (savedPath) {
        pathInput.value = savedPath;
        includeFilesCheckbox.checked = savedInclude === "true";
    }

    loadBtn.addEventListener("click", loadOverview);
    pathInput.addEventListener("keypress", (e) => { if (e.key === "Enter") loadOverview(); });

    async function loadOverview() {
        const path = pathInput.value.trim();
        if (!path) { showError("请输入目录路径"); return; }
        loadBtn.disabled = true;
        loadBtn.textContent = "加载中...";
        hideError();

        try {
            const data = await fetchTree(path, includeFilesCheckbox.checked);
            if (data.length === 0) { showError("目录为空或路径不存在"); return; }
            renderOverview(data, path, includeFilesCheckbox.checked);
        } catch (err) {
            showError(err.message);
        } finally {
            loadBtn.disabled = false;
            loadBtn.textContent = "加载";
        }
    }

    function showError(msg) {
        errorMsg.textContent = msg;
        errorMsg.style.display = "block";
    }

    function hideError() {
        errorMsg.style.display = "none";
    }
}

document.addEventListener("DOMContentLoaded", init);

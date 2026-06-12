const activeFolderInput = document.getElementById("active-folder");
const saveFolderBtn = document.getElementById("save-folder-btn");
const refreshBtn = document.getElementById("refresh-btn");
const filesHeading = document.getElementById("files-heading");
const filesBody = document.getElementById("files-body");
const filesTable = document.getElementById("files-table");
const filesEmpty = document.getElementById("files-empty");
const phoneQr = document.getElementById("phone-qr");
const phoneUrl = document.getElementById("phone-url");
const outlookDateFrom = document.getElementById("outlook-date-from");
const outlookDateTo = document.getElementById("outlook-date-to");
const outlookSubfolders = document.getElementById("outlook-subfolders");
const outlookRunBtn = document.getElementById("outlook-run-btn");
const outlookResult = document.getElementById("outlook-result");
const wixDateFrom = document.getElementById("wix-date-from");
const wixDateTo = document.getElementById("wix-date-to");
const wixForceLogin = document.getElementById("wix-force-login");
const wixRunBtn = document.getElementById("wix-run-btn");
const wixResult = document.getElementById("wix-result");
const wixNextInvoice = document.getElementById("wix-next-invoice");
const dropboxDateFrom = document.getElementById("dropbox-date-from");
const dropboxDateTo = document.getElementById("dropbox-date-to");
const dropboxForceLogin = document.getElementById("dropbox-force-login");
const dropboxRunBtn = document.getElementById("dropbox-run-btn");
const dropboxResult = document.getElementById("dropbox-result");
const toast = document.getElementById("toast");

function showToast(message) {
  toast.textContent = message;
  toast.classList.add("show");
  window.setTimeout(() => toast.classList.remove("show"), 2400);
}

function formatSize(bytes) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

function renderStatus(status) {
  const files = status.recent_files || [];
  if (filesHeading) filesHeading.textContent = `Files (${files.length})`;
  filesBody.innerHTML = "";
  filesEmpty.style.display = files.length ? "none" : "block";
  filesTable.style.display = files.length ? "table" : "none";

  files.forEach((file) => {
    const row = document.createElement("tr");
    row.innerHTML = `
      <td title="${file.path}">${file.name}</td>
      <td>${file.extension || "-"}</td>
      <td>${formatSize(file.size)}</td>
      <td>${file.modified_at}</td>
    `;
    filesBody.appendChild(row);
  });

  renderJobState(status.job_state || {});
}

function renderJobState(jobState) {
  const outlook = jobState.outlook;
  if (outlook) {
    outlookResult.textContent =
      `Last run ${outlook.completed_at}: downloaded ${outlook.downloaded_count || 0} PDF attachment(s) ` +
      `for ${outlook.date_from || "?"} to ${outlook.date_to || "?"}. ` +
      `Output: ${outlook.output_dir || "-"}. ` +
      `Errors: ${outlook.error_count || 0}.`;
  }

  const wix = jobState.wix;
  if (wix) {
    renderWixNextInvoice(wix.next_invoice);
    wixResult.textContent =
      `Last run ${wix.completed_at}: downloaded ${wix.downloaded_count || 0} Wix invoice PDF(s) ` +
      `for ${wix.date_from || "?"} to ${wix.date_to || "?"}. ` +
      `Subscriptions found: ${wix.subscriptions_count || 0}. ` +
      `Output: ${wix.output_dir || "-"}. ` +
      `Errors: ${wix.error_count || 0}.`;
  }

  const dropbox = jobState.dropbox;
  if (dropbox) {
    dropboxResult.textContent =
      `Last run ${dropbox.completed_at}: downloaded ${dropbox.downloaded_count || 0} Dropbox invoice PDF(s) ` +
      `for ${dropbox.date_from || "?"} to ${dropbox.date_to || "?"}. ` +
      `Output: ${dropbox.output_dir || "-"}. ` +
      `Errors: ${dropbox.error_count || 0}.`;
  }
}

function setDefaultJobDates() {
  const localDate = (value) => {
    const year = value.getFullYear();
    const month = String(value.getMonth() + 1).padStart(2, "0");
    const day = String(value.getDate()).padStart(2, "0");
    return `${year}-${month}-${day}`;
  };
  const today = new Date();
  const start = new Date(today.getFullYear(), today.getMonth(), 1);
  outlookDateFrom.value = localDate(start);
  outlookDateTo.value = localDate(today);
  wixDateFrom.value = localDate(start);
  wixDateTo.value = localDate(today);
  dropboxDateFrom.value = localDate(start);
  dropboxDateTo.value = localDate(today);
}

async function loadDashboard() {
  const [configResponse, statusResponse] = await Promise.all([
    fetch("/api/config"),
    fetch("/api/folder/status"),
  ]);
  const config = await configResponse.json();
  const status = await statusResponse.json();

  activeFolderInput.value = config.active_folder || "";
  renderStatus(status);
}

async function loadRuntimeUrls() {
  const response = await fetch("/api/runtime/urls");
  const urls = await response.json();

  if (phoneUrl && urls.phone_scan_url) {
    phoneUrl.href = urls.phone_scan_url;
    phoneUrl.textContent = urls.phone_scan_url;
  }

  if (phoneQr) {
    phoneQr.src = `/api/runtime/phone-qr.svg?t=${Date.now()}`;
  }
}

async function chooseFolder() {
  saveFolderBtn.disabled = true;
  saveFolderBtn.textContent = "Choosing...";

  try {
    const response = await fetch("/api/config/choose-folder", {
      method: "POST",
    });
    const data = await response.json();

    if (data.status === "cancelled") {
      showToast("Folder choice cancelled.");
      return;
    }

    if (!response.ok || data.status !== "saved") {
      showToast(data.message || "Could not choose folder.");
      return;
    }

    activeFolderInput.value = data.config.active_folder || "";
    renderStatus(data.folder);
    showToast("Folder selected.");
  } catch (error) {
    showToast("Could not choose folder.");
  } finally {
    saveFolderBtn.disabled = false;
    saveFolderBtn.textContent = "Choose folder";
  }
}

async function runOutlookDownload() {
  const dateFrom = outlookDateFrom.value;
  const dateTo = outlookDateTo.value;
  if (!dateFrom || !dateTo) {
    showToast("Set both Outlook dates first.");
    return;
  }

  outlookRunBtn.disabled = true;
  outlookRunBtn.textContent = "Downloading...";
  outlookResult.textContent = "Opening Outlook if needed and scanning for PDF attachments.";

  try {
    const response = await fetch("/api/jobs/outlook/attachments", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        date_from: dateFrom,
        date_to: dateTo,
        include_subfolders: outlookSubfolders.checked,
      }),
    });
    const data = await response.json();

    if (!response.ok || data.status !== "done") {
      throw new Error(data.message || "Outlook download failed.");
    }

    const result = data.result;
    outlookResult.textContent =
      `Downloaded ${result.downloaded_count} PDF attachment(s) to ${result.output_dir}. ` +
      `Skipped ${result.skipped_non_pdf} non-PDF attachment(s). ` +
      `Skipped ${result.skipped_excluded_sender || 0} excluded sender message(s). ` +
      `Skipped ${result.skipped_outside_date_range || 0} outside date range. ` +
      `Errors: ${result.error_count || 0}.`;
    await loadDashboard();
    showToast("Outlook download complete.");
  } catch (error) {
    outlookResult.textContent = error.message;
    showToast("Outlook download failed.");
  } finally {
    outlookRunBtn.disabled = false;
    outlookRunBtn.textContent = "Download";
  }
}

function renderWixNextInvoice(nextInvoice) {
  if (!nextInvoice) {
    wixNextInvoice.textContent = "Next Wix invoice: not found in subscription data.";
    return;
  }

  const parts = [
    `Next Wix invoice: ${nextInvoice.date}`,
    nextInvoice.website,
    nextInvoice.plan,
    nextInvoice.billing_cycle,
    nextInvoice.payment_method,
  ].filter(Boolean);
  wixNextInvoice.textContent = parts.join(" - ");
}

async function runWixDownload() {
  const dateFrom = wixDateFrom.value;
  const dateTo = wixDateTo.value;
  if (!dateFrom || !dateTo) {
    showToast("Set both Wix dates first.");
    return;
  }

  wixRunBtn.disabled = true;
  wixRunBtn.textContent = "Downloading...";
  wixNextInvoice.textContent = "";
  wixResult.textContent = wixForceLogin.checked
    ? "Opening Wix in a browser. Complete 2FA there; the app will continue after login."
    : "Checking saved Wix session and downloading invoice PDFs.";

  try {
    const response = await fetch("/api/jobs/wix/invoices", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        date_from: dateFrom,
        date_to: dateTo,
        force_login: wixForceLogin.checked,
        headless: false,
        login_timeout_ms: 10 * 60 * 1000,
      }),
    });
    const data = await response.json();

    if (!response.ok || data.status !== "done") {
      throw new Error(data.message || "Wix download failed.");
    }

    const result = data.result;
    renderWixNextInvoice(result.next_invoice);
    wixResult.textContent =
      `Downloaded ${result.downloaded_count} Wix invoice PDF(s) to ${result.output_dir}. ` +
      `Inspected ${result.inspected_rows || 0} invoice row(s). ` +
      `Subscriptions found: ${(result.subscriptions || []).length}. ` +
      `Errors: ${result.error_count || 0}.`;
    await loadDashboard();
    showToast("Wix download complete.");
  } catch (error) {
    wixResult.textContent = error.message;
    showToast("Wix download failed.");
  } finally {
    wixRunBtn.disabled = false;
    wixRunBtn.textContent = "Run";
  }
}

async function runDropboxDownload() {
  const dateFrom = dropboxDateFrom.value;
  const dateTo = dropboxDateTo.value;
  if (!dateFrom || !dateTo) {
    showToast("Set both Dropbox dates first.");
    return;
  }

  dropboxRunBtn.disabled = true;
  dropboxRunBtn.textContent = "Downloading...";
  dropboxResult.textContent = dropboxForceLogin.checked
    ? "Opening Dropbox in a browser. Complete 2FA there; the app will continue after login."
    : "Checking saved Dropbox session and downloading invoice PDFs.";

  try {
    const response = await fetch("/api/jobs/dropbox/invoices", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        date_from: dateFrom,
        date_to: dateTo,
        force_login: dropboxForceLogin.checked,
        headless: false,
        login_timeout_ms: 10 * 60 * 1000,
      }),
    });
    const data = await response.json();

    if (!response.ok || data.status !== "done") {
      throw new Error(data.message || "Dropbox download failed.");
    }

    const result = data.result;
    dropboxResult.textContent =
      `Downloaded ${result.downloaded_count} Dropbox invoice PDF(s) to ${result.output_dir}. ` +
      `Inspected ${result.inspected_rows || 0} invoice row(s). ` +
      `Errors: ${result.error_count || 0}.`;
    await loadDashboard();
    showToast("Dropbox download complete.");
  } catch (error) {
    dropboxResult.textContent = error.message;
    showToast("Dropbox download failed.");
  } finally {
    dropboxRunBtn.disabled = false;
    dropboxRunBtn.textContent = "Run";
  }
}

saveFolderBtn.addEventListener("click", chooseFolder);
outlookRunBtn.addEventListener("click", runOutlookDownload);
wixRunBtn.addEventListener("click", runWixDownload);
dropboxRunBtn.addEventListener("click", runDropboxDownload);
refreshBtn.addEventListener("click", () => {
  loadDashboard()
    .then(() => showToast("Dashboard refreshed."))
    .catch(() => showToast("Could not refresh dashboard."));
});

document.querySelectorAll(".nav-list a[data-page]").forEach((link) => {
  link.addEventListener("click", (e) => {
    e.preventDefault();
    const page = link.dataset.page;
    document.querySelectorAll(".nav-list a").forEach((a) => a.classList.remove("active"));
    link.classList.add("active");
    document.querySelectorAll(".content").forEach((section) => {
      section.hidden = section.id !== `page-${page}`;
    });
  });
});

setDefaultJobDates();
loadRuntimeUrls().catch(() => {
  if (phoneUrl) phoneUrl.textContent = "Could not load scanner URL.";
});
loadDashboard().catch(() => showToast("Could not load dashboard."));

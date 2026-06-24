const { ipcRenderer } = require('electron');

// ========== State ==========
let jsonData = null;
let screenshots = [];
let currentIndex = -1;
let currentFilter = 'all';
let currentRecord = null;
let filteredIndices = [];
let jsonFilePath = '';

// DOM Elements
const jsonPathInput = document.getElementById('jsonPathInput');
const screenshotsPathInput = document.getElementById('screenshotsPathInput');
const browseJsonBtn = document.getElementById('browseJsonBtn');
const browseFolderBtn = document.getElementById('browseFolderBtn');
const scanBtn = document.getElementById('scanBtn');
const listFrame = document.getElementById('listFrame');
const loggedCount = document.getElementById('loggedCount');
const partialCount = document.getElementById('partialCount');
const notLoggedCount = document.getElementById('notLoggedCount');
const emptyState = document.getElementById('emptyState');
const detailContent = document.getElementById('detailContent');
const detailTitle = document.getElementById('detailTitle');
const detailBadge = document.getElementById('detailBadge');
const previewImage = document.getElementById('previewImage');
const statusMessage = document.getElementById('statusMessage');
const fieldsContainer = document.getElementById('fieldsContainer');
const confirmSaveBtn = document.getElementById('confirmSaveBtn');
const prevBtn = document.getElementById('prevBtn');
const nextBtn = document.getElementById('nextBtn');
const filterBtns = document.querySelectorAll('.filter-btn');

// Modal elements
const modal = document.getElementById('confirmationModal');
const modalTitle = document.getElementById('modalTitle');
const modalMessage = document.getElementById('modalMessage');
const modalConfirm = document.getElementById('modalConfirm');
const modalCancel = document.getElementById('modalCancel');

// ========== Constants ==========
const MODE_LABELS = {
    conquest: 'Conquest',
    control: 'Control',
    hardpoint: 'Hardpoint',
    'kill-confirmed': 'Kill Confirmed'
};

const REQUIRED_FIELDS = [
    'captures', 'destroyed', 'deaths', 'assists',
    'damage_caused', 'damage_blocked', 'credits', 'tech',
    'intel', 'XP', 'agent', 'vehicle', 'outcome', 'map'
];

// ========== Initialization ==========
document.addEventListener('DOMContentLoaded', () => {
    initTitleBar();
    initEventListeners();
    loadOptions();
});

function initTitleBar() {
    document.getElementById('minimizeBtn').addEventListener('click', () => {
        ipcRenderer.invoke('window-minimize');
    });
    document.getElementById('maximizeBtn').addEventListener('click', async () => {
        await ipcRenderer.invoke('window-maximize');
        updateMaximizeButton();
    });
    document.getElementById('closeBtn').addEventListener('click', () => {
        ipcRenderer.invoke('window-close');
    });
    updateMaximizeButton();
}

async function updateMaximizeButton() {
    const isMaximized = await ipcRenderer.invoke('window-is-maximized');
    const icon = document.querySelector('#maximizeBtn svg');
    if (isMaximized) {
        icon.innerHTML = '<path d="M3 3h6v6H3zM7 7h6v6H7z" fill="none" stroke="currentColor" />';
    } else {
        icon.innerHTML = '<path d="M1 1h10v10H1z" fill="none" stroke="currentColor" />';
    }
}

function initEventListeners() {
    browseJsonBtn.addEventListener('click', browseJson);
    browseFolderBtn.addEventListener('click', browseFolder);
    scanBtn.addEventListener('click', scanData);
    confirmSaveBtn.addEventListener('click', confirmAndSave);
    prevBtn.addEventListener('click', () => navigateScreenshot(-1));
    nextBtn.addEventListener('click', () => navigateScreenshot(1));

    filterBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            filterBtns.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            currentFilter = btn.dataset.filter;
            applyFilter();
        });
    });

    // Modal events
    modalCancel.addEventListener('click', closeModal);
    modal.addEventListener('click', (e) => {
        if (e.target === modal) closeModal();
    });
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
            if (modal.classList.contains('show')) closeModal();
        }
        if (e.key === 'ArrowLeft' && detailContent.style.display !== 'none') {
            navigateScreenshot(-1);
        }
        if (e.key === 'ArrowRight' && detailContent.style.display !== 'none') {
            navigateScreenshot(1);
        }
    });

    // Handle window resize for image
    window.addEventListener('resize', () => {
        const img = document.getElementById('previewImage');
        if (img && img.src) {
            const container = img.parentElement;
            if (container) {
                const currentSrc = img.src;
                img.src = '';
                setTimeout(() => {
                    img.src = currentSrc;
                }, 10);
            }
        }
    });
}

// ========== Options ==========
async function loadOptions() {
    try {
        const options = await ipcRenderer.invoke('load-options');
        if (options) {
            jsonPathInput.value = options.jsonPath || '';
            screenshotsPathInput.value = options.screenshotsFolder || '';
            if (options.autoLoad !== false && options.jsonPath && options.screenshotsFolder) {
                setTimeout(() => scanData(), 500);
            }
        }
    } catch (error) {
        console.error('Error loading options:', error);
    }
}

async function saveOptions() {
    const options = {
        jsonPath: jsonPathInput.value,
        screenshotsFolder: screenshotsPathInput.value,
        autoLoad: true
    };
    try {
        await ipcRenderer.invoke('save-options', options);
    } catch (error) {
        console.error('Error saving options:', error);
    }
}

// ========== File Browsing ==========
async function browseJson() {
    const result = await ipcRenderer.invoke('show-open-dialog', {
        filters: [{ name: 'JSON Files', extensions: ['json'] }]
    });
    if (!result.canceled && result.filePaths.length > 0) {
        const filePath = result.filePaths[0];
        jsonPathInput.value = filePath;
        jsonFilePath = filePath;
        saveOptions();
        scanData();
    }
}

async function browseFolder() {
    const result = await ipcRenderer.invoke('show-open-directory');
    if (!result.canceled && result.filePaths.length > 0) {
        screenshotsPathInput.value = result.filePaths[0];
        saveOptions();
        scanData();
    }
}

// ========== Scanning ==========
async function scanData() {
    jsonFilePath = jsonPathInput.value;
    const folderPath = screenshotsPathInput.value;

    if (!jsonFilePath || !folderPath) {
        showToast('Please select both JSON file and screenshots folder.', 'error');
        return;
    }

    try {
        // Load JSON
        const fileResult = await ipcRenderer.invoke('read-file', jsonFilePath);
        if (!fileResult.success) {
            showToast('Error reading JSON: ' + fileResult.error, 'error');
            return;
        }

        jsonData = JSON.parse(fileResult.content);

        // Scan screenshots
        const scanResult = await ipcRenderer.invoke('scan-screenshots', folderPath, jsonData);
        if (!scanResult.success) {
            showToast('Error scanning screenshots: ' + scanResult.error, 'error');
            return;
        }

        screenshots = scanResult.results;
        saveOptions();
        applyFilter();
        showToast(`Loaded ${screenshots.length} screenshots`, 'success');
    } catch (error) {
        console.error('Scan error:', error);
        showToast('Error: ' + error.message, 'error');
    }
}

// ========== Filtering ==========
function applyFilter() {
    filteredIndices = [];
    screenshots.forEach((s, i) => {
        if (currentFilter === 'all' || s.status === currentFilter) {
            filteredIndices.push(i);
        }
    });
    renderList();
    updateCounts();

    // Select first if available
    if (filteredIndices.length > 0) {
        selectScreenshot(filteredIndices[0]);
    } else {
        emptyState.style.display = 'flex';
        detailContent.style.display = 'none';
    }
}

function updateCounts() {
    const logged = screenshots.filter(s => s.status === 'logged').length;
    const partial = screenshots.filter(s => s.status === 'partial').length;
    const notLogged = screenshots.filter(s => s.status === 'not_logged').length;
    loggedCount.textContent = logged;
    partialCount.textContent = partial;
    notLoggedCount.textContent = notLogged;
}

// ========== Rendering ==========
function renderList() {
    listFrame.innerHTML = '';

    if (filteredIndices.length === 0) {
        const empty = document.createElement('div');
        empty.style.cssText = 'text-align:center;padding:40px 0;color:var(--text-muted);font-size:14px;';
        empty.textContent = 'Nothing here.';
        listFrame.appendChild(empty);
        return;
    }

    filteredIndices.forEach((realIdx) => {
        const s = screenshots[realIdx];
        const item = document.createElement('div');
        item.className = 'list-item';
        if (realIdx === currentIndex) {
            item.classList.add('selected');
        }

        // Dot color based on mode
        const dotColors = {
            conquest: '#f59e0b',
            control: '#0077ff',
            hardpoint: '#ef4444',
            'kill-confirmed': '#a855f7'
        };
        const dot = document.createElement('div');
        dot.className = 'list-item-dot';
        dot.style.background = dotColors[s.mode] || '#ff8300';
        item.appendChild(dot);

        const info = document.createElement('div');
        info.className = 'list-item-info';
        const name = document.createElement('div');
        name.className = 'list-item-name';
        name.textContent = s.player;
        const meta = document.createElement('div');
        meta.className = 'list-item-meta';
        meta.textContent = `${MODE_LABELS[s.mode] || s.mode} · ${s.filename}`;
        info.appendChild(name);
        info.appendChild(meta);
        item.appendChild(info);

        const badge = document.createElement('div');
        badge.className = `list-item-badge badge-${s.status}`;
        badge.textContent = s.status === 'logged' ? 'LOGGED' :
                           s.status === 'partial' ? 'PARTIAL' : 'NOT LOGGED';
        item.appendChild(badge);

        item.addEventListener('click', () => selectScreenshot(realIdx));
        listFrame.appendChild(item);
    });
}

// ========== Screenshot Selection ==========
async function selectScreenshot(realIdx) {
    if (realIdx < 0 || realIdx >= screenshots.length) return;

    currentIndex = realIdx;
    const s = screenshots[realIdx];

    // Update list selection
    document.querySelectorAll('.list-item').forEach(el => el.classList.remove('selected'));
    const items = listFrame.querySelectorAll('.list-item');
    const pos = filteredIndices.indexOf(realIdx);
    if (pos >= 0 && pos < items.length) {
        items[pos].classList.add('selected');
    }

    // Show detail panel
    emptyState.style.display = 'none';
    detailContent.style.display = 'flex';

    // Update header
    detailTitle.textContent = `${s.player} · ${s.filename}`;
    detailBadge.textContent = (MODE_LABELS[s.mode] || s.mode).toUpperCase();

    // Load preview
    const imageUrl = 'file:///' + s.filepath.replace(/\\/g, '/');
    previewImage.src = imageUrl;
    previewImage.onerror = () => {
        previewImage.alt = 'Preview unavailable';
        previewImage.src = '';
    };

    // Get existing record
    try {
        const result = await ipcRenderer.invoke('get-existing-record', jsonData, s.mode, s.filename);
        if (result.success && result.record) {
            currentRecord = result.record;
            const emptyCount = countEmptyFields(currentRecord);
            if (s.status === 'logged') {
                statusMessage.textContent = `✓ Complete record found (${emptyCount} empty fields allowed). Edit and confirm to update.`;
                statusMessage.style.color = '#22c55e';
            } else {
                statusMessage.textContent = `⚠ Partial record found (${emptyCount} empty fields). Complete missing fields and confirm.`;
                statusMessage.style.color = '#ff8c00';
            }
        } else {
            currentRecord = null;
            statusMessage.textContent = '✗ No record found. Enter data and confirm.';
            statusMessage.style.color = '#ef4444';
        }
    } catch (error) {
        currentRecord = null;
        statusMessage.textContent = '✗ No record found. Enter data and confirm.';
        statusMessage.style.color = '#ef4444';
    }

    renderFields(s);
}

// ========== Field Rendering ==========
function renderFields(s) {
    fieldsContainer.innerHTML = '';

    const isKC = s.mode === 'kill-confirmed';

    // Stats fields
    const statFields = isKC ? [
        ['confirms', 'Confirms'],
        ['denies', 'Denies'],
        ['destroyed', 'Destroyed'],
        ['deaths', 'Deaths'],
        ['assists', 'Assists'],
        ['damage_caused', 'Damage Caused'],
        ['damage_blocked', 'Damage Blocked']
    ] : [
        ['captures', 'Captures'],
        ['destroyed', 'Destroyed'],
        ['deaths', 'Deaths'],
        ['assists', 'Assists'],
        ['damage_caused', 'Damage Caused'],
        ['damage_blocked', 'Damage Blocked']
    ];

    // Meta fields
    const metaFields = [
        ['credits', 'Credits (Rewards)'],
        ['tech', 'Tech (Rewards)'],
        ['intel', 'Intel (Rewards)'],
        ['XP', 'Vehicle XP'],
        ['agent', 'Agent'],
        ['vehicle', 'Vehicle'],
        ['outcome', 'Outcome'],
        ['map', 'Map']
    ];

    // Stats group
    const statsGroup = document.createElement('div');
    statsGroup.className = 'field-group';
    const statsTitle = document.createElement('div');
    statsTitle.className = 'field-group-title';
    statsTitle.textContent = 'MATCH STATS';
    statsGroup.appendChild(statsTitle);

    statFields.forEach(([key, label]) => {
        const row = createFieldRow(key, label);
        statsGroup.appendChild(row);
    });
    fieldsContainer.appendChild(statsGroup);

    // Meta group
    const metaGroup = document.createElement('div');
    metaGroup.className = 'field-group';
    const metaTitle = document.createElement('div');
    metaTitle.className = 'field-group-title';
    metaTitle.textContent = 'REWARDS & META';
    metaGroup.appendChild(metaTitle);

    metaFields.forEach(([key, label]) => {
        const row = createFieldRow(key, label);
        metaGroup.appendChild(row);
    });
    fieldsContainer.appendChild(metaGroup);

    // Proof group
    const proofGroup = document.createElement('div');
    proofGroup.className = 'field-group';
    const proofTitle = document.createElement('div');
    proofTitle.className = 'field-group-title';
    proofTitle.textContent = 'PROOF';
    proofGroup.appendChild(proofTitle);

    const proofRow = document.createElement('div');
    proofRow.className = 'field-row';
    const proofLabel = document.createElement('div');
    proofLabel.className = 'field-label';
    proofLabel.textContent = 'URL';
    proofRow.appendChild(proofLabel);
    const proofValue = document.createElement('div');
    proofValue.className = 'field-proof';
    const base = 'https://cdn6.heatlabs.net/player-records';
    proofValue.textContent = `${base}/${s.mode}/${s.filename}`;
    proofRow.appendChild(proofValue);
    proofGroup.appendChild(proofRow);
    fieldsContainer.appendChild(proofGroup);
}

function createFieldRow(key, label) {
    const row = document.createElement('div');
    row.className = 'field-row';

    const labelEl = document.createElement('div');
    labelEl.className = 'field-label';
    labelEl.textContent = label;
    row.appendChild(labelEl);

    const input = document.createElement('input');
    input.className = 'field-input';
    input.type = 'text';
    input.dataset.key = key;

    if (currentRecord && currentRecord[key] !== undefined) {
        input.value = currentRecord[key] !== null ? String(currentRecord[key]) : '';
    }

    row.appendChild(input);
    return row;
}

// ========== Count Empty Fields ==========
function countEmptyFields(record) {
    let count = 0;
    for (const field of REQUIRED_FIELDS) {
        const value = record[field];
        if (value === null || value === undefined || value === '' || value === 0 || value === '0') {
            count++;
        }
    }
    return count;
}

// ========== Navigation ==========
function navigateScreenshot(direction) {
    const pos = filteredIndices.indexOf(currentIndex);
    if (pos < 0) return;
    const newPos = pos + direction;
    if (newPos >= 0 && newPos < filteredIndices.length) {
        selectScreenshot(filteredIndices[newPos]);
    }
}

// ========== Confirm & Save ==========
async function confirmAndSave() {
    if (currentIndex < 0 || !jsonData) {
        showToast('No screenshot selected or data loaded.', 'error');
        return;
    }

    if (!jsonFilePath) {
        showToast('No JSON file path set. Please load a JSON file first.', 'error');
        return;
    }

    const s = screenshots[currentIndex];
    const record = {};

    // Gather all field values
    const inputs = fieldsContainer.querySelectorAll('.field-input');
    inputs.forEach(input => {
        const key = input.dataset.key;
        const raw = input.value.trim();

        // Parse numbers
        if (['captures', 'confirms', 'denies', 'destroyed', 'deaths', 'assists',
             'damage_caused', 'damage_blocked', 'credits', 'tech', 'intel', 'XP'].includes(key)) {
            const num = parseInt(raw.replace(/[^0-9-]/g, '')) || 0;
            record[key] = num;
        } else {
            record[key] = raw;
        }
    });

    // Add mode and proof
    record.mode = MODE_LABELS[s.mode] || s.mode;
    const base = 'https://cdn6.heatlabs.net/player-records';
    record.proof = `${base}/${s.mode}/${s.filename}`;

    try {
        console.log('Saving record for:', s.player, 'mode:', s.mode);
        console.log('Record data:', record);
        console.log('Current jsonData structure:', JSON.stringify(jsonData, null, 2).substring(0, 200) + '...');

        // Update the in-memory jsonData
        const result = await ipcRenderer.invoke('update-record', jsonData, s.mode, s.player, record);

        console.log('Update result:', result);

        if (!result.success) {
            showToast('Error saving record: ' + result.error, 'error');
            return;
        }

        // Ensure we have the updated data
        if (result.jsonData) {
            jsonData = result.jsonData;
        }

        // Save JSON file
        const jsonString = JSON.stringify(jsonData, null, 4);
        console.log('Saving JSON to:', jsonFilePath);
        console.log('JSON content length:', jsonString.length);

        const saveResult = await ipcRenderer.invoke('save-file', jsonFilePath, jsonString);

        console.log('Save result:', saveResult);

        if (!saveResult.success) {
            showToast('Error saving JSON: ' + saveResult.error, 'error');
            return;
        }

        // Update status
        const emptyCount = countEmptyFields(record);
        if (emptyCount <= 2) {
            s.status = 'logged';
            statusMessage.textContent = `✓ Record saved! Complete with ${emptyCount} empty fields.`;
            statusMessage.style.color = '#22c55e';
        } else {
            s.status = 'partial';
            statusMessage.textContent = `⚠ Record saved! ${emptyCount} empty fields remaining.`;
            statusMessage.style.color = '#ff8c00';
        }

        currentRecord = record;
        updateCounts();
        renderList();

        // Re-apply filter to refresh the list
        applyFilter();

        showToast(`Record saved for ${s.player}`, 'success');

        // Auto-navigate to next non-logged item
        const nextIdx = screenshots.findIndex((sc, i) =>
            i > currentIndex && sc.status !== 'logged'
        );
        if (nextIdx >= 0) {
            setTimeout(() => selectScreenshot(nextIdx), 600);
        }
    } catch (error) {
        console.error('Save error:', error);
        showToast('Error: ' + error.message, 'error');
    }
}

// ========== Modal ==========
function showModal(title, message, confirmText = 'Confirm', onConfirm) {
    modalTitle.textContent = title;
    modalMessage.textContent = message;
    modalConfirm.textContent = confirmText;
    modalConfirm.onclick = () => {
        closeModal();
        if (onConfirm) onConfirm();
    };
    modal.classList.add('show');
}

function closeModal() {
    modal.classList.remove('show');
}

// ========== Toast ==========
function showToast(message, type = 'success') {
    const existing = document.querySelectorAll('.toast-notification');
    existing.forEach(t => t.remove());

    const toast = document.createElement('div');
    toast.className = `toast-notification ${type}`;
    toast.textContent = message;
    document.body.appendChild(toast);

    setTimeout(() => toast.classList.add('show'), 10);
    setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => toast.remove(), 300);
    }, type === 'error' ? 5000 : 3000);
}

// ========== Splash Screen ==========
setTimeout(() => {
    const splash = document.getElementById('splash-screen');
    const main = document.getElementById('main-app');
    if (splash && main) {
        splash.style.opacity = '0';
        setTimeout(() => {
            splash.style.display = 'none';
            main.style.opacity = '1';
        }, 500);
    }
}, 3500);
const {
    app,
    BrowserWindow,
    dialog,
    ipcMain
} = require('electron');
const path = require('path');
const fs = require('fs').promises;

let mainWindow;

// Development flag
const isDevelopment = false;

function createWindow() {
    mainWindow = new BrowserWindow({
        width: 1340,
        height: 820,
        minWidth: 1100,
        minHeight: 700,
        webPreferences: {
            nodeIntegration: true,
            contextIsolation: false,
            enableRemoteModule: true,
            devTools: isDevelopment
        },
        frame: false,
        titleBarStyle: 'hidden',
        backgroundColor: '#0f0f0f',
        show: false,
        icon: path.join(__dirname, 'assets', 'icon.png')
    });

    mainWindow.loadFile('index.html');

    if (!isDevelopment) {
        mainWindow.webContents.on('devtools-opened', () => {
            mainWindow.webContents.closeDevTools();
        });

        mainWindow.webContents.on('before-input-event', (event, input) => {
            if (input.key === 'F12' ||
                (input.control && input.shift && input.key.toLowerCase() === 'i') ||
                (input.control && input.shift && input.key.toLowerCase() === 'c')) {
                event.preventDefault();
            }
        });
    }

    mainWindow.once('ready-to-show', () => {
        mainWindow.show();
    });

    mainWindow.on('closed', () => {
        mainWindow = null;
    });
}

// Window controls
ipcMain.handle('window-minimize', () => {
    if (mainWindow) mainWindow.minimize();
});

ipcMain.handle('window-maximize', () => {
    if (mainWindow) {
        if (mainWindow.isMaximized()) {
            mainWindow.unmaximize();
        } else {
            mainWindow.maximize();
        }
    }
});

ipcMain.handle('window-close', () => {
    if (mainWindow) mainWindow.close();
});

ipcMain.handle('window-is-maximized', () => {
    return mainWindow ? mainWindow.isMaximized() : false;
});

// File operations
ipcMain.handle('show-open-dialog', async (event, options) => {
    const defaultOptions = {
        properties: ['openFile'],
        filters: [{
            name: 'JSON Files',
            extensions: ['json']
        }, {
            name: 'All Files',
            extensions: ['*']
        }]
    };

    const dialogOptions = options ? { ...defaultOptions, ...options } : defaultOptions;
    const result = await dialog.showOpenDialog(mainWindow, dialogOptions);
    return result;
});

ipcMain.handle('show-open-directory', async (event, options) => {
    const defaultOptions = {
        properties: ['openDirectory']
    };

    const dialogOptions = options ? { ...defaultOptions, ...options } : defaultOptions;
    const result = await dialog.showOpenDialog(mainWindow, dialogOptions);
    return result;
});

ipcMain.handle('read-file', async (event, filePath) => {
    try {
        const content = await fs.readFile(filePath, 'utf8');
        if (!content.trim()) {
            return { success: false, error: 'File is empty' };
        }
        return { success: true, content };
    } catch (error) {
        return { success: false, error: error.message };
    }
});

ipcMain.handle('save-file', async (event, filePath, data) => {
    try {
        await fs.writeFile(filePath, data, 'utf8');
        return { success: true };
    } catch (error) {
        console.error('Save file error:', error);
        return { success: false, error: error.message };
    }
});

// Options management
ipcMain.handle('load-options', async () => {
    try {
        const appDataPath = app.getPath('appData');
        const configDir = path.join(appDataPath, 'HEATLabsRecordKeeper');
        const configPath = path.join(configDir, 'settings.json');
        const data = await fs.readFile(configPath, 'utf8');
        return JSON.parse(data);
    } catch (error) {
        if (error.code === 'ENOENT') {
            return {
                jsonPath: '',
                screenshotsFolder: '',
                autoLoad: true
            };
        }
        console.error('Error loading options:', error);
        return {
            jsonPath: '',
            screenshotsFolder: '',
            autoLoad: true
        };
    }
});

ipcMain.handle('save-options', async (event, options) => {
    try {
        const appDataPath = app.getPath('appData');
        const configDir = path.join(appDataPath, 'HEATLabsRecordKeeper');
        const configPath = path.join(configDir, 'settings.json');
        await fs.mkdir(configDir, { recursive: true });
        await fs.writeFile(configPath, JSON.stringify(options, null, 2));
        return { success: true };
    } catch (error) {
        console.error('Error saving options:', error);
        return { success: false, error: error.message };
    }
});

// Scan screenshots directory
ipcMain.handle('scan-screenshots', async (event, screenshotsFolder, jsonData) => {
    try {
        const results = [];
        const base = path.resolve(screenshotsFolder);

        // Get known proofs from JSON
        const knownProofs = new Set();
        const completeProofs = new Set();
        const partialProofs = new Set();

        const records = jsonData.records || {};
        const requiredFields = ['captures', 'destroyed', 'deaths', 'assists', 'damage_caused', 'damage_blocked',
            'credits', 'tech', 'intel', 'XP', 'agent', 'vehicle', 'outcome', 'map'];

        for (const modeData of Object.values(records)) {
            if (typeof modeData !== 'object') continue;
            for (const playerRecords of Object.values(modeData)) {
                if (!Array.isArray(playerRecords)) continue;
                for (const rec of playerRecords) {
                    const proof = rec.proof || '';
                    if (!proof) continue;
                    const proofName = path.basename(proof);
                    knownProofs.add(proofName);

                    // Check completeness
                    let emptyCount = 0;
                    for (const field of requiredFields) {
                        const value = rec[field];
                        if (value === null || value === undefined || value === '' || value === 0 || value === '0') {
                            emptyCount++;
                        }
                    }

                    if (emptyCount <= 2) {
                        completeProofs.add(proofName);
                    } else {
                        // Check if it has any data
                        let hasData = false;
                        for (const field of requiredFields) {
                            const value = rec[field];
                            if (value !== null && value !== undefined && value !== '' && value !== 0 && value !== '0') {
                                hasData = true;
                                break;
                            }
                        }
                        if (hasData) {
                            partialProofs.add(proofName);
                        }
                    }
                }
            }
        }

        // Scan folders for each mode
        const modes = ['conquest', 'control', 'hardpoint', 'kill-confirmed'];
        const modeLabels = {
            'conquest': 'Conquest',
            'control': 'Control',
            'hardpoint': 'Hardpoint',
            'kill-confirmed': 'Kill Confirmed'
        };

        for (const mode of modes) {
            const sub = path.join(base, mode);
            try {
                await fs.access(sub);
                const files = await fs.readdir(sub);
                const sortedFiles = files.filter(f => {
                    const ext = path.extname(f).toLowerCase();
                    return ['.png', '.jpg', '.jpeg', '.webp'].includes(ext);
                }).sort();

                for (const filename of sortedFiles) {
                    const filepath = path.join(sub, filename);
                    const stats = await fs.stat(filepath);

                    // Parse player name from filename - IMPROVED LOGIC
                    let playerName = filename;
                    const nameWithoutExt = path.basename(filename, path.extname(filename));

                    // Try to extract player name - look for patterns
                    // Pattern 1: player_extra.png (standard format)
                    // Pattern 2: date_player.png (date then player)
                    // Pattern 3: player.png (just player name)

                    const match = nameWithoutExt.match(/^(.+?)_/);
                    if (match) {
                        // Check if the first part looks like a date (digits only)
                        const firstPart = match[1];
                        if (/^\d+$/.test(firstPart) && firstPart.length >= 6) {
                            // It's a date, try to get the player name after the underscore
                            const remaining = nameWithoutExt.substring(firstPart.length + 1);
                            if (remaining) {
                                // Check if there's another underscore - take everything after the date
                                const playerMatch = remaining.match(/^(.+?)(?:_|$)/);
                                if (playerMatch) {
                                    playerName = playerMatch[1];
                                } else {
                                    playerName = remaining;
                                }
                            }
                        } else {
                            // Standard format: player_extra
                            playerName = firstPart;
                        }
                    } else {
                        // No underscore, use the whole name
                        playerName = nameWithoutExt;
                    }

                    // Determine status
                    let status;
                    if (completeProofs.has(filename)) {
                        status = 'logged';
                    } else if (partialProofs.has(filename) || knownProofs.has(filename)) {
                        status = 'partial';
                    } else {
                        status = 'not_logged';
                    }

                    results.push({
                        mode: mode,
                        modeLabel: modeLabels[mode] || mode,
                        player: playerName,
                        filename: filename,
                        filepath: filepath,
                        status: status,
                        size: stats.size,
                        modified: stats.mtime
                    });
                }
            } catch (err) {
                // Folder doesn't exist, skip
                continue;
            }
        }

        return { success: true, results };
    } catch (error) {
        console.error('Error scanning screenshots:', error);
        return { success: false, error: error.message };
    }
});

// Get existing record for a screenshot
ipcMain.handle('get-existing-record', async (event, jsonData, mode, filename) => {
    try {
        const records = jsonData.records || {};
        const modeData = records[mode] || {};

        for (const playerRecords of Object.values(modeData)) {
            if (!Array.isArray(playerRecords)) continue;
            for (const rec of playerRecords) {
                const proof = rec.proof || '';
                if (path.basename(proof) === filename) {
                    return { success: true, record: rec };
                }
            }
        }
        return { success: true, record: null };
    } catch (error) {
        return { success: false, error: error.message };
    }
});

// Update or add record
ipcMain.handle('update-record', async (event, jsonData, mode, player, record) => {
    try {
        // Ensure the structure exists
        if (!jsonData.records) {
            jsonData.records = {};
        }
        if (!jsonData.records[mode]) {
            jsonData.records[mode] = {};
        }

        const modeData = jsonData.records[mode];
        const proof = record.proof || '';
        const proofName = path.basename(proof);

        let updated = false;

        // Check if this proof exists under ANY player name in this mode
        for (const [existingPlayer, existingRecords] of Object.entries(modeData)) {
            if (!Array.isArray(existingRecords)) continue;

            for (let i = 0; i < existingRecords.length; i++) {
                const existingProof = existingRecords[i].proof || '';
                const existingProofName = path.basename(existingProof);

                if (existingProofName === proofName) {
                    // Found the record under a different player name
                    // Update it in place
                    existingRecords[i] = {
                        ...existingRecords[i],
                        ...record
                    };

                    // If the player name is different, move the record to the correct player
                    if (existingPlayer !== player) {
                        // Remove from old location
                        existingRecords.splice(i, 1);
                        // If the old player has no more records, delete the player entry
                        if (existingRecords.length === 0) {
                            delete modeData[existingPlayer];
                        }
                        // Add to new player
                        if (!modeData[player]) {
                            modeData[player] = [];
                        }
                        modeData[player].push(record);
                    }

                    updated = true;
                    console.log(`Updated existing record for ${existingPlayer} -> ${player} - ${proofName}`);
                    break;
                }
            }
            if (updated) break;
        }

        // If no existing record found, add new one
        if (!updated) {
            // Add the new record
            if (!modeData[player]) {
                modeData[player] = [];
            }
            modeData[player].push(record);
            console.log(`Added new record for ${player} - ${proofName}`);
        }

        // Clean up any empty player entries
        for (const [key, value] of Object.entries(modeData)) {
            if (Array.isArray(value) && value.length === 0) {
                delete modeData[key];
            }
        }

        // Return success with the updated jsonData
        return {
            success: true,
            updated: updated,
            jsonData: jsonData
        };
    } catch (error) {
        console.error('Error updating record:', error);
        return { success: false, error: error.message };
    }
});

app.whenReady().then(() => {
    createWindow();
});

app.on('window-all-closed', () => {
    if (process.platform !== 'darwin') app.quit();
});

app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
});
# Kobo Sage Notebooks to Obsidian - Research

## Overview

Research into tools and workflows for exporting Kobo Sage notebooks (handwritten notes) to Obsidian. Two main approaches investigated: USB/Linux automation and cloud-based automation.

---

## Kobo Notebook File Format

### The `.nebo` Format

Kobo notebooks use MyScript's proprietary `.nebo` format. The file is a ZIP archive with the following structure:

```
notebook.nebo
├── index.bdom
├── meta.json          # Device metadata, DPI (228x228), geometry (1404x1872)
├── pages/
│   └── [8-letter-page-id]/
│       ├── ink.bink   # Binary stroke data (proprietary)
│       ├── meta.json
│       ├── page.bdom
│       └── style.css
└── rel.json
```

**Key limitation:** The `ink.bink` files contain handwriting strokes in a proprietary binary format from MyScript. No open-source decoder exists.

### Native Export Formats

Kobo can export notebooks to:
- **Basic notebooks:** PNG, JPEG, PDF, ZIP
- **Advanced notebooks:** Word (.docx), Text, HTML, ZIP, PNG, JPEG, PDF

Exported files are stored in `Exported Annotations/` folder on the device.

---

## Approach 1: USB Connection to Linux

### File Locations

When connected via USB, the device mounts as `KOBOeReader`:
- Raw notebooks: `.nebo` files in device storage
- Exported notebooks: `Exported Annotations/` folder
- Database: `.kobo/KoboReader.sqlite` (for text highlights/annotations)

### Direct `.nebo` Extraction

**Status: Not feasible**

The `ink.bink` binary format is undocumented. Potential workarounds:
1. MyScript developer account can convert `.nebo` → `.jiix` (JSON with stroke coordinates)
   - Requires Windows + Visual Studio + certificates
   - Impractical for automation
2. Reverse engineering the binary format (no existing tools)

### Automation for Pre-Exported Files

If you export notebooks on-device first, you can automate copying:

```bash
#!/bin/bash
# Auto-copy exported notebooks when Kobo mounts
KOBO_MOUNT="/run/media/$USER/KOBOeReader"
OBSIDIAN_VAULT="$HOME/Documents/Vault/Daily/kobo"

if [ -d "$KOBO_MOUNT/Exported Annotations" ]; then
    cp -r "$KOBO_MOUNT/Exported Annotations/"* "$OBSIDIAN_VAULT/notebooks/"
    echo "Notebooks copied to Obsidian vault"
fi
```

Could be triggered via **udev rules** when device mounts.

### Text Highlights/Annotations (Not Handwritten)

For text-based highlights (not handwritten notebooks), several tools exist:

- [Kobo Highlights Importer Plugin](https://www.obsidianstats.com/plugins/obsidian-kobo-highlights-importer-plugin) - Native Obsidian plugin
- [kobo-to-obsidian-import](https://github.com/chrisbrasington/kobo-to-obsidian-import) - Python script with Obsidian callout formatting
- [export-kobo](https://github.com/pettarin/export-kobo) - Python tool for SQLite extraction
- [kobo-annotation-exporter](https://github.com/Moonire/kobo-annotation-exporter) - Markdown export

---

## Approach 2: Cloud Automation

### Kobo Web Portal

Notebooks sync to: https://www.kobo.com/us/en/library/notebooks

**Status: Limited automation potential**

Challenges:
- No public API for notebooks
- CAPTCHA on login blocks headless browsers
- Existing scrapers (e.g., [kobo-scraper](https://github.com/hill84/kobo-scraper)) are for book metadata, not notebooks

### Dropbox/Google Drive Integration

Kobo has native integration with Dropbox and Google Drive:
- Link account via device Settings
- Export notebooks directly to cloud storage
- Files sync automatically

**Limitation:** One-way sync only, must use `Apps/Kobo` folder in Dropbox.

---

## Recommended Workflow

### Option A: Dropbox Sync (Most Automated)

1. Link Kobo to Dropbox (Settings → Dropbox on device)
2. Export notebooks to Dropbox as Text (searchable) or PDF (visual)
3. Symlink to Obsidian vault:
   ```bash
   ln -s ~/Dropbox/Apps/Kobo ~/Documents/Vault/Daily/kobo/notebooks
   ```

### Option B: USB with Pre-Export

1. Export notebooks on device (tap notebook → Export → choose format)
2. Connect to computer via USB
3. Run sync script to copy `Exported Annotations/` to vault

### Option C: Web Portal (Manual)

1. Access https://www.kobo.com/us/en/library/notebooks
2. Manually download notebooks
3. Move to Obsidian vault

---

## Comparison Table

| Approach | Feasibility | Automation Level | Notes |
|----------|-------------|------------------|-------|
| USB + raw `.nebo` extraction | ❌ Blocked | None | Proprietary binary format |
| USB + pre-exported files | ✅ Works | Semi-auto (udev + script) | Requires on-device export first |
| Cloud API | ❌ No API | None | No public API exists |
| Cloud scraping | ⚠️ Difficult | Manual login required | CAPTCHA blocks automation |
| **Dropbox sync** | ✅ Native | Full auto | Best option |

---

## Tools and Resources

### For Text Highlights (SQLite-based)

- [Kobo Highlights Importer](https://www.obsidianstats.com/plugins/obsidian-kobo-highlights-importer-plugin) - Obsidian plugin
- [kobo-to-obsidian-import](https://github.com/chrisbrasington/kobo-to-obsidian-import) - Python, Obsidian-formatted
- [export-kobo](https://github.com/pettarin/export-kobo) - Python, multiple formats
- [kobo-annotation-exporter](https://github.com/Moonire/kobo-annotation-exporter) - Markdown export
- [Epubor KClippings](https://www.epubor.com/kclippings.html) - GUI app, exports to Markdown/Notion
- [kobohighlightsexport.com](https://kobohighlightsexport.com/) - Web-based export

### For Device Management

- [KoboCloud](https://github.com/fsantini/KoboCloud) - Cloud sync scripts for Kobo
- [kobo (kevinboone)](https://github.com/kevinboone/kobo) - Linux CLI management tool

### File Format Research

- [Xournal++ nebo issue](https://github.com/xournalpp/xournalpp/issues/5730) - Details on `.nebo` internal structure
- [MyScript Developer](https://developer.myscript.com/) - JIIX format documentation

---

## Troubleshooting: Export Hangs/Spins Indefinitely

### Known Issue

The built-in notebook export feature on Kobo Sage/Elipsa can hang indefinitely, spinning without completing. This is a documented issue in the community.

### Likely Causes

1. **WiFi/Network instability** - Cloud exports (Dropbox/Google Drive) require stable connection
2. **Large notebook size** - Complex notebooks with many pages can timeout
3. **Firmware bugs** - Some firmware versions have known export issues
4. **Corrupted notebook** - The notebook file itself may have become corrupted
5. **Incorrect date/time** - Sync issues can occur if device date is wrong

### Workarounds

#### Option 1: USB Direct Copy (Safest - Preserves Raw Data)

Instead of using the built-in export, copy the raw `.nebo` files directly:

```bash
# Connect Kobo via USB, then:
KOBO="/run/media/$USER/KOBOeReader"
BACKUP="$HOME/kobo-backups/$(date +%Y-%m-%d)"
mkdir -p "$BACKUP"
find "$KOBO" -name "*.nebo" -exec cp {} "$BACKUP/" \;
```

These `.nebo` files can be restored later if you need to factory reset.

#### Option 2: Kobo Note Up (Browser-Based)

[Kobo Note Up](https://kobo-up.runawayup.com) - Web tool that reads directly from SQLite database:
- No software install needed
- Works locally via WebAssembly (privacy-safe)
- Bypasses Kobo's buggy export function
- Exports to Markdown or plain text

**Note:** Works for text highlights/annotations. Handwritten notebooks in `.nebo` format require different handling.

#### Option 3: Export via Computer

If on-device export hangs, use USB + SQLite tools:
1. Connect via USB
2. Copy `.kobo/KoboReader.sqlite`
3. Use [export-kobo](https://github.com/pettarin/export-kobo) for text annotations

### Basic Troubleshooting Steps

```
1. Force restart: Hold power button for 40 seconds
2. Check firmware: Settings → Device Information → ensure latest version
3. Check date/time: Incorrect date can cause sync failures
4. Try smaller export: Export single page instead of full notebook
5. Try different format: PNG instead of PDF, etc.
6. Check WiFi: Ensure stable connection for cloud exports
```

### If Notebooks Become Corrupted

Per [MobileRead forums](https://www.mobileread.com/forums/showthread.php?t=346907):
- Try opening the `.nebo` file in the standalone [MyScript Notes app](https://www.myscript.com/notes/) (more robust parser than Kobo's built-in)
- Contact Kobo support if device is under warranty

### Prevention: Regular Backups

Always backup `.nebo` files via USB regularly:

```bash
#!/bin/bash
# kobo-backup.sh - Run periodically or via udev on mount
KOBO="/run/media/$USER/KOBOeReader"
BACKUP_DIR="$HOME/kobo-backups"
TIMESTAMP=$(date +%Y-%m-%d_%H%M%S)

if [ -d "$KOBO" ]; then
    mkdir -p "$BACKUP_DIR/$TIMESTAMP"

    # Backup notebooks
    find "$KOBO" -name "*.nebo" -exec cp {} "$BACKUP_DIR/$TIMESTAMP/" \;

    # Backup database (for highlights/annotations)
    cp "$KOBO/.kobo/KoboReader.sqlite" "$BACKUP_DIR/$TIMESTAMP/" 2>/dev/null

    echo "Backup complete: $BACKUP_DIR/$TIMESTAMP"
else
    echo "Kobo not mounted at $KOBO"
fi
```

### Related Forum Threads

- [Elipsa Note-taking freezing](https://www.mobileread.com/forums/showthread.php?t=344400)
- [Elipsa crashing and corrupting notebooks](https://www.mobileread.com/forums/showthread.php?t=346907)
- [Fix common Kobo eReader problems](https://help.kobo.com/hc/en-us/articles/360017605134-Fix-common-Kobo-eReader-problems)

---

## Future Possibilities

1. **Reverse engineering `.nebo`** - Community effort to decode `ink.bink` binary format
2. **Kobo API** - Kobo may add notebook API in future updates
3. **MyScript JIIX** - If MyScript provides easier access to conversion tools
4. **Alternative firmware** - Custom Kobo firmware might expose raw stroke data

---

## References

- [Kobo Help: Use your eReader as a notebook](https://help.kobo.com/hc/en-us/articles/360062226733-Use-your-Kobo-eReader-as-a-notebook)
- [Kobo Help: Export annotations](https://help.kobo.com/hc/en-us/articles/29991333812631-Export-annotations-from-your-books)
- [MobileRead Forums: Kobo filesystem](https://www.mobileread.com/forums/showthread.php?t=331863)
- [Linux Magazine: Extract Kobo annotations](https://www.linux-magazine.com/Online/Blogs/Productivity-Sauce/Extract-Highlights-and-Annotations-from-Kobo-Ebook-Reader)

---

*Research conducted: 2026-01-02*

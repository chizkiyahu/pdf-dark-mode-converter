# PDF Dark Mode Batch Converter

A Python GUI application for batch converting PDFs to dark mode with vector-based processing that preserves text quality and searchability.

## Features

- **Vector-based conversion** - Preserves text quality and searchability
- **Batch processing** - Convert entire folder trees automatically
- **Smart file tracking** - Only converts files that are newer than existing dark mode versions
- **Quick scan** - One-click conversion of configured job folder
- **Dry run mode** - Preview what will be converted before processing
- **CNC folder exclusion** - Automatically skips CNC subfolders
- **Detailed statistics** - Shows converted vs skipped file counts

## Installation

1. Install Python 3.9 or higher
2. Install dependencies:
   ```bash
   pip install -r backend\requirements.txt
   ```

## Usage

### Launch the GUI

**Windows:**
- Double-click `Launch PDF Dark Mode Converter.bat`

**Command line:**
```bash
python batch_converter_gui.py
```

### Quick Scan

1. Click **"Quick Scan Ready Jobs"** to automatically process the configured folder
2. Default path: `Y:/Ready Jobs` (configurable in Settings)
3. Conversion starts automatically

### Manual Selection

1. Click **"Browse..."** to select a folder
2. Click **"Convert All PDFs"** to start processing

### Settings

- Click **"Settings..."** to configure the quick scan path
- Set your preferred parent job folder location

## How It Works

1. Scans the selected folder and all subfolders
2. For each PDF found:
   - Creates a "DARK MODE" subfolder in the job folder
   - Checks if the PDF needs conversion (newer source file)
   - Converts using vector-based processing (preserves text quality)
   - Maintains the original folder structure
3. Skips:
   - Files already converted (unless source is newer)
   - CNC subfolders
   - DARK MODE folders (prevents reprocessing)

## Example Folder Structure

**Before:**
```
Y:\Ready Jobs\
  └── 272 - CINDY GOTTS\
      ├── 272 - ASSEMBLY SHEETS.pdf
      ├── 272 - COVER SHEET.pdf
      └── subfolder\
          └── document.pdf
```

**After:**
```
Y:\Ready Jobs\
  └── 272 - CINDY GOTTS\
      ├── 272 - ASSEMBLY SHEETS.pdf
      ├── 272 - COVER SHEET.pdf
      ├── subfolder\
      │   └── document.pdf
      └── DARK MODE\
          ├── 272 - ASSEMBLY SHEETS.pdf
          ├── 272 - COVER SHEET.pdf
          └── subfolder\
              └── document.pdf
```

## Technical Details

- **PDF Processing**: pikepdf + reportlab for vector-based conversion
- **Color Transformation**: HSV color space for hue-preserving brightening
- **Background**: True Black (RGB 0,0,0) underlay
- **Text Handling**: Preserves all text encoding and searchability
- **Threading**: Background processing keeps GUI responsive

## Requirements

- Python 3.9+
- pikepdf >= 8.0.0
- reportlab
- tkinter (included with Python)

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for more details.

## Credits

Based on [pdf-dark-mode-converter](https://github.com/Chizkiyahu/pdf-dark-mode-converter) by Chizkiyahu

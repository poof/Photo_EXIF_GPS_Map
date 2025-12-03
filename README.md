# 照片 EXIF 資訊擷取專案 v1.1.0

本專案旨在掃描指定資料夾中的所有照片與影片，擷取其 EXIF 或中繼資料，並將其儲存到 SQLite 資料庫中，最終生成一個互動式的地圖來呈現媒體的地理位置。

## 主要功能

*   **圖形與命令列雙介面**:
    *   提供完整的圖形化介面 (GUI)，可透過點擊按鈕執行所有核心功能。
    *   同時保留傳統的命令列介面 (CLI) 供進階使用者操作。
*   **智慧媒體掃描**:
    *   遞迴掃描資料夾，並自動跳過已存在於資料庫中的檔案，僅處理新檔案。
    *   支援共 16 種檔案類型，包含 14 種圖片格式 (JPG, TIFF, HEIC, PNG, ARW, CR2, CR3, DNG, NEF, ORF, RAF, RW2, PEF) 及 2 種影片格式 (MP4, MOV)。
*   **詳細資料擷取與儲存**:
    *   從照片中擷取 EXIF 中繼資料 (如：拍攝日期、相機型號、GPS座標、ISO、光圈、快門速度等)。
    *   若無 EXIF，則讀取影片或檔案的最後修改日期作為拍攝日期。
    *   所有資訊儲存於單一的 SQLite 資料庫檔案 (`data/photo_exif.db`) 中，方便管理與備份。
*   **互動式地圖生成**:
    *   將帶有 GPS 座標的媒體在世界地圖上以聚合點形式呈現。
    *   地圖上的點位在滑鼠懸停時，會顯示該媒體的 **日期、相機型號與檔名**。
    *   提供強大的側邊欄，包含 **單一檢視**、**照片/影片牆**、**熱力圖** 等多種模式。
    *   可根據 **年、月、日、相機型號** 篩選地圖上的媒體。
*   **多國語言支援**:
    *   圖形介面與產生的地圖均支援多國語言，包含：**正體中文、英文、日文、德文、法文、西班牙文、葡萄牙文、俄文**。

## 使用方法

1.  **安裝相依套件:**
    ```bash
    pip install -r requirements.txt
    ```

2.  **執行主腳本:**
    ```bash
    # 啟動 CLI 介面
    python photo_manager.py

    # 啟動 GUI 介面
    python photo_manager.py --gui
    ```

## 資料庫結構

資料庫檔案位於 `data/photo_exif.db`。

## 致謝

本專案使用 OpenStreetMap 圖資，感謝其對開源地圖的貢獻。

---

# Photo EXIF Map v1.1.0

This project scans a directory of photos and videos, extracts their EXIF metadata, stores it in a SQLite database, and finally generates an interactive map to visualize the geographic locations of the media.

## Main Features

*   **Dual Interface (GUI & CLI)**:
    *   Offers a full Graphical User Interface (GUI) to perform all core functions via button clicks.
    *   Retains a traditional Command-Line Interface (CLI) for advanced users.
*   **Smart Media Scanning**:
    *   Recursively scans folders and automatically skips files that already exist in the database, processing only new ones.
    *   Supports 16 file types, including 14 image formats (JPG, TIFF, HEIC, PNG, ARW, CR2, CR3, DNG, NEF, ORF, RAF, RW2, PEF) and 2 video formats (MP4, MOV).
*   **Detailed Data Extraction & Storage**:
    *   Extracts EXIF metadata from photos (e.g., date taken, camera model, GPS coordinates, ISO, aperture, shutter speed).
    *   Uses the file's modification date for videos or files without an EXIF date.
    *   All information is stored in a single SQLite database file (`data/photo_exif.db`) for easy management and backup.
*   **Interactive Map Generation**:
    *   Visualizes media with GPS coordinates as clustered points on a world map.
    *   Hovering over a point on the map displays the media's **date, camera model, and filename**.
    *   Includes a powerful sidebar with multiple modes: **Single View**, **Photo/Video Wall**, and **Heatmap**.
    *   Allows filtering media on the map by **year, month, day, and camera model**.
*   **Multi-language Support**:
    *   The GUI and the generated map support multiple languages, including: **English, Traditional Chinese (正體中文), Japanese, German, French, Spanish, Portuguese, and Russian**.

## How to Use

1.  **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

2.  **Run the Main Script:**
    ```bash
    # For CLI interface
    python photo_manager.py
    
    # For GUI interface
    python photo_manager.py --gui
    ```

## Database Structure

The database file is located at `data/photo_exif.db`.

## Acknowledgments

This project utilizes OpenStreetMap data, and we are grateful for their invaluable contribution to open-source mapping.
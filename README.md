# 照片 EXIF 資訊擷取專案 (Release)

本專案旨在掃描指定資料夾中的所有照片與影片，擷取其 EXIF 或中繼資料，並將其儲存到 SQLite 資料庫中。此版本為單一整合腳本，方便部署與執行。

## 功能

*   遞迴掃描指定資料夾中的所有圖片檔案 (JPEG, TIFF, HEIC, PNG, and various RAW formats) 與影片檔案 (.mp4, .mov)。
*   **智慧掃描**: 再次掃描時，會自動跳過資料庫中已存在的檔案，僅處理新檔案。
*   擷取照片的 EXIF 資訊，或影片的檔案修改日期作為拍攝日期。
*   將擷取到的資訊儲存到 SQLite 資料庫中。
*   提供互動式選單，整合掃描、搜尋、地圖生成等功能。

## 使用方法

1.  **安裝相依套件:**

    ```bash
    pip install -r requirements.txt
    ```

2.  **執行主腳本:**

    ```bash
    python photo_manager.py
    ```

    腳本會顯示一個選單，您可以根據提示選擇要執行的操作：
    *   **1. 掃描媒體資料夾**: 將新的照片和影片加入資料庫。
    *   **2. 互動式搜尋資料庫**: 根據相機、日期、ISO 等條件查詢資料。
    *   **3. 產生 HTML 地圖**: 根據資料庫中的內容生成一個 `output/photo_map.html` 檔案。

## 產生照片地圖

您可以透過主選單中的選項 `3` 來產生互動式地圖。

### 地圖功能

*   **互動式地圖:** 照片與影片會以聚合點的形式顯示在地圖上。
*   **篩選功能:**
    *   您可以根據 **年**、**月**、**日** 和 **相機型號** 來篩選媒體。
    *   **顯示沒有定位的照片:** 篩選有或沒有原生 GPS 座標的媒體。
*   **側邊欄:**
    *   **可自由調整寬度**。
    *   **單一檢視:** 顯示照片預覽或影片播放器及詳細資訊。
    *   **照片牆/影片牆:** 以網格形式顯示照片或影片，影片支援懸停預覽。
    *   **熱力圖/統計:** 提供視覺化的數據分析圖表。

## 資料庫結構

資料庫檔案位於 `data/photo_exif.db`，結構與開發版相同。

## 致謝

本專案使用 OpenStreetMap 圖資，感謝其對開源地圖的貢獻。

---

# Photo EXIF Map (Release)

This project is a Photo EXIF and GPS Data Extractor and Map Visualizer.

It scans a directory of photos and videos, extracts their EXIF metadata (such as camera model, date taken, and GPS coordinates), and stores this information in a SQLite database. It then generates an interactive HTML map to visualize the locations where the photos were taken.

## Features

*   **Recursive Scanning:** Scans all image files (JPEG, TIFF, HEIC, PNG, and various RAW formats) and video files (.mp4, .mov) in the specified folder.
*   **Smart Scan:** When scanning again, it automatically skips files that already exist in the database and only processes new files.
*   **EXIF Extraction:** Captures EXIF information from photos or the file modification date of videos as the shooting date.
*   **Database Storage:** Saves the captured information into a SQLite database.
*   **Interactive Menu:** Provides an integrated menu for scanning, searching, map generation, and other functions.

## How to Use

1.  **Install Dependencies:**

    ```bash
    pip install -r requirements.txt
    ```

2.  **Run the Main Script:**

    ```bash
    python photo_manager.py
    ```

    The script will display a menu, and you can choose the operation to perform based on the prompts:
    *   **1. Scan Media Folder**: Add new photos and videos to the database.
    *   **2. Interactive Database Search**: Query data based on camera, date, ISO, and other criteria.
    *   **3. Generate HTML Map**: Generate an `output/photo_map.html` file based on the content in the database.

## Generate Photo Map

You can generate an interactive map through option `3` in the main menu.

### Map Features

*   **Interactive Map:** Photos and videos are displayed on the map as clustered points.
*   **Filtering:**
    *   You can filter media by **year**, **month**, **day**, and **camera model**.
    *   **Show photos without location:** Filter media with or without native GPS coordinates.
*   **Sidebar:**
    *   **Freely adjustable width**.
    *   **Single View:** Displays a photo preview or video player and detailed information.
    *   **Photo Wall/Video Wall:** Displays photos or videos in a grid format, with video hover-to-preview support.
    *   **Heatmap/Statistics:** Provides visual data analysis charts.

## Database Structure

The database file is located at `data/photo_exif.db`, and its structure is the same as the development version.

## Acknowledgments

This project utilizes OpenStreetMap data, and we are grateful for their invaluable contribution to open-source mapping.

import os
import sys
import multiprocessing
import sqlite3
import json
import datetime
import exifread
from tqdm import tqdm
import pandas as pd
from collections import Counter

# ==============================================================================
# 1. EXIF EXTRACTION LOGIC (from src/exif_extractor.py)
# ==============================================================================

class ExifExtractor:
    """A class to extract EXIF data from a single image file."""
    def __init__(self, file_path):
        """Initializes the ExifExtractor.

        Args:
            file_path (str): The absolute path to the image file.
        """
        self.file_path = file_path
        self.tags = {}

    def _get_tag_value(self, tag_name):
        """Safely retrieves a tag value from the extracted tags."""
        if tag_name in self.tags:
            return self.tags[tag_name].values
        return None

    def _get_gps_latitude(self):
        """Extracts and converts GPS latitude to degrees."""
        lat = None
        lat_ref = None
        if 'GPS GPSLatitude' in self.tags:
            lat = self.tags['GPS GPSLatitude'].values
        if 'GPS GPSLatitudeRef' in self.tags and self.tags['GPS GPSLatitudeRef'].values:
            lat_ref = self.tags['GPS GPSLatitudeRef'].values[0]

        if lat and lat_ref:
            return self._convert_to_degrees(lat), lat_ref
        return None, None

    def _get_gps_longitude(self):
        """Extracts and converts GPS longitude to degrees."""
        lon = None
        lon_ref = None
        if 'GPS GPSLongitude' in self.tags:
            lon = self.tags['GPS GPSLongitude'].values
        if 'GPS GPSLongitudeRef' in self.tags and self.tags['GPS GPSLongitudeRef'].values:
            lon_ref = self.tags['GPS GPSLongitudeRef'].values[0]

        if lon and lon_ref:
            return self._convert_to_degrees(lon), lon_ref
        return None, None

    def _convert_to_degrees(self, value):
        """Converts GPS coordinate values (degrees, minutes, seconds) to decimal degrees."""
        try:
            d = float(value[0].num) / float(value[0].den)
            m = float(value[1].num) / float(value[1].den)
            s = float(value[2].num) / float(value[2].den)
            return d + (m / 60.0) + (s / 3600.0)
        except (ZeroDivisionError, IndexError):
            return None

    def extract(self):
        """Extracts all relevant EXIF data from the image file.

        If no EXIF date is found, it falls back to the file's modification time.

        Returns:
            dict: A dictionary containing the extracted EXIF data.
        """
        with open(self.file_path, 'rb') as f:
            # Suppress warnings from exifread
            original_stderr = sys.stderr
            sys.stderr = open(os.devnull, 'w')
            try:
                self.tags = exifread.process_file(f, details=False)
            finally:
                sys.stderr.close()
                sys.stderr = original_stderr


        date_taken = self._get_tag_value('EXIF DateTimeOriginal')
        if not date_taken:
            try:
                date_taken = datetime.datetime.fromtimestamp(os.path.getmtime(self.file_path)).strftime('%Y:%m:%d %H:%M:%S')
            except Exception:
                date_taken = None
        else:
            date_taken = str(date_taken)

        camera_model = self._get_tag_value('Image Model')
        if camera_model:
            camera_model = str(camera_model).strip()

        lat, lat_ref = self._get_gps_latitude()
        lon, lon_ref = self._get_gps_longitude()

        if lat is not None and lat_ref and lon is not None and lon_ref:
            if lat_ref == 'S':
                lat = -lat
            if lon_ref == 'W':
                lon = -lon
        else:
            lat, lon = None, None


        altitude = self._get_tag_value('GPS GPSAltitude')
        if altitude and altitude[0].den != 0:
            altitude = round(float(altitude[0].num) / float(altitude[0].den))
        else:
            altitude = None

        iso = self._get_tag_value('EXIF ISOSpeedRatings')
        if iso and iso:
            iso = iso[0]
        else:
            iso = None

        aperture = self._get_tag_value('EXIF FNumber')
        if aperture and aperture[0].den != 0:
            try:
                aperture_val = float(aperture[0].num) / float(aperture[0].den)
                aperture = f"f/{aperture_val}"
            except ZeroDivisionError:
                aperture = None
        else:
            aperture = None

        shutter_speed = self._get_tag_value('EXIF ExposureTime')
        if shutter_speed and shutter_speed[0].den != 0:
            try:
                shutter_speed_val = float(shutter_speed[0].num) / float(shutter_speed[0].den)
                if shutter_speed_val < 1:
                    denominator = round(1 / shutter_speed_val)
                    shutter_speed = f"1/{denominator}s"
                else:
                    shutter_speed = f"{int(shutter_speed_val)}s"
            except ZeroDivisionError:
                shutter_speed = "0s"
        else:
            shutter_speed = None

        focal_length = self._get_tag_value('EXIF FocalLength')
        if focal_length and focal_length[0].den != 0:
            try:
                focal_length_val = focal_length[0].num / focal_length[0].den
                focal_length = f"{focal_length_val}mm"
            except ZeroDivisionError:
                focal_length = None
        else:
            focal_length = None

        return {
            'date_taken': date_taken,
            'file_path': self.file_path,
            'camera_model': camera_model,
            'gps_latitude': lat,
            'gps_longitude': lon,
            'gps_altitude': altitude,
            'iso': iso,
            'aperture': aperture,
            'shutter_speed': shutter_speed,
            'focal_length': focal_length
        }

# ==============================================================================
# 2. DATABASE HANDLER LOGIC (from src/database_handler.py)
# ==============================================================================

class DatabaseHandler:
    """Manages the connection and operations for the EXIF data database."""
    def __init__(self, db_name, buffer_size=500):
        self.db_name = db_name
        self.conn = None
        self.buffer = []
        self.buffer_size = buffer_size

    def flush_buffer(self):
        if not self.conn:
            self.create_connection()
        if not self.conn or not self.buffer:
            return

        sql = ''' INSERT OR IGNORE INTO exif_data(date_taken,file_path,camera_model,gps_latitude,gps_longitude,gps_altitude,iso,aperture,shutter_speed,focal_length)
                  VALUES(?,?,?,?,?,?,?,?,?,?) '''
        try:
            cur = self.conn.cursor()
            data_to_insert = [list(item.values()) for item in self.buffer]
            cur.executemany(sql, data_to_insert)
            self.conn.commit()
            self.buffer = []
        except Exception as e:
            print(f"Error flushing buffer: {e}")

    def create_connection(self):
        try:
            self.conn = sqlite3.connect(self.db_name)
        except sqlite3.Error as e:
            print(f"Database connection error: {e}")
            self.conn = None

    def close_connection(self):
        if self.conn:
            self.conn.close()
            self.conn = None

    def create_table(self):
        if not self.conn:
            self.create_connection()
        if not self.conn: return

        create_table_sql = """CREATE TABLE IF NOT EXISTS exif_data (
                                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                                    date_taken TEXT,
                                    file_path TEXT NOT NULL UNIQUE,
                                    camera_model TEXT,
                                    gps_latitude REAL,
                                    gps_longitude REAL,
                                    gps_altitude INTEGER,
                                    iso INTEGER,
                                    aperture TEXT,
                                    shutter_speed TEXT,
                                    focal_length TEXT
                                );"""
        try:
            c = self.conn.cursor()
            c.execute(create_table_sql)
        except sqlite3.Error as e:
            print(e)

    def insert_exif_data(self, exif_data):
        self.buffer.append(exif_data)
        if len(self.buffer) >= self.buffer_size:
            self.flush_buffer()

    def get_photos(self, start_date=None, end_date=None, camera_filter=None, allowed_extensions=None):
        self.create_connection()
        if not self.conn: return []

        query = "SELECT file_path, gps_latitude, gps_longitude, camera_model, date_taken FROM exif_data"
        conditions = []
        params = []

        if start_date and end_date:
            conditions.append("date_taken BETWEEN ? AND ?")
            params.extend([start_date, end_date])
        
        if camera_filter:
            conditions.append("camera_model = ?")
            params.append(camera_filter)

        if allowed_extensions:
            ext_conditions = " OR ".join([f"file_path LIKE ?" for _ in allowed_extensions])
            conditions.append(f"({ext_conditions})")
            params.extend([f"%{ext}" for ext in allowed_extensions])

        if conditions:
            query += " WHERE " + " AND ".join(conditions)
            
        query += " ORDER BY date_taken"

        try:
            self.conn.row_factory = sqlite3.Row
            cursor = self.conn.cursor()
            cursor.execute(query, params)
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        finally:
            self.close_connection()

    def count_photos(self, start_date=None, end_date=None, camera_filter=None, allowed_extensions=None):
        self.create_connection()
        if not self.conn: return 0

        query = "SELECT COUNT(*) FROM exif_data"
        conditions = []
        params = []

        if start_date and end_date:
            conditions.append("date_taken BETWEEN ? AND ?")
            params.extend([start_date, end_date])

        if camera_filter:
            conditions.append("camera_model = ?")
            params.append(camera_filter)

        if allowed_extensions:
            ext_conditions = " OR ".join([f"file_path LIKE ?" for _ in allowed_extensions])
            conditions.append(f"({ext_conditions})")
            params.extend([f"%{ext}" for ext in allowed_extensions])

        if conditions:
            query += " WHERE " + " AND ".join(conditions)
            
        try:
            cursor = self.conn.cursor()
            cursor.execute(query, params)
            count = cursor.fetchone()[0]
            return count
        finally:
            self.close_connection()

    def get_all_paths(self):
        self.create_connection()
        if not self.conn: return set()
        try:
            cursor = self.conn.cursor()
            cursor.execute("SELECT file_path FROM exif_data")
            return {row[0] for row in cursor.fetchall()}
        finally:
            self.close_connection()

    def get_unique_camera_models(self):
        self.create_connection()
        if not self.conn: return []
        try:
            cursor = self.conn.cursor()
            cursor.execute("SELECT DISTINCT camera_model FROM exif_data WHERE camera_model IS NOT NULL ORDER BY camera_model")
            return [row[0] for row in cursor.fetchall()]
        finally:
            self.close_connection()

    def clean_db(self, confirmed=False, output_stream=sys.stdout):
        self.create_connection()
        if not self.conn:
            return

        try:
            cursor = self.conn.cursor()
            cursor.execute("SELECT id, file_path FROM exif_data")
            records = cursor.fetchall()
            
            print(f"Checking {len(records)} records from the database...", file=output_stream)
            non_existent_ids = []
            for record_id, file_path in tqdm(records, desc="Scanning for missing files", unit=" record", file=output_stream, mininterval=0.5):
                if not os.path.exists(file_path):
                    non_existent_ids.append((record_id,))
            
            if non_existent_ids:
                print(f"\nFound {len(non_existent_ids)} non-existent photo records to delete.", file=output_stream)
                if confirmed:
                    cursor.executemany("DELETE FROM exif_data WHERE id = ?", non_existent_ids)
                    self.conn.commit()
                    print(f"Successfully deleted {len(non_existent_ids)} records.", file=output_stream)
                else:
                    print("Deletion cancelled. Pass confirmed=True to delete.", file=output_stream)
            else:
                print("\nDatabase is clean. No non-existent photo records found.", file=output_stream)

        except Exception as e:
            print(f"An error occurred during database cleaning: {e}", file=output_stream)
        finally:
            self.close_connection()

# ==============================================================================
# 3. PHOTO SCANNING LOGIC (from main.py)
# ==============================================================================

def process_file(file_path):
    """Worker function to process a single image or video file."""
    file_ext = os.path.splitext(file_path)[1].lower()
    image_extensions = ('.jpg', '.jpeg', '.tiff', '.heic', '.png', '.arw', '.cr2', '.cr3', '.dng', '.nef', '.orf', '.raf', '.rw2', '.pef')
    video_extensions = ('.mp4', '.mov')

    if file_ext in image_extensions:
        try:
            extractor = ExifExtractor(file_path)
            exif_data = extractor.extract()
            if all(value is None for key, value in exif_data.items() if key not in ['file_path', 'date_taken']):
                return {'file_path': file_path, 'no_exif': True, 'data': exif_data}
            return {'data': exif_data}
        except Exception as e:
            return {'file_path': file_path, 'error': str(e)}
    
    elif file_ext in video_extensions:
        try:
            date_taken = datetime.datetime.fromtimestamp(os.path.getmtime(file_path)).strftime('%Y:%m:%d %H:%M:%S')
            return {
                'data': {
                    'date_taken': date_taken, 'file_path': file_path, 'camera_model': 'Video',
                    'gps_latitude': None, 'gps_longitude': None, 'gps_altitude': None, 'iso': None,
                    'aperture': None, 'shutter_speed': None, 'focal_length': None
                }
            }
        except Exception as e:
            return {'file_path': file_path, 'error': str(e)}
    
    return None

class PhotoScanner:
    """Manages the workflow of scanning a directory and populating the database."""
    def __init__(self, db_path, stop_event=None, output_stream=sys.stdout):
        self.db_path = db_path
        self.db_handler = DatabaseHandler(self.db_path, buffer_size=100)
        self.db_handler.create_table()
        self.stop_event = stop_event
        self.output_stream = output_stream

    def _get_files_to_process(self, media_directories):
        print(f"Scanning directories: {', '.join(media_directories)}", file=self.output_stream)
        
        all_files_on_disk = []
        for media_directory in media_directories:
            all_files_on_disk.extend([os.path.join(root, file) for root, _, files in os.walk(media_directory) for file in files if file.lower().endswith(('.jpg', '.jpeg', '.tiff', '.heic', '.png', '.arw', '.cr2', '.cr3', '.dng', '.nef', '.orf', '.raf', '.rw2', '.pef', '.mp4', '.mov'))])
        all_files_on_disk.sort()

        existing_paths = self.db_handler.get_all_paths()
        print(f"Found {len(existing_paths)} records in the database.", file=self.output_stream)

        files_to_process = [f for f in all_files_on_disk if f not in existing_paths]
        
        print(f"Total media files found on disk: {len(all_files_on_disk)}.", file=self.output_stream)
        print(f"{len(files_to_process)} new media files to be added to the database.", file=self.output_stream)
        
        return files_to_process

    def scan_directories_multiprocess(self, media_directories, num_processes):
        files_to_process = self._get_files_to_process(media_directories)

        if not files_to_process:
            print("No new media to add to the database.", file=self.output_stream)
            return

        no_exif_count = 0
        error_count = 0
        processed_count = 0

        with multiprocessing.Pool(processes=num_processes) as pool:
            with tqdm(total=len(files_to_process), unit="file", desc="Processing new files (Multiprocess)", file=self.output_stream, mininterval=0.5) as pbar:
                for result in pool.imap_unordered(process_file, files_to_process):
                    if self.stop_event and self.stop_event.is_set():
                        print("\nScan stopped by user. Terminating worker processes...", file=self.output_stream)
                        pool.terminate()
                        break
                    if result:
                        if result.get('error'):
                            error_count += 1
                        elif result.get('no_exif'):
                            no_exif_count += 1
                            self.db_handler.insert_exif_data(result['data'])
                            processed_count += 1
                        elif 'data' in result:
                            self.db_handler.insert_exif_data(result['data'])
                            processed_count += 1
                    pbar.update(1)

        self.db_handler.flush_buffer()

        print(f"\n--- Processing Summary ---", file=self.output_stream)
        print(f"New media files processed and saved: {processed_count}", file=self.output_stream)
        print(f"New images without full EXIF data (using modification time): {no_exif_count}", file=self.output_stream)
        print(f"New media files with processing errors: {error_count}", file=self.output_stream)

    def scan_directories_single_thread(self, media_directories):
        files_to_process = self._get_files_to_process(media_directories)

        if not files_to_process:
            print("No new media to add to the database.", file=self.output_stream)
            return

        no_exif_count = 0
        error_count = 0
        processed_count = 0

        with tqdm(total=len(files_to_process), unit="file", desc="Processing new files (Single-thread)", file=self.output_stream, mininterval=0.5) as pbar:
            for file_path in files_to_process:
                if self.stop_event and self.stop_event.is_set():
                    print("\nScan stopped by user.", file=self.output_stream)
                    break
                result = process_file(file_path)
                if result:
                    if result.get('error'):
                        error_count += 1
                    elif result.get('no_exif'):
                        no_exif_count += 1
                        self.db_handler.insert_exif_data(result['data'])
                        processed_count += 1
                    elif 'data' in result:
                        self.db_handler.insert_exif_data(result['data'])
                        processed_count += 1
                pbar.update(1)

        self.db_handler.flush_buffer()
        
        print(f"\n--- Processing Summary ---", file=self.output_stream)
        print(f"New media files processed and saved: {processed_count}", file=self.output_stream)
        print(f"New images without full EXIF data (using modification time): {no_exif_count}", file=self.output_stream)
        print(f"New media files with processing errors: {error_count}", file=self.output_stream)

# ==============================================================================
# 4. MAP GENERATION LOGIC (from generate_map.py)
# ==============================================================================

class MapGenerator:
    """Generates an HTML map from a list of photo data."""
    def __init__(self, locations, template_file, output_html_file, db_name, output_stream=sys.stdout):
        self.locations = locations
        self.template_file = template_file
        self.output_html_file = output_html_file
        self.db_name = db_name
        self.output_stream = output_stream

    def _generate_html(self):
        camera_models = sorted(list(set(loc['camera_model'] for loc in self.locations if loc['camera_model'])))
        camera_model_map = {model: i for i, model in enumerate(camera_models)}
        
        processed_locations = []
        keys = ["date_taken", "gps_latitude", "gps_longitude", "camera_model", "file_path_web"]
        
        for loc in self.locations:
            if loc.get('date_taken'):
                date_str = loc['date_taken']
                loc['date_taken'] = date_str[0:10].replace(':', '-') + date_str[10:]
            
            if loc.get('gps_latitude') is not None:
                loc['gps_latitude'] = round(loc['gps_latitude'], 6)
            if loc.get('gps_longitude') is not None:
                loc['gps_longitude'] = round(loc['gps_longitude'], 6)

            if loc.get('gps_latitude') == 0.0 and loc.get('gps_longitude') == 0.0:
                loc['gps_latitude'] = None
                loc['gps_longitude'] = None
            
            loc['file_path_web'] = loc['file_path'].replace('\\', '/')
            
            camera_model_index = None
            if loc.get('camera_model') in camera_model_map:
                camera_model_index = camera_model_map[loc['camera_model']]
            
            processed_locations.append([
                loc.get('date_taken'), loc.get('gps_latitude'), loc.get('gps_longitude'),
                camera_model_index, loc.get('file_path_web')
            ])

        locations_json = json.dumps(processed_locations, separators=(',', ':'))
        keys_json = json.dumps(keys, separators=(',', ':'))
        cameras_json = json.dumps(camera_models, separators=(',', ':'))

        try:
            with open(self.template_file, 'r', encoding='utf-8') as f:
                template_content = f.read()
        except FileNotFoundError:
            print(f"Error: Template file not found at {self.template_file}", file=self.output_stream)
            return None

        html_content = template_content.replace('__KEYS_JSON__', keys_json)
        html_content = html_content.replace('__CAMERAS_JSON__', cameras_json)
        html_content = html_content.replace('__LOCATIONS_JSON__', locations_json)
        return html_content

    def run(self):
        """Executes the map generation process."""
        if not self.locations:
            print("No data found in the database.", file=self.output_stream)
            return

        print(f"Found {len(self.locations)} records, generating HTML map file...", file=self.output_stream)
        html_content = self._generate_html()

        try:
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()
            cursor.execute("SELECT date_taken FROM exif_data WHERE date_taken IS NOT NULL")
            rows = cursor.fetchall()
            dates = [row[0] for row in rows]
            conn.close()

            date_counts = Counter(date.split(' ')[0].replace(':', '-') for date in dates)
            photo_counts_data = [{'date': date, 'count': count} for date, count in date_counts.items()]
            photo_counts_json = json.dumps(photo_counts_data)

            years = sorted(list(set(d.split('-')[0] for d in date_counts.keys())), reverse=True)
            heatmaps_html = ''
            for year in years:
                heatmap_id = f'cal-heatmap-{year}'
                heatmaps_html += f'<div id="{heatmap_id}" style="width: 100%; margin-bottom: 20px;"></div>'

            html_content = html_content.replace('__HEATMAPS__', heatmaps_html)
            html_content = html_content.replace('__PHOTO_COUNTS_JSON__', photo_counts_json)
            html_content = html_content.replace('__YEARS_JSON__', json.dumps(years))

        except Exception as e:
            print(f"Error generating heatmap: {e}", file=self.output_stream)

        if html_content:
            try:
                with open(self.output_html_file, 'w', encoding='utf-8') as f:
                    f.write(html_content)
                print(f"Successfully generated file: {self.output_html_file}", file=self.output_stream)
                print(f"You can open this file in your web browser to view the map.", file=self.output_stream)
            except IOError as e:
                print(f"Error writing to file: {e}", file=self.output_stream)

# ==============================================================================
# 5. DATABASE QUERY LOGIC (from scripts/search_db.py)
# ==============================================================================

class InteractiveSearch:
    def __init__(self, db_name):
        self.db_name = db_name
        self.conn = None

    def _connect(self):
        try:
            self.conn = sqlite3.connect(self.db_name)
            return True
        except sqlite3.Error as e:
            print(f"Database connection error: {e}")
            return False

    def _close(self):
        if self.conn:
            self.conn.close()

    def _get_unique_values(self, column_name):
        if not self._connect():
            return []
        try:
            df = pd.read_sql_query(f"SELECT DISTINCT {column_name} FROM exif_data WHERE {column_name} IS NOT NULL ORDER BY {column_name}", self.conn)
            return df[column_name].tolist()
        except Exception as e:
            print(f"Error querying unique values: {e}")
            return []
        finally:
            self._close()

    def _execute_query(self, query, params=()):
        if not self._connect():
            return

        try:
            df = pd.read_sql_query(query, self.conn, params=params)
            if df.empty:
                print("--- No matching data found ---")
            else:
                print(df.to_string())
        except Exception as e:
            print(f"Error during query: {e}")
        finally:
            self._close()

    def _search_by_menu(self, column_name, column_title):
        options = self._get_unique_values(column_name)
        if not options:
            print(f"No {column_title} options available in the database.")
            return

        print(f"\n--- Select {column_title} ---")
        for i, option in enumerate(options):
            print(f"{i + 1}. {option}")
        
        try:
            choice = int(input(f"Enter your choice [1-{len(options)}]: "))
            if 1 <= choice <= len(options):
                selected_option = options[choice - 1]
                query = f"SELECT * FROM exif_data WHERE {column_name} = ? ORDER BY file_path"
                self._execute_query(query, (selected_option,))
            else:
                print("Invalid choice.")
        except ValueError:
            print("Please enter a number.")

    def search_by_camera(self):
        self._search_by_menu("camera_model", "Camera Model")

    def search_by_date_range(self):
        start_date_str = input("Enter start date (YYYY-MM-DD): ")
        end_date_str = input("Enter end date (YYYY-MM-DD): ")
        try:
            start_date = start_date_str.replace('-', ':') + " 00:00:00"
            end_date = end_date_str.replace('-', ':') + " 23:59:59"
            query = "SELECT * FROM exif_data WHERE date_taken BETWEEN ? AND ? ORDER BY file_path"
            self._execute_query(query, (start_date, end_date))
        except Exception as e:
            print(f"Incorrect date format: {e}")

    def search_by_iso(self):
        self._search_by_menu("iso", "ISO Value")

    def search_by_focal_length(self):
        self._search_by_menu("focal_length", "Focal Length")

    def search_by_aperture(self):
        self._search_by_menu("aperture", "Aperture Value")

    def search_by_shutter_speed(self):
        self._search_by_menu("shutter_speed", "Shutter Speed")

    def search_by_path(self):
        path = input("Enter file path keyword: ")
        query = "SELECT * FROM exif_data WHERE file_path LIKE ? ORDER BY file_path"
        self._execute_query(query, ('%' + path + '%',))

    def show_all(self):
        query = "SELECT * FROM exif_data ORDER BY file_path"
        self._execute_query(query)

    def run(self):
        try:
            import pandas as pd
        except ImportError:
            print("\n'pandas' library not found. The search functionality is disabled.")
            print("Please install it using: pip install pandas")
            return

        while True:
            print("\n--- Interactive EXIF Database Search ---")
            print("1. By Camera Model")
            print("2. By Date Range")
            print("3. By ISO Value")
            print("4. By Focal Length")
            print("5. By Aperture Value")
            print("6. By Shutter Speed")
            print("7. By File Path")
            print("8. Show All Data")
            print("9. Exit")

            choice = input("Enter your choice [1-9]: ")

            if choice == '1': self.search_by_camera()
            elif choice == '2': self.search_by_date_range()
            elif choice == '3': self.search_by_iso()
            elif choice == '4': self.search_by_focal_length()
            elif choice == '5': self.search_by_aperture()
            elif choice == '6': self.search_by_shutter_speed()
            elif choice == '7': self.search_by_path()
            elif choice == '8': self.show_all()
            elif choice == '9': break
            else: print("Invalid choice, please try again.")

# ==============================================================================
# 6. MAIN EXECUTION AND MENU
# ==============================================================================

def scan_media_non_interactive(db_path, dir_paths, use_multiprocess, num_processes, stop_event, output_stream=sys.stdout):
    """Non-interactive version of the media scanning function."""
    valid_paths = []
    for path in dir_paths:
        if os.path.isdir(path):
            valid_paths.append(path)
        else:
            print(f"Error: '{path}' is not a valid directory. Skipping.", file=output_stream)

    if not valid_paths:
        print("No valid directories to scan.", file=output_stream)
        return
        
    scanner = PhotoScanner(db_path, stop_event=stop_event, output_stream=output_stream)
    if use_multiprocess:
        scanner.scan_directories_multiprocess(valid_paths, num_processes)
    else:
        scanner.scan_directories_single_thread(valid_paths)

def generate_map_non_interactive(db_path, template_path, output_path, start_date=None, end_date=None, camera_filter=None, allowed_extensions=None, output_stream=sys.stdout):
    """Non-interactive version of the map generation function."""
    print(f"\n--- Generate HTML Map from template: {os.path.basename(template_path)} ---", file=output_stream)
    
    start_db_format = None
    end_db_format = None

    if start_date and end_date:
        try:
            # Validate and format dates
            datetime.datetime.strptime(start_date, '%Y-%m-%d')
            datetime.datetime.strptime(end_date, '%Y-%m-%d')
            start_db_format = start_date.replace('-', ':') + " 00:00:00"
            end_db_format = end_date.replace('-', ':') + " 23:59:59"
        except ValueError:
            print("Invalid date format. Aborting.", file=output_stream)
            return

    db_handler = DatabaseHandler(db_path)
    count = db_handler.count_photos(start_db_format, end_db_format, camera_filter, allowed_extensions)
    print(f"Found {count} photos for the selected criteria.", file=output_stream)
    
    if count == 0:
        print("No photos to map. Aborting.", file=output_stream)
        return
        
    locations = db_handler.get_photos(start_db_format, end_db_format, camera_filter, allowed_extensions)
    map_gen = MapGenerator(locations, template_path, output_path, db_path, output_stream=output_stream)
    map_gen.run()

def clean_db_non_interactive(db_path, confirmed, output_stream=sys.stdout):
    """Non-interactive version of the database cleaning function."""
    print("\n--- Clean Database ---", file=output_stream)
    db_handler = DatabaseHandler(db_path)
    db_handler.clean_db(confirmed=confirmed, output_stream=output_stream)


def main_menu():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(script_dir, 'data', 'photo_exif.db')
    output_path = os.path.join(script_dir, 'output', 'photo_map.html')
    template_path_en = os.path.join(script_dir, 'web', 'map_template_en-US.html')
    template_path_zh = os.path.join(script_dir, 'web', 'map_template_zh-TW.html')
    
    os.makedirs(os.path.join(script_dir, 'data'), exist_ok=True)
    os.makedirs(os.path.join(script_dir, 'output'), exist_ok=True)
    os.makedirs(os.path.join(script_dir, 'web'), exist_ok=True)

    if '--gui' in sys.argv:
        try:
            import gui
            gui.main()
        except ImportError:
            print("Could not import the GUI module. Please ensure gui.py is in the same directory.")
        return

    # Keep old CLI menu for compatibility
    while True:
        print("\n======= Photo Manager (CLI) ========")
        print("Hint: For a graphical interface, run with the --gui flag.")
        print("1. Scan Media Directories")
        print("2. Generate HTML Map")
        print("3. Search Database (Interactive)")
        print("4. Clean Database")
        print("5. Exit")
        choice = input("Enter your choice [1-5]: ")

        if choice == '1':
            dir_paths_str = input("Enter one or more absolute paths to media directories, separated by commas: ")
            dir_paths = [path.strip() for path in dir_paths_str.split(',')]
            mode = input("Use (m)ultiprocess or (s)ingle-thread? [m]: ").lower()
            use_multiprocess = mode != 's'
            num_processes = multiprocessing.cpu_count()
            if use_multiprocess:
                try:
                    num = int(input(f"How many processes to use? (1-{num_processes}) [{num_processes}]: ") or num_processes)
                    if 1 <= num <= num_processes:
                        num_processes = num
                except ValueError:
                    pass # Keep default
            scan_media_non_interactive(db_path, dir_paths, use_multiprocess, num_processes, None)

        elif choice == '2':
            template_path = template_path_zh
            
            start_date = input("Enter start date (YYYY-MM-DD) or leave blank for all: ")
            end_date = input("Enter end date (YYYY-MM-DD) or leave blank for all: ")

            generate_map_non_interactive(db_path, template_path, output_path, start_date, end_date)

        elif choice == '3':
            searcher = InteractiveSearch(db_path)
            searcher.run()
        
        elif choice == '4':
            confirm = input("Are you sure you want to scan for and delete records of non-existent files? (y/n): ").lower()
            clean_db_non_interactive(db_path, confirmed=(confirm == 'y'))

        elif choice == '5':
            print("Exiting.")
            break
        else:
            print("Invalid choice, please try again.")

if __name__ == "__main__":
    try:
        multiprocessing.set_start_method('spawn')
    except RuntimeError:
        pass

    main_menu()
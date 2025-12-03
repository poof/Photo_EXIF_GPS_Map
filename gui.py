import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
import sys
import threading
import queue
import datetime
import multiprocessing

# Import the refactored functions and classes from photo_manager
import photo_manager

class PhotoManagerGUI(tk.Frame):
    def __init__(self, master=None):
        super().__init__(master)
        self.master = master
        self.master.title("Photo Manager GUI")
        self.pack(fill=tk.BOTH, expand=True)
        self.scanning = False
        self.stop_event = None

        # Get base paths from photo_manager
        self.script_dir = os.path.dirname(os.path.abspath(__file__))
        self.db_path = os.path.join(self.script_dir, 'data', 'photo_exif.db')
        self.output_path = os.path.join(self.script_dir, 'output', 'photo_map.html')
        self.web_dir = os.path.join(self.script_dir, 'web')

        # Create necessary directories if they don't exist
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        os.makedirs(os.path.dirname(self.output_path), exist_ok=True)

        self.create_widgets()
        self.queue = queue.Queue()
        self._after_id = self.master.after(100, self.process_queue)
        self.master.protocol("WM_DELETE_WINDOW", self.on_closing)
        self._after_id_counts = None
        self.schedule_update_counts(update_total=True)

    def on_closing(self):
        """Handles window closing event."""
        if self._after_id:
            self.master.after_cancel(self._after_id)
            self._after_id = None
        self.master.destroy()

    def create_widgets(self):
        # PanedWindow for resizable sections
        self.paned_window = ttk.PanedWindow(self, orient=tk.VERTICAL)
        self.paned_window.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Top frame for controls
        self.top_frame = ttk.Frame(self.paned_window, padding="10")
        self.paned_window.add(self.top_frame, weight=1)

        # Bottom frame for terminal output
        self.bottom_frame = ttk.LabelFrame(self.paned_window, text="Output Console", padding="10")
        self.paned_window.add(self.bottom_frame, weight=1)

        self.create_control_widgets(self.top_frame)
        self.create_terminal_widget(self.bottom_frame)

    def create_control_widgets(self, parent):
        # --- Main Control Notebook ---
        notebook = ttk.Notebook(parent)
        notebook.pack(fill=tk.BOTH, expand=True)

        # -- Scan Tab --
        scan_tab = ttk.Frame(notebook, padding="10")
        notebook.add(scan_tab, text="Scan Media")
        self.create_scan_tab(scan_tab)

        # -- Generate Map Tab --
        map_tab = ttk.Frame(notebook, padding="10")
        notebook.add(map_tab, text="Generate Map")
        self.create_map_tab(map_tab)
        
        # -- Other Actions Tab --
        other_tab = ttk.Frame(notebook, padding="10")
        notebook.add(other_tab, text="Other")
        self.create_other_tab(other_tab)

    def create_scan_tab(self, parent):
        dir_frame = ttk.LabelFrame(parent, text="Media Directories", padding="10")
        dir_frame.pack(fill=tk.X, expand=True, pady=5)

        self.dir_listbox = tk.Listbox(dir_frame)
        self.dir_listbox.pack(fill=tk.X, expand=True, side=tk.LEFT, padx=(0, 10))
        
        dir_buttons_frame = ttk.Frame(dir_frame)
        dir_buttons_frame.pack(side=tk.LEFT)

        add_dir_button = ttk.Button(dir_buttons_frame, text="Add Directory", command=self.add_directory)
        add_dir_button.pack(fill=tk.X, pady=2)
        remove_dir_button = ttk.Button(dir_buttons_frame, text="Remove Selected", command=self.remove_directory)
        remove_dir_button.pack(fill=tk.X, pady=2)

        processing_frame = ttk.LabelFrame(parent, text="Processing Options", padding="10")
        processing_frame.pack(fill=tk.X, expand=True, pady=5)

        self.processing_var = tk.StringVar(value="multiprocess")
        multiprocess_radio = ttk.Radiobutton(processing_frame, text="Multiprocess", variable=self.processing_var, value="multiprocess", command=self.toggle_process_count)
        multiprocess_radio.grid(row=0, column=0, sticky=tk.W)
        
        self.process_count_var = tk.StringVar(value=str(multiprocessing.cpu_count() or 4))
        self.process_count_combo = ttk.Combobox(processing_frame, textvariable=self.process_count_var, width=5, state="readonly")
        self.process_count_combo['values'] = [str(i) for i in range(1, (multiprocessing.cpu_count() or 1) + 1)]
        self.process_count_combo.grid(row=0, column=1, sticky=tk.W, padx=5)

        single_thread_radio = ttk.Radiobutton(processing_frame, text="Single-thread", variable=self.processing_var, value="singlethread", command=self.toggle_process_count)
        single_thread_radio.grid(row=1, column=0, sticky=tk.W)

        self.scan_button = ttk.Button(parent, text="Start Scanning", command=self.start_scan)
        self.scan_button.pack(pady=10)


    def create_map_tab(self, parent):
        filter_frame = ttk.LabelFrame(parent, text="Filters", padding="10")
        filter_frame.pack(fill=tk.X, expand=True, pady=5)
        
        self.date_filter_var = tk.BooleanVar()
        date_filter_check = ttk.Checkbutton(filter_frame, text="Filter by Date Range", variable=self.date_filter_var, command=self.toggle_date_filter)
        date_filter_check.grid(row=0, column=0, columnspan=4, sticky=tk.W)

        self.start_date_label = ttk.Label(filter_frame, text="Start Date (YYYY-MM-DD):", state=tk.DISABLED)
        self.start_date_entry = ttk.Entry(filter_frame, state=tk.DISABLED)
        self.end_date_label = ttk.Label(filter_frame, text="End Date (YYYY-MM-DD):", state=tk.DISABLED)
        self.end_date_entry = ttk.Entry(filter_frame, state=tk.DISABLED)

        self.start_date_label.grid(row=1, column=0, sticky=tk.W, padx=5)
        self.start_date_entry.grid(row=1, column=1, sticky=tk.W)
        self.end_date_label.grid(row=1, column=2, sticky=tk.W, padx=5)
        self.end_date_entry.grid(row=1, column=3, sticky=tk.W)

        self.camera_filter_var = tk.BooleanVar()
        camera_filter_check = ttk.Checkbutton(filter_frame, text="Filter by Camera Model", variable=self.camera_filter_var, command=self.toggle_camera_filter)
        camera_filter_check.grid(row=2, column=0, columnspan=4, sticky=tk.W, pady=(10, 0))

        self.camera_label = ttk.Label(filter_frame, text="Camera:", state=tk.DISABLED)
        self.camera_combo = ttk.Combobox(filter_frame, state=tk.DISABLED)
        self.camera_label.grid(row=3, column=0, sticky=tk.W, padx=5)
        self.camera_combo.grid(row=3, column=1, columnspan=3, sticky=tk.EW)

        # --- Extension Filter ---
        ext_frame = ttk.LabelFrame(filter_frame, text="File Extensions", padding="10")
        ext_frame.grid(row=4, column=0, columnspan=4, sticky=tk.EW, pady=(10, 0))

        self.extension_vars = {}
        ext_groups = {
            "Images": ['.jpg', '.jpeg', '.png', '.heic', '.tiff'],
            "RAW": ['.arw', '.cr2', '.cr3', '.dng', '.nef', '.orf', '.raf', '.rw2', '.pef'],
            "Videos": ['.mp4', '.mov']
        }
        
        col_count = 0
        for group_name, extensions in ext_groups.items():
            group_label = ttk.Label(ext_frame, text=f"{group_name}", font=('TkDefaultFont', 9, 'italic'))
            group_label.grid(row=0, column=col_count, sticky=tk.W, padx=5, pady=(0, 5))
            row_num = 1
            for ext in extensions:
                var = tk.BooleanVar(value=True)
                # Use a lambda to pass the event object
                chk = ttk.Checkbutton(ext_frame, text=ext.upper(), variable=var, command=lambda: self.schedule_update_counts())
                chk.grid(row=row_num, column=col_count, sticky=tk.W)
                self.extension_vars[ext] = var
                row_num += 1
                if row_num > 5: # Max 5 rows before starting a new column
                    row_num = 1
                    col_count += 1
            col_count += 1
        
        # --- Bindings for live counts ---
        self.date_filter_var.trace_add('write', self.schedule_update_counts)
        self.start_date_entry.bind('<KeyRelease>', lambda e: self.schedule_update_counts())
        self.end_date_entry.bind('<KeyRelease>', lambda e: self.schedule_update_counts())
        self.camera_filter_var.trace_add('write', self.schedule_update_counts)
        self.camera_combo.bind('<<ComboboxSelected>>', self.schedule_update_counts)

        # --- Counts Display ---
        counts_frame = ttk.Frame(parent, padding="10 0 0 0")
        counts_frame.pack(fill=tk.X, expand=True, pady=5)

        self.filtered_count_var = tk.StringVar(value="Matching photos: N/A")
        filtered_count_label = ttk.Label(counts_frame, textvariable=self.filtered_count_var)
        filtered_count_label.pack(side=tk.LEFT)

        self.total_count_var = tk.StringVar(value="Total photos in DB: N/A")
        total_count_label = ttk.Label(counts_frame, textvariable=self.total_count_var)
        total_count_label.pack(side=tk.RIGHT)

        self.generate_map_button = ttk.Button(parent, text="Generate Map", command=self.generate_map)
        self.generate_map_button.pack(pady=10)

    def create_other_tab(self, parent):
        self.clean_db_button = ttk.Button(parent, text="Clean Database", command=self.clean_db)
        self.clean_db_button.pack(pady=10, padx=10)

    def _start_update_counts_thread(self):
        """Starts a background thread to query the database for photo counts."""
        # This task should not disable all buttons, so we use a simpler thread
        thread = threading.Thread(target=self._update_counts_task, daemon=True)
        thread.start()

    def _update_counts_task(self, update_total=False):
        """
        Queries the database for filtered and total counts and puts the result in the queue.
        This method is designed to run in a background thread.
        """
        try:
            start_date, end_date, camera_filter = None, None, None
            
            selected_extensions = [ext for ext, var in self.extension_vars.items() if var.get()]
            if not selected_extensions:
                self.queue.put(("UPDATE_COUNTS", 0, None))
                return

            # --- Get filter values from widgets ---
            if self.date_filter_var.get():
                start_date = self.start_date_entry.get()
                end_date = self.end_date_entry.get()
                try:
                    # Just validate, the DB handler will format it
                    datetime.datetime.strptime(start_date, '%Y-%m-%d')
                    datetime.datetime.strptime(end_date, '%Y-%m-%d')
                except ValueError:
                    start_date, end_date = None, None # Invalidate if format is wrong

            if self.camera_filter_var.get():
                camera_filter = self.camera_combo.get()

            # --- Query database ---
            db_handler = photo_manager.DatabaseHandler(self.db_path)
            
            # Format dates for DB query
            start_db = f"{start_date.replace('-', ':')} 00:00:00" if start_date else None
            end_db = f"{end_date.replace('-', ':')} 23:59:59" if end_date else None
            
            filtered_count = db_handler.count_photos(start_db, end_db, camera_filter, selected_extensions)
            
            total_count = db_handler.count_photos() if update_total else None

            # --- Enqueue UI update ---
            self.queue.put(("UPDATE_COUNTS", filtered_count, total_count))

        except Exception as e:
            self.queue.put(f"Error updating counts: {e}\n")
    
    def schedule_update_counts(self, *args, update_total=False):
        """Schedules a debounced update for the photo counts."""
        if self._after_id_counts:
            self.master.after_cancel(self._after_id_counts)

        # Wrapper to pass the 'update_total' argument
        def do_update():
            thread = threading.Thread(target=self._update_counts_task, args=(update_total,), daemon=True)
            thread.start()

        self._after_id_counts = self.master.after(500, do_update) # 500ms delay

    def create_terminal_widget(self, parent):
        self.terminal = tk.Text(parent, wrap=tk.WORD, bg="black", fg="white", insertbackground="white", state=tk.DISABLED)
        self.terminal.pack(fill=tk.BOTH, expand=True)

    def process_queue(self):
        try:
            while not self.queue.empty():
                msg = self.queue.get_nowait()
                self.terminal.configure(state="normal")
                if isinstance(msg, tuple) and msg[0] == "UPDATE_COUNTS":
                    _, filtered_count, total_count = msg
                    self.filtered_count_var.set(f"Matching photos: {filtered_count}")
                    if total_count is not None:
                        self.total_count_var.set(f"Total photos in DB: {total_count}")
                elif msg == "JOB_DONE":
                    self.enable_buttons()
                    self.schedule_update_counts(update_total=True) # Update counts after a job
                elif '\r' in msg:
                    # Overwrite the current line with the new progress message
                    self.terminal.delete("end-1c linestart", "end")
                    self.terminal.insert("end", msg.strip('\r'))
                else:
                    self.terminal.insert(tk.END, msg)
                self.terminal.configure(state="disabled")
                self.terminal.see(tk.END)
        except queue.Empty:
            pass
        finally:
            self._after_id = self.master.after(100, self.process_queue)
		
    def add_directory(self):
        directory = filedialog.askdirectory()
        if directory:
            self.dir_listbox.insert(tk.END, directory)

    def remove_directory(self):
        selected_indices = self.dir_listbox.curselection()
        for i in reversed(selected_indices):
            self.dir_listbox.delete(i)

    def _set_widgets_state(self, widgets, state):
        """Helper to enable/disable multiple widgets."""
        for widget in widgets:
            widget.config(state=state)

    def toggle_process_count(self):
        state = "readonly" if self.processing_var.get() == "multiprocess" else tk.DISABLED
        self.process_count_combo.config(state=state)

    def toggle_date_filter(self):
        state = tk.NORMAL if self.date_filter_var.get() else tk.DISABLED
        self._set_widgets_state(
            [self.start_date_label, self.start_date_entry, self.end_date_label, self.end_date_entry],
            state
        )

    def toggle_camera_filter(self):
        state = tk.NORMAL if self.camera_filter_var.get() else tk.DISABLED
        self._set_widgets_state([self.camera_label, self.camera_combo], state)
        if state == tk.NORMAL and not self.camera_combo['values']:
            self.run_threaded_task(self.populate_camera_models)

    def populate_camera_models(self, *args):
        """Fetches camera models from DB and populates the combobox."""
        try:
            self.queue.put("Fetching camera models from database...\n")
            db_handler = photo_manager.DatabaseHandler(self.db_path)
            models = db_handler.get_unique_camera_models()
            if models:
                self.camera_combo['values'] = models
                self.queue.put(f"Found {len(models)} camera models.\n")
            else:
                self.queue.put("No camera models found in the database.\n")
        except Exception as e:
            self.queue.put(f"Error fetching camera models: {e}\n")

    def disable_buttons(self):
        # The scan button is managed separately during scanning.
        self.generate_map_button.config(state=tk.DISABLED)
        self.clean_db_button.config(state=tk.DISABLED)
    
    def enable_buttons(self):
        self.scanning = False
        self.scan_button.config(state=tk.NORMAL, text="Start Scanning", command=self.start_scan)
        self.generate_map_button.config(state=tk.NORMAL)
        self.clean_db_button.config(state=tk.NORMAL)

    def run_threaded_task(self, task, *args):
        self.disable_buttons()
        self.terminal.configure(state="normal")
        self.terminal.delete('1.0', tk.END)
        self.terminal.configure(state="disabled")

        # Wrapper for redirecting stream
        class QueueStream:
            def __init__(self, q):
                self.q = q
            def write(self, text):
                self.q.put(text)
            def flush(self):
                pass
        
        stream = QueueStream(self.queue)
        
        thread = threading.Thread(target=task, args=args + (stream,), daemon=True)
        thread.start()

        # Add another thread to just signal the end
        def signal_end():
            thread.join()
            self.queue.put("JOB_DONE")
        
        threading.Thread(target=signal_end, daemon=True).start()

    def start_scan(self):
        dirs = self.dir_listbox.get(0, tk.END)
        if not dirs:
            messagebox.showerror("Error", "Please add at least one directory to scan.")
            return

        self.scanning = True
        self.scan_button.config(text="Stop Scanning", command=self.stop_scan)

        use_multiprocess = self.processing_var.get() == "multiprocess"
        num_processes = int(self.process_count_var.get())

        self.stop_event = threading.Event()
        self.run_threaded_task(photo_manager.scan_media_non_interactive, self.db_path, dirs, use_multiprocess, num_processes, self.stop_event)

    def stop_scan(self):
        """Signals the scanning thread to stop."""
        if self.stop_event:
            self.queue.put("\nStopping scan...\n")
            self.stop_event.set()
            self.scan_button.config(state=tk.DISABLED, text="Stopping...")

    def generate_map(self):
        template_file = "map_template_i18n.html"
        template = os.path.join(self.web_dir, template_file)
        start_date, end_date, camera_filter = None, None, None

        selected_extensions = [ext for ext, var in self.extension_vars.items() if var.get()]
        if not selected_extensions:
            messagebox.showerror("Error", "Please select at least one file extension to filter.")
            return

        if self.date_filter_var.get():
            start_date = self.start_date_entry.get()
            end_date = self.end_date_entry.get()
            try:
                datetime.datetime.strptime(start_date, '%Y-%m-%d')
                datetime.strptime(end_date, '%Y-%m-%d')
            except ValueError:
                messagebox.showerror("Error", "Invalid date format. Please use YYYY-MM-DD.")
                return
        
        if self.camera_filter_var.get():
            camera_filter = self.camera_combo.get()
            if not camera_filter:
                messagebox.showerror("Error", "Please select a camera model.")
                return
        
        # Use a fixed output file name for zh-TW as language selection is removed
        base_output_dir = os.path.dirname(self.output_path)
        output_file_name = "photo_map_i18n.html"
        dynamic_output_path = os.path.join(base_output_dir, output_file_name)

        # Ensure the output directory exists
        os.makedirs(os.path.dirname(dynamic_output_path), exist_ok=True)

        self.run_threaded_task(photo_manager.generate_map_non_interactive, self.db_path, template, dynamic_output_path, start_date, end_date, camera_filter, selected_extensions)

    def clean_db(self):
        if messagebox.askyesno("Confirm Deletion", "Are you sure you want to scan for and delete records of non-existent files? This action cannot be undone."):
            self.run_threaded_task(photo_manager.clean_db_non_interactive, self.db_path, True)

    def search_db(self):
        messagebox.showinfo("Info", "The interactive search is a command-line feature. Please run the script without the --gui flag to use it.")

def main():
    root = tk.Tk()
    style = ttk.Style(root)
    try:
        # It's good practice to have a fallback, even if we prefer 'clam'
        style.theme_use('clam') 
    except tk.TclError:
        # If 'clam' is not available for some reason, use the default theme
        pass
    
    app = PhotoManagerGUI(master=root)
    app.mainloop()

if __name__ == '__main__':
    main()

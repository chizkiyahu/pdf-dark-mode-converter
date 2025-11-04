#!/usr/bin/env python3
"""
PDF Dark Mode Batch Converter - GUI Application

This module provides a graphical user interface for batch converting PDF files to dark mode.
The application processes entire folder structures recursively while preserving directory
hierarchy and provides smart file tracking to avoid redundant conversions.

Key Features:
    - Batch conversion of PDF files in folder hierarchies
    - Quick Scan feature for one-click conversion of preconfigured job folders
    - Smart file tracking: only converts files newer than existing dark mode versions
    - Dry run mode to preview conversions without modifying files
    - Progress tracking with detailed logging
    - Automatic folder structure preservation with "DARK MODE" subfolder organization
    - Selective processing: skips CNC and DARK MODE folders automatically

Usage:
    Run directly as a script:
        python batch_converter_gui.py

    Or import and instantiate:
        from batch_converter_gui import PDFBatchConverterGUI
        import tkinter as tk
        root = tk.Tk()
        app = PDFBatchConverterGUI(root)
        root.mainloop()

Requirements:
    - Python 3.9+
    - tkinter (typically included with Python)
    - Backend PDF processor (pdf_processor_pikepdf module)

Author: PDF Dark Mode Converter Project
License: MIT
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import os
import sys
import threading
from pathlib import Path

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))
from pdf_processor_pikepdf import PDFVectorProcessorPikePDF


class PDFBatchConverterGUI:
    """
    Main GUI application class for batch PDF dark mode conversion.

    This class manages the entire user interface and coordinates the batch conversion
    process. It provides folder selection, conversion options, progress tracking,
    and detailed logging of all operations.

    Attributes:
        root (tk.Tk): The root Tkinter window
        selected_folder (str|None): Currently selected folder path for conversion
        is_converting (bool): Flag indicating if conversion is in progress
        total_files (int): Total number of PDF files to process
        processed_files (int): Number of files processed so far
        converted_count (int): Number of files actually converted
        skipped_count (int): Number of files skipped (already up to date)
        quick_scan_path (str): Configurable path for quick scan feature
        theme_var (tk.StringVar): Selected theme (always "classic" - True Black)
        dry_run_var (tk.BooleanVar): Dry run mode flag
        progress_var (tk.DoubleVar): Progress bar value (0-100)

    UI Components:
        folder_label: Displays currently selected folder
        browse_btn: Opens folder browser dialog
        quick_scan_btn: Triggers quick scan of configured path
        settings_btn: Opens settings dialog
        convert_btn: Starts the conversion process
        cancel_btn: Cancels ongoing conversion
        close_btn: Closes the application
        progress_bar: Visual progress indicator
        status_label: Current status text
        log_text: Scrolled text widget for detailed logging
    """

    def __init__(self, root):
        """
        Initialize the PDF Batch Converter GUI application.

        Sets up the main window, initializes all state variables, and creates
        the user interface components.

        Args:
            root (tk.Tk): The root Tkinter window instance
        """
        self.root = root
        self.root.title("PDF Dark Mode Batch Converter")
        self.root.geometry("700x600")
        self.root.resizable(True, True)

        self.selected_folder = None
        self.is_converting = False
        self.total_files = 0
        self.processed_files = 0
        self.converted_count = 0
        self.skipped_count = 0

        # Default quick scan path (user configurable)
        self.quick_scan_path = "Y:/Ready Jobs"

        self.setup_ui()

    def setup_ui(self):
        """
        Create and configure all GUI components.

        Builds the complete user interface including:
        - Title and folder selection frame
        - Quick scan and settings buttons
        - Options frame with dry run checkbox
        - Progress tracking components (progress bar, status label, log text)
        - Action buttons (Convert, Cancel, Close)

        The UI is organized using ttk.Frame containers with grid layout management
        for responsive resizing.
        """
        # Main container
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)

        # Title
        title_label = ttk.Label(main_frame, text="PDF Dark Mode Batch Converter",
                               font=("Arial", 16, "bold"))
        title_label.grid(row=0, column=0, columnspan=3, pady=(0, 20))

        # Folder selection
        folder_frame = ttk.LabelFrame(main_frame, text="Select Job Folder", padding="10")
        folder_frame.grid(row=1, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        folder_frame.columnconfigure(1, weight=1)

        self.folder_label = ttk.Label(folder_frame, text="No folder selected",
                                      foreground="gray")
        self.folder_label.grid(row=0, column=0, columnspan=3, sticky=tk.W, pady=(0, 10))

        self.browse_btn = ttk.Button(folder_frame, text="Browse...",
                                     command=self.browse_folder)
        self.browse_btn.grid(row=1, column=0, padx=(0, 5))

        self.quick_scan_btn = ttk.Button(folder_frame, text="Quick Scan Ready Jobs",
                                         command=self.quick_scan)
        self.quick_scan_btn.grid(row=1, column=1, padx=(0, 5))

        self.settings_btn = ttk.Button(folder_frame, text="Settings...",
                                       command=self.open_settings)
        self.settings_btn.grid(row=1, column=2)

        # Always use True Black (Classic) theme
        self.theme_var = tk.StringVar(value="classic")

        # Options
        options_frame = ttk.LabelFrame(main_frame, text="Options", padding="10")
        options_frame.grid(row=2, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))

        self.dry_run_var = tk.BooleanVar(value=False)
        dry_run_cb = ttk.Checkbutton(options_frame, text="Dry Run (show what would be converted without actually converting)",
                                     variable=self.dry_run_var)
        dry_run_cb.grid(row=0, column=0, sticky=tk.W, padx=5, pady=2)

        # Progress section
        progress_frame = ttk.LabelFrame(main_frame, text="Progress", padding="10")
        progress_frame.grid(row=3, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S),
                           pady=(0, 10))
        progress_frame.columnconfigure(0, weight=1)
        progress_frame.rowconfigure(1, weight=1)

        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(progress_frame, variable=self.progress_var,
                                           maximum=100)
        self.progress_bar.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))

        self.status_label = ttk.Label(progress_frame, text="Ready to convert",
                                      foreground="blue")
        self.status_label.grid(row=1, column=0, sticky=tk.W, pady=(0, 5))

        # Log output
        self.log_text = scrolledtext.ScrolledText(progress_frame, height=15, width=70,
                                                  state='disabled')
        self.log_text.grid(row=2, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=4, column=0, columnspan=3, pady=(10, 0))

        self.convert_btn = ttk.Button(button_frame, text="Convert All PDFs",
                                      command=self.start_conversion, state='disabled')
        self.convert_btn.grid(row=0, column=0, padx=5)

        self.cancel_btn = ttk.Button(button_frame, text="Cancel",
                                     command=self.cancel_conversion, state='disabled')
        self.cancel_btn.grid(row=0, column=1, padx=5)

        self.close_btn = ttk.Button(button_frame, text="Close",
                                    command=self.root.quit)
        self.close_btn.grid(row=0, column=2, padx=5)

        # Configure grid weights
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(3, weight=1)

    def browse_folder(self):
        """
        Open a folder selection dialog and update the selected folder.

        Allows the user to browse and select a folder containing PDF files to convert.
        Updates the UI to display the selected path, enables the convert button,
        and counts the number of PDF files found in the folder hierarchy.

        The count excludes PDFs in "DARK MODE" and "CNC" subfolders.
        """
        folder = filedialog.askdirectory(title="Select Job Folder")
        if folder:
            self.selected_folder = folder
            self.folder_label.config(text=folder, foreground="black")
            self.convert_btn.config(state='normal')
            self.log(f"Selected folder: {folder}")

            # Count PDFs
            pdf_count = self.count_pdfs(folder)
            self.log(f"Found {pdf_count} PDF file(s) to convert")

    def quick_scan(self):
        """
        Execute a quick scan of the preconfigured ready jobs folder and auto-start conversion.

        This convenience method provides one-click operation for frequently used job folders.
        It automatically:
        1. Selects the preconfigured quick_scan_path as the target folder
        2. Counts PDF files in the folder hierarchy
        3. Immediately starts the conversion process

        If the configured path doesn't exist, displays an error dialog prompting the user
        to update the path in Settings.

        The default path is "Y:/Ready Jobs" but can be customized via the Settings dialog.
        """
        if os.path.exists(self.quick_scan_path):
            self.selected_folder = self.quick_scan_path
            self.folder_label.config(text=self.quick_scan_path, foreground="black")
            self.convert_btn.config(state='normal')
            self.log(f"Quick scan: {self.quick_scan_path}")

            # Count PDFs
            pdf_count = self.count_pdfs(self.quick_scan_path)
            self.log(f"Found {pdf_count} PDF file(s) to convert")

            # Automatically start conversion
            self.log("Starting automatic conversion...\n")
            self.start_conversion()
        else:
            messagebox.showerror("Path Not Found",
                                f"Quick scan path does not exist:\n{self.quick_scan_path}\n\n"
                                f"Please update it in Settings.")

    def open_settings(self):
        """
        Open the settings dialog window for configuration.

        Creates a modal dialog that allows the user to configure application settings.
        Currently supports:
        - Quick Scan Path: The default folder path used by the Quick Scan feature

        The dialog includes:
        - A text entry field displaying the current quick scan path
        - A Browse button to select a new path via folder dialog
        - Save button to apply changes
        - Cancel button to dismiss without saving

        The settings window is modal (blocks interaction with main window until closed)
        and is automatically centered on the parent window.
        """
        settings_window = tk.Toplevel(self.root)
        settings_window.title("Settings")
        settings_window.geometry("500x150")
        settings_window.resizable(False, False)

        # Center the window
        settings_window.transient(self.root)
        settings_window.grab_set()

        frame = ttk.Frame(settings_window, padding="20")
        frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # Quick scan path setting
        ttk.Label(frame, text="Quick Scan Path:", font=("Arial", 10, "bold")).grid(
            row=0, column=0, sticky=tk.W, pady=(0, 10))

        path_var = tk.StringVar(value=self.quick_scan_path)
        path_entry = ttk.Entry(frame, textvariable=path_var, width=50)
        path_entry.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))

        def browse_path():
            folder = filedialog.askdirectory(title="Select Quick Scan Path",
                                            initialdir=self.quick_scan_path)
            if folder:
                path_var.set(folder)

        browse_settings_btn = ttk.Button(frame, text="Browse...", command=browse_path)
        browse_settings_btn.grid(row=2, column=0, sticky=tk.W, pady=(0, 10))

        def save_settings():
            new_path = path_var.get()
            if new_path:
                self.quick_scan_path = new_path
                self.log(f"Settings saved: Quick scan path = {new_path}")
                messagebox.showinfo("Settings Saved", "Quick scan path updated successfully!")
                settings_window.destroy()

        def cancel_settings():
            settings_window.destroy()

        # Buttons
        button_frame = ttk.Frame(frame)
        button_frame.grid(row=3, column=0, columnspan=2, pady=(10, 0))

        save_btn = ttk.Button(button_frame, text="Save", command=save_settings)
        save_btn.grid(row=0, column=0, padx=5)

        cancel_btn = ttk.Button(button_frame, text="Cancel", command=cancel_settings)
        cancel_btn.grid(row=0, column=1, padx=5)

    def count_pdfs(self, folder):
        """
        Count the total number of PDF files in a folder hierarchy.

        Recursively walks through the specified folder and all its subfolders,
        counting files with .pdf extension. Automatically excludes:
        - Files in folders containing "DARK MODE" in the path
        - Files in folders containing "CNC" in the path

        Args:
            folder (str): The root folder path to search

        Returns:
            int: Total count of PDF files found (excluding filtered folders)
        """
        count = 0
        for root, dirs, files in os.walk(folder):
            # Skip DARK MODE and CNC folders
            if "DARK MODE" in root or "CNC" in root:
                continue
            for file in files:
                if file.lower().endswith('.pdf'):
                    count += 1
        return count

    def log(self, message):
        """
        Append a message to the scrolled text log display.

        Adds the message to the log text widget with automatic scrolling to keep
        the most recent message visible. The log is normally read-only but is
        temporarily enabled for writing.

        Args:
            message (str): The message to append to the log (newline automatically added)

        Note:
            This method also calls root.update_idletasks() to ensure the UI updates
            immediately, which is important during long-running operations.
        """
        self.log_text.config(state='normal')
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)
        self.log_text.config(state='disabled')
        self.root.update_idletasks()

    def start_conversion(self):
        """
        Initiate the PDF conversion process in a background thread.

        Validates that a folder has been selected, then starts the conversion process
        in a separate daemon thread to prevent the UI from freezing during processing.

        Updates the UI state:
        - Disables convert and browse buttons
        - Enables cancel button
        - Resets progress bar to 0%

        If no folder is selected, displays a warning dialog.

        The actual conversion logic is executed in convert_all_pdfs() which runs
        in the background thread.
        """
        if not self.selected_folder:
            messagebox.showwarning("No Folder", "Please select a folder first.")
            return

        self.is_converting = True
        self.convert_btn.config(state='disabled')
        self.browse_btn.config(state='disabled')
        self.cancel_btn.config(state='normal')
        self.progress_var.set(0)

        # Run conversion in a separate thread
        thread = threading.Thread(target=self.convert_all_pdfs, daemon=True)
        thread.start()

    def cancel_conversion(self):
        """
        Request cancellation of the ongoing conversion process.

        Sets the is_converting flag to False, which is checked by convert_all_pdfs()
        between file conversions. The cancellation is cooperative - the current file
        will finish converting before the process stops.

        Updates the UI:
        - Logs a cancellation message
        - Changes status label to "Cancelling..." in orange

        Note:
            This doesn't forcibly kill the thread but allows convert_all_pdfs() to
            gracefully exit at the next check point.
        """
        self.is_converting = False
        self.log("Cancellation requested...")
        self.status_label.config(text="Cancelling...", foreground="orange")

    def convert_all_pdfs(self):
        """
        Main conversion logic that processes all PDF files in the selected folder hierarchy.

        This method runs in a background thread and performs the following operations:

        1. Discovery Phase:
           - Recursively scans the selected folder for PDF files
           - Skips "DARK MODE" and "CNC" subfolders
           - Determines output paths maintaining folder structure
           - Creates "DARK MODE" subfolder within each job folder

        2. Smart File Tracking:
           - Compares modification times of source and existing output files
           - Only converts files that are newer than their dark mode versions
           - Skips files that are already up to date

        3. Conversion Phase:
           - Creates necessary output directories
           - Processes each PDF using PDFVectorProcessorPikePDF
           - Updates progress bar and status label in real-time
           - Logs detailed information for each file

        4. Dry Run Mode:
           - When enabled, simulates conversion without writing files
           - Shows what would be converted/skipped
           - Useful for previewing batch operations

        5. Error Handling:
           - Catches and logs errors for individual files
           - Continues processing remaining files after errors
           - Displays final summary with conversion statistics

        Output Structure:
            Original: /Ready Jobs/JobName/Folder/file.pdf
            Dark Mode: /Ready Jobs/JobName/DARK MODE/Folder/file.pdf

        The method updates instance variables:
        - total_files: Total PDFs discovered
        - processed_files: Number of PDFs processed so far
        - converted_count: Number of PDFs actually converted
        - skipped_count: Number of PDFs skipped (already up to date)

        Displays a completion dialog with statistics when finished.
        Calls reset_ui() in the finally block to restore UI state.
        """
        try:
            # Find all PDFs and their output paths
            pdf_files = []
            for root, dirs, files in os.walk(self.selected_folder):
                # Skip the DARK MODE and CNC folders
                if "DARK MODE" in root or "CNC" in root:
                    continue

                for file in files:
                    if file.lower().endswith('.pdf'):
                        source_path = os.path.join(root, file)

                        # Determine output path: create DARK MODE folder in the job folder
                        # Find the immediate subfolder of selected_folder (the job folder)
                        rel_to_parent = os.path.relpath(source_path, self.selected_folder)
                        path_parts = rel_to_parent.split(os.sep)

                        if len(path_parts) > 1:
                            # Inside a job folder
                            job_folder = path_parts[0]
                            job_folder_path = os.path.join(self.selected_folder, job_folder)
                            output_folder = os.path.join(job_folder_path, "DARK MODE")

                            # Relative path within the job folder
                            rel_within_job = os.path.relpath(source_path, job_folder_path)
                            output_path = os.path.join(output_folder, rel_within_job)
                        else:
                            # File directly in selected folder (shouldn't happen normally)
                            output_folder = os.path.join(self.selected_folder, "DARK MODE")
                            output_path = os.path.join(output_folder, file)

                        pdf_files.append((source_path, output_path))

            self.total_files = len(pdf_files)
            self.processed_files = 0
            self.converted_count = 0
            self.skipped_count = 0

            if self.total_files == 0:
                self.log("No PDF files found!")
                self.reset_ui()
                return

            # Check if dry run mode
            dry_run = self.dry_run_var.get()
            if dry_run:
                self.log("=== DRY RUN MODE - No files will be converted ===")
                self.log(f"Analyzing {self.total_files} PDF(s)...\n")
            else:
                self.log(f"Starting conversion of {self.total_files} PDF(s)...")

            self.status_label.config(text=f"Converting 0/{self.total_files}",
                                    foreground="green")

            # Get theme
            theme = self.theme_var.get()
            processor = None if dry_run else PDFVectorProcessorPikePDF(theme=theme)

            # Convert each PDF
            for i, (pdf_path, output_path) in enumerate(pdf_files):
                if not self.is_converting:
                    self.log("Conversion cancelled by user.")
                    break

                # Calculate relative path for display
                rel_path = os.path.relpath(pdf_path, self.selected_folder)
                rel_output = os.path.relpath(output_path, self.selected_folder)

                # Create output subdirectories (even in dry run to test path logic)
                if not dry_run:
                    os.makedirs(os.path.dirname(output_path), exist_ok=True)

                # Check if we need to convert (only if source is newer or output doesn't exist)
                should_convert = True
                if os.path.exists(output_path):
                    source_mtime = os.path.getmtime(pdf_path)
                    output_mtime = os.path.getmtime(output_path)
                    if source_mtime <= output_mtime:
                        should_convert = False
                        self.skipped_count += 1
                        if dry_run:
                            self.log(f"[SKIP] {rel_path}")
                            self.log(f"       -> {rel_output} (already up to date)")
                        else:
                            self.log(f"Skipping (up to date): {rel_path}")
                        self.processed_files += 1
                        progress = (self.processed_files / self.total_files) * 100
                        self.progress_var.set(progress)
                        self.status_label.config(
                            text=f"Processing {self.processed_files}/{self.total_files}",
                            foreground="green"
                        )

                # Convert (or simulate in dry run)
                if should_convert:
                    try:
                        if dry_run:
                            # Dry run - just show what would happen
                            self.log(f"[WOULD CONVERT] {rel_path}")
                            self.log(f"                -> {rel_output}")
                        else:
                            # Actually convert
                            self.log(f"Converting: {rel_path}")

                            with open(pdf_path, 'rb') as f:
                                input_bytes = f.read()

                            output_bytes = processor.process_pdf(input_bytes)

                            with open(output_path, 'wb') as f:
                                f.write(output_bytes)

                            self.log(f"  ✓ Saved to: {rel_output}")

                        self.converted_count += 1
                        self.processed_files += 1
                        progress = (self.processed_files / self.total_files) * 100
                        self.progress_var.set(progress)
                        self.status_label.config(
                            text=f"Processing {self.processed_files}/{self.total_files}",
                            foreground="green"
                        )

                    except Exception as e:
                        self.log(f"  ✗ ERROR: {str(e)}")

            # Done
            if self.is_converting:
                self.log(f"\n{'='*50}")
                if dry_run:
                    self.log(f"Dry run complete!")
                    self.log(f"Would convert: {self.converted_count} file(s)")
                    self.log(f"Would skip: {self.skipped_count} file(s) (already up to date)")
                    self.log(f"Total analyzed: {self.total_files} file(s)")
                    self.log(f"No files were actually modified.")
                    self.status_label.config(text="Dry run complete!", foreground="blue")
                    messagebox.showinfo("Dry Run Complete",
                                       f"Dry run analyzed {self.total_files} PDF(s)\n"
                                       f"Would convert: {self.converted_count} file(s)\n"
                                       f"Would skip: {self.skipped_count} file(s)\n\n"
                                       f"No files were actually modified.\n"
                                       f"Uncheck 'Dry Run' to perform actual conversion.")
                else:
                    self.log(f"Conversion complete!")
                    self.log(f"Converted: {self.converted_count} file(s)")
                    self.log(f"Skipped: {self.skipped_count} file(s) (already up to date)")
                    self.log(f"Total processed: {self.total_files} file(s)")
                    self.log(f"DARK MODE folders created in each job folder")
                    self.status_label.config(text="Conversion complete!", foreground="blue")
                    messagebox.showinfo("Complete",
                                       f"Successfully processed {self.total_files} PDF(s)!\n\n"
                                       f"Converted: {self.converted_count} file(s)\n"
                                       f"Skipped: {self.skipped_count} file(s) (already up to date)\n\n"
                                       f"DARK MODE folders created in each job folder.")

        except Exception as e:
            self.log(f"\nFATAL ERROR: {str(e)}")
            import traceback
            self.log(traceback.format_exc())
            messagebox.showerror("Error", f"An error occurred:\n{str(e)}")

        finally:
            self.reset_ui()

    def reset_ui(self):
        """
        Reset the UI to its ready state after conversion completes or is cancelled.

        Re-enables controls and updates button states:
        - Enables convert button
        - Enables browse button
        - Disables cancel button
        - Resets is_converting flag to False

        This method is always called in the finally block of convert_all_pdfs()
        to ensure the UI is properly restored regardless of success, failure, or cancellation.
        """
        self.is_converting = False
        self.convert_btn.config(state='normal')
        self.browse_btn.config(state='normal')
        self.cancel_btn.config(state='disabled')


def main():
    """
    Application entry point.

    Creates the root Tkinter window, initializes the PDFBatchConverterGUI application,
    and starts the Tkinter event loop.

    This function is called when the script is run directly.
    """
    root = tk.Tk()
    app = PDFBatchConverterGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()

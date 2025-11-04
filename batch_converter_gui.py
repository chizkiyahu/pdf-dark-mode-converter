#!/usr/bin/env python3
"""
GUI application for batch PDF dark mode conversion.
Converts all PDFs in a folder and subfolders, preserving the directory structure.
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
    def __init__(self, root):
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
        """Quick scan the configured ready jobs path and automatically start conversion"""
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
        """Open settings dialog to configure quick scan path"""
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
        self.log_text.config(state='normal')
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)
        self.log_text.config(state='disabled')
        self.root.update_idletasks()

    def start_conversion(self):
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
        self.is_converting = False
        self.log("Cancellation requested...")
        self.status_label.config(text="Cancelling...", foreground="orange")

    def convert_all_pdfs(self):
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
        self.is_converting = False
        self.convert_btn.config(state='normal')
        self.browse_btn.config(state='normal')
        self.cancel_btn.config(state='disabled')


def main():
    root = tk.Tk()
    app = PDFBatchConverterGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()

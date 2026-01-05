import gradio as gr
import pandas as pd
import os
import tempfile
from datetime import datetime
from pathlib import Path


def process_csv(file_path):
    """
    Process CSV file according to business rules:
    1. Remove unwanted columns
    2. Filter rows (remove empty Vendor/Country Destination)
    3. For OPS/IVG vendors: keep Revenue but clear Cost and Profit
    4. Group by Trunk Group and calculate totals
    5. Add spacing between groups
    """
    try:
        # Read CSV file
        df = pd.read_csv(file_path)
        
        # Strip whitespace from column names
        df.columns = df.columns.str.strip()
        
        # Define columns to remove
        columns_to_remove = [
            'Attempts', 'Completions', 'Minutes', 'ASR %', 'NER %', 'Aloc', 
            'PPM', 'PRV', 'NEPR %', 'SDR %', 'MOS', 'PDD', 'LCR Depth'
        ]
        
        # Remove unwanted columns (only if they exist)
        columns_to_remove = [col for col in columns_to_remove if col in df.columns]
        df = df.drop(columns=columns_to_remove)
        
        # Ensure required columns exist
        required_columns = ['Customer Relationships', 'Trunk Group', 'Country Destination', 'Vendor', 'Revenue', 'Cost', 'Profit']
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            available_cols = ', '.join(df.columns.tolist())
            return None, f"Error: Missing required columns: {', '.join(missing_columns)}\n\nAvailable columns in file: {available_cols}", None, None
        
        # Filter 1: Remove rows where Vendor OR Country Destination is empty
        df = df[
            (df['Vendor'].notna()) & 
            (df['Vendor'].astype(str).str.strip() != '') &
            (df['Country Destination'].notna()) & 
            (df['Country Destination'].astype(str).str.strip() != '')
        ]
        
        if df.empty:
            return None, "Error: No rows remaining after filtering. Please check your data.", None, None
        
        # Convert Revenue, Cost, Profit to numeric (handle any string values)
        for col in ['Revenue', 'Cost', 'Profit']:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        
        # For rows where Vendor contains "OPS" or "IVG": 
        # - Set Cost to 0
        # - Recalculate Profit as Revenue - Cost (which equals Revenue since Cost = 0)
        ops_ivg_mask = (
            df['Vendor'].astype(str).str.upper().str.contains('OPS', na=False) |
            df['Vendor'].astype(str).str.upper().str.contains('IVG', na=False)
        )
        df.loc[ops_ivg_mask, 'Cost'] = 0
        df.loc[ops_ivg_mask, 'Profit'] = df.loc[ops_ivg_mask, 'Revenue']  # Profit = Revenue - 0 = Revenue
        
        # Group by Trunk Group AND Country Destination together
        processed_rows = []
        
        # Create unique combinations of Trunk Group + Country Destination
        df['_group_key'] = df['Trunk Group'] + '|||' + df['Country Destination']
        unique_groups = df['_group_key'].unique()
        
        for idx, group_key in enumerate(unique_groups):
            # Get all rows for this Trunk Group + Country combination
            group_df = df[df['_group_key'] == group_key].copy()
            
            # Add rows for this group
            for _, row in group_df.iterrows():
                processed_rows.append({
                    'Customer Relationships': row['Customer Relationships'],
                    'Trunk Group': row['Trunk Group'],
                    'Country Destination': row['Country Destination'],
                    'Vendor': row['Vendor'],
                    'Revenue': row['Revenue'],
                    'Cost': row['Cost'],
                    'Profit': row['Profit']
                })
            
            # Calculate totals for this Trunk Group + Country (round to 2 decimal places)
            total_revenue = round(group_df['Revenue'].sum(), 2)
            total_cost = round(group_df['Cost'].sum(), 2)
            total_profit = round(group_df['Profit'].sum(), 2)
            
            # Add totals row (empty for descriptive columns, totals for financial columns)
            processed_rows.append({
                'Customer Relationships': '',
                'Trunk Group': '',
                'Country Destination': '',
                'Vendor': '',
                'Revenue': total_revenue,
                'Cost': total_cost,
                'Profit': total_profit
            })
            
            # Add 5 empty rows between groups (except after the last group)
            if idx < len(unique_groups) - 1:
                for _ in range(5):
                    processed_rows.append({
                        'Customer Relationships': '',
                        'Trunk Group': '',
                        'Country Destination': '',
                        'Vendor': '',
                        'Revenue': '',
                        'Cost': '',
                        'Profit': ''
                    })
        
        # Create DataFrame from processed rows
        result_df = pd.DataFrame(processed_rows)
        
        # Replace NaN with empty strings for better CSV readability
        result_df = result_df.fillna('')
        
        # Create processed directory if it doesn't exist
        processed_dir = Path("processed")
        processed_dir.mkdir(exist_ok=True)
        
        # Generate cleaner filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        original_filename = Path(file_path).stem
        
        # Clean the original filename: remove spaces, special chars, keep only alphanumeric and underscores
        cleaned_name = "".join(c if c.isalnum() or c in ('_', '-') else '_' for c in original_filename)
        # Remove multiple consecutive underscores
        cleaned_name = '_'.join(filter(None, cleaned_name.split('_')))
        # Limit length to avoid too long filenames
        if len(cleaned_name) > 50:
            cleaned_name = cleaned_name[:50]
        
        # Format: timestamp_cleanedname.csv (timestamp first for better sorting)
        output_filename = f"{timestamp}_{cleaned_name}.csv"
        output_path = processed_dir / output_filename
        
        # Write to CSV (use empty string for NaN values)
        result_df.to_csv(output_path, index=False, na_rep='')
        
        # Count OPS/IVG vendors for summary (need to recalculate after grouping)
        ops_ivg_count = ops_ivg_mask.sum()
        
        # Create preview data (first 20 rows)
        preview_df = result_df.head(20).copy()
        
        # Return file path, summary, and preview
        summary = "Processing complete!\n\n"
        summary += f"Total rows processed: {len(df)}\n"
        summary += f"OPS/IVG vendors (Cost recalculated): {ops_ivg_count}\n"
        summary += f"Trunk Group + Country combinations: {len(unique_groups)}\n"
        summary += f"Output rows: {len(result_df)}\n"
        summary += f"\nFile saved as: {output_filename}"
        
        # Convert preview to HTML table for better display
        preview_html = preview_df.to_html(index=False, classes="preview-table", table_id="preview-table")
        
        return str(output_path), summary, preview_html, result_df
        
    except Exception as e:
        return None, f"Error processing file: {str(e)}", None, None


def process_file_interface(file):
    """
    Gradio interface function for processing uploaded file
    """
    if file is None:
        return None, "Please upload a CSV file first.", None, get_processed_files_list()
    
    output_path, message, preview_html, result_df = process_csv(file.name)
    
    if output_path is None:
        return None, message, None, get_processed_files_list()
    
    # Get updated list of processed files
    files_list = get_processed_files_list()
    
    return output_path, message, preview_html, files_list


def get_processed_files_list():
    """
    Get list of all processed files with their creation dates
    """
    processed_dir = Path("processed")
    if not processed_dir.exists():
        return "No processed files yet."
    
    # Updated pattern to match new naming format
    files = list(processed_dir.glob("*.csv"))
    if not files:
        return "No processed files yet."
    
    # Sort by modification time (newest first)
    files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
    
    files_info = []
    for file in files:
        file_stat = file.stat()
        file_size = file_stat.st_size / 1024  # Size in KB
        mod_time = datetime.fromtimestamp(file_stat.st_mtime)
        mod_time_str = mod_time.strftime("%Y-%m-%d %H:%M:%S")
        files_info.append(f"📄 {file.name}\n   Created: {mod_time_str} | Size: {file_size:.2f} KB")
    
    return "\n\n".join(files_info)


def get_processed_files_dataframe():
    """
    Get processed files as a DataFrame for display with actions
    """
    processed_dir = Path("processed")
    if not processed_dir.exists():
        return pd.DataFrame(columns=["Filename", "Created", "Size"])
    
    files = list(processed_dir.glob("*.csv"))
    if not files:
        return pd.DataFrame(columns=["Filename", "Created", "Size"])
    
    # Sort by modification time (newest first)
    files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
    
    data = []
    for file in files:
        file_stat = file.stat()
        file_size = file_stat.st_size / 1024  # Size in KB
        mod_time = datetime.fromtimestamp(file_stat.st_mtime)
        mod_time_str = mod_time.strftime("%Y-%m-%d %H:%M:%S")
        data.append({
            "Filename": file.name,
            "Created": mod_time_str,
            "Size": f"{file_size:.2f} KB"
        })
    
    return pd.DataFrame(data)


def get_processed_files_dropdown():
    """
    Get list of filenames for dropdown
    """
    processed_dir = Path("processed")
    if not processed_dir.exists():
        return []
    
    files = list(processed_dir.glob("*.csv"))
    if not files:
        return []
    
    # Sort by modification time (newest first)
    files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
    
    return [file.name for file in files]


def download_processed_file(filename):
    """
    Download a specific processed file
    """
    processed_dir = Path("processed")
    file_path = processed_dir / filename
    
    if file_path.exists() and file_path.is_file():
        return str(file_path.absolute())
    return None


def delete_processed_file(filename, confirm):
    """
    Delete a processed file with confirmation
    """
    if not confirm:
        return get_processed_files_list(), "Deletion cancelled. Please confirm to delete."
    
    processed_dir = Path("processed")
    file_path = processed_dir / filename
    
    if file_path.exists() and file_path.is_file():
        try:
            file_path.unlink()
            updated_list = get_processed_files_list()
            return updated_list, f"✅ File '{filename}' deleted successfully."
        except Exception as e:
            return get_processed_files_list(), f"❌ Error deleting file: {str(e)}"
    
    return get_processed_files_list(), f"❌ File '{filename}' not found."


# Create Gradio interface
custom_css = """
.preview-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 12px;
    margin: 10px 0;
}
.preview-table th, .preview-table td {
    border: 1px solid #ddd;
    padding: 6px;
    text-align: left;
}
.preview-table th {
    background-color: #f2f2f2;
    font-weight: bold;
}
.preview-table tr:nth-child(even) {
    background-color: #f9f9f9;
}
"""

with gr.Blocks(title="CSV Data Processor") as app:
    gr.Markdown("# CSV Data Processing Application")
    gr.Markdown("""
    This application processes customer CSV files by:
    - Removing unwanted columns (Attempts, Completions, Minutes, ASR %, NER %, Aloc, PPM, PRV, NEPR %, SDR %, MOS, PDD, LCR Depth)
    - Filtering rows (removes rows with empty Vendor/Country Destination)
    - For vendors containing 'OPS' or 'IVG': keeps Revenue but clears Cost and Profit
    - Grouping by Trunk Group and calculating totals
    - Adding 5 empty rows between groups
    """)
    
    with gr.Row():
        with gr.Column():
            file_input = gr.File(
                label="Upload CSV File",
                file_types=[".csv"],
                type="filepath"
            )
            process_btn = gr.Button("Process CSV", variant="primary")
        
        with gr.Column():
            status_output = gr.Textbox(
                label="Processing Status",
                lines=6,
                interactive=False
            )
            file_output = gr.File(
                label="Download Processed CSV",
                type="filepath"
            )
    
    # Preview section
    with gr.Row():
        with gr.Column():
            gr.Markdown("### 📊 Data Preview (First 20 rows)")
            preview_output = gr.HTML(
                label="Preview",
                value="<p style='text-align: center; color: #666;'>Upload and process a file to see preview</p>"
            )
        
        with gr.Column():
            gr.Markdown("### 📁 Processed Files History")
            files_dataframe = gr.Dataframe(
                label="All Processed Files",
                headers=["Filename", "Created", "Size"],
                interactive=False,
                value=get_processed_files_dataframe(),
                wrap=True
            )
            files_list_output = gr.Textbox(
                label="Files List (Text)",
                visible=False,
                value=get_processed_files_list()
            )
            
            selected_filename = gr.Dropdown(
                label="Select File",
                choices=get_processed_files_dropdown(),
                interactive=True,
                value=None
            )
            
            with gr.Row():
                download_file_btn = gr.Button("⬇️ Download Selected File", variant="primary")
                download_file_output = gr.File(label="Download File", visible=False)
            
            with gr.Row():
                delete_confirm_checkbox = gr.Checkbox(
                    label="⚠️ I confirm I want to delete this file",
                    value=False
                )
                delete_file_btn = gr.Button("🗑️ Delete Selected File", variant="stop")
            
            delete_status = gr.Textbox(
                label="Status",
                interactive=False,
                visible=True
            )
    
    # Function to update dropdown and dataframe
    def update_files_display():
        return get_processed_files_dataframe(), gr.update(choices=get_processed_files_dropdown()), get_processed_files_list()
    
    # Connect the process button
    process_btn.click(
        fn=process_file_interface,
        inputs=file_input,
        outputs=[file_output, status_output, preview_output, files_list_output]
    ).then(
        fn=update_files_display,
        inputs=None,
        outputs=[files_dataframe, selected_filename, files_list_output]
    )
    
    # Download file functionality
    def handle_download(filename):
        if not filename:
            return None, "⚠️ Please select a file from the table above."
        file_path = download_processed_file(filename)
        if file_path:
            return file_path, f"✅ Ready to download: {filename}"
        return None, f"❌ File '{filename}' not found."
    
    download_file_btn.click(
        fn=handle_download,
        inputs=selected_filename,
        outputs=[download_file_output, delete_status]
    )
    
    # Delete file functionality with confirmation
    def handle_delete(filename, confirm, current_list):
        if not filename:
            df, dropdown = update_files_display()[:2]
            return current_list, df, dropdown, "⚠️ Please select a file from the dropdown above."
        
        if not confirm:
            df, dropdown = update_files_display()[:2]
            return current_list, df, dropdown, "⚠️ Please check the confirmation box to delete the file."
        
        updated_list, message = delete_processed_file(filename, confirm)
        updated_df, updated_dropdown, _ = update_files_display()
        # Reset confirmation checkbox and clear selection after deletion
        return updated_list, updated_df, gr.update(choices=updated_dropdown, value=None), message, gr.update(value=False)
    
    delete_file_btn.click(
        fn=handle_delete,
        inputs=[selected_filename, delete_confirm_checkbox, files_list_output],
        outputs=[files_list_output, files_dataframe, selected_filename, delete_status, delete_confirm_checkbox]
    )
    
    # Refresh button for files list
    refresh_btn = gr.Button("🔄 Refresh Files List", variant="secondary")
    refresh_btn.click(
        fn=update_files_display,
        inputs=None,
        outputs=[files_dataframe, selected_filename, files_list_output]
    )
    
    gr.Markdown("### Instructions")
    gr.Markdown("""
    1. Click 'Upload CSV File' and select your CSV file
    2. Click 'Process CSV' to start processing
    3. Wait for processing to complete
    4. View the preview of processed data
    5. Download the processed CSV file from the download section
    6. All processed files are saved with timestamp in filename
    """)


if __name__ == "__main__":
    server_name = os.environ.get("GRADIO_SERVER_NAME", "0.0.0.0")
    server_port = int(os.environ.get("GRADIO_SERVER_PORT", 7860))
    app.launch(
        share=False,
        server_name=server_name,
        server_port=server_port,
        theme=gr.themes.Soft(),
        css=custom_css
    )

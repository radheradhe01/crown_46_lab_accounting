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
    3. For OPS/IVG/PROXY 2 vendors: keep Revenue but set Cost to 0 and recalculate Profit
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
            return None, f"### ❌ Error\nMissing required columns: {', '.join(missing_columns)}\n\nAvailable columns in file: {available_cols}", None, None
        
        # Filter 1: Remove rows where Vendor OR Country Destination is empty
        df = df[
            (df['Vendor'].notna()) & 
            (df['Vendor'].astype(str).str.strip() != '') &
            (df['Country Destination'].notna()) & 
            (df['Country Destination'].astype(str).str.strip() != '')
        ]
        
        if df.empty:
            return None, "### ❌ Error\nNo rows remaining after filtering. Please check your data.", None, None
        
        # Convert Revenue, Cost, Profit to numeric (handle any string values)
        for col in ['Revenue', 'Cost', 'Profit']:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        
        # For rows where Vendor contains "OPS", "IVG", or "PROXY 2": 
        # - Set Cost to 0
        # - Recalculate Profit as Revenue - Cost (which equals Revenue since Cost = 0)
        ops_ivg_proxy_mask = (
            df['Vendor'].astype(str).str.upper().str.contains('OPS', na=False) |
            df['Vendor'].astype(str).str.upper().str.contains('IVG', na=False) |
            df['Vendor'].astype(str).str.upper().str.contains('PROXY 2', na=False)
        )
        df.loc[ops_ivg_proxy_mask, 'Cost'] = 0
        df.loc[ops_ivg_proxy_mask, 'Profit'] = df.loc[ops_ivg_proxy_mask, 'Revenue']  # Profit = Revenue - 0 = Revenue
        
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
                # Calculate profit percentage (Profit/Revenue * 100)
                revenue_val = float(row['Revenue']) if pd.notna(row['Revenue']) and row['Revenue'] != '' else 0
                profit_val = float(row['Profit']) if pd.notna(row['Profit']) and row['Profit'] != '' else 0
                profit_pct = round((profit_val / revenue_val * 100), 2) if revenue_val != 0 else 0.0
                
                processed_rows.append({
                    'Customer Relationships': row['Customer Relationships'],
                    'Trunk Group': row['Trunk Group'],
                    'Country Destination': row['Country Destination'],
                    'Vendor': row['Vendor'],
                    'Revenue': row['Revenue'],
                    'Cost': row['Cost'],
                    'Profit': row['Profit'],
                    'Profit %': profit_pct
                })
            
            # Calculate totals for this Trunk Group + Country (round to 2 decimal places)
            total_revenue = round(group_df['Revenue'].sum(), 2)
            total_cost = round(group_df['Cost'].sum(), 2)
            total_profit = round(group_df['Profit'].sum(), 2)
            
            # Calculate profit percentage for totals
            total_profit_pct = round((total_profit / total_revenue * 100), 2) if total_revenue != 0 else 0.0
            
            # Add totals row (empty for descriptive columns, totals for financial columns)
            processed_rows.append({
                'Customer Relationships': '',
                'Trunk Group': '',
                'Country Destination': '',
                'Vendor': '',
                'Revenue': total_revenue,
                'Cost': total_cost,
                'Profit': total_profit,
                'Profit %': total_profit_pct
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
                        'Profit': '',
                        'Profit %': ''
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
        
        # Count OPS/IVG/PROXY 2 vendors for summary (need to recalculate after grouping)
        ops_ivg_proxy_count = ops_ivg_proxy_mask.sum()
        
        # Return file path, summary, and dataframe
        summary = "### ✅ Processing Complete!\n\n"
        summary += f"- **Total input rows:** {len(df)}\n"
        summary += f"- **Recalculated Vendors (OPS/IVG/PROXY 2):** {ops_ivg_proxy_count}\n"
        summary += f"- **Groups (Trunk + Country):** {len(unique_groups)}\n"
        summary += f"- **Output rows:** {len(result_df)}\n"
        summary += f"\nFile saved as: `{output_filename}`"
        
        return str(output_path), summary, None, result_df
        
    except Exception as e:
        return None, f"### ❌ Error processing file\n{str(e)}", None, None


def process_file_interface(file):
    """
    Gradio interface function for processing uploaded file
    """
    if file is None:
        return None, "### ⚠️ Warning\nPlease upload a CSV file first.", None, get_processed_files_list()
    
    output_path, message, _, result_df = process_csv(file.name)
    
    if output_path is None:
        return None, message, None, get_processed_files_list()
    
    # Get updated list of processed files
    files_list = get_processed_files_list()
    
    return output_path, message, result_df, files_list


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
        return get_processed_files_list(), "### ⚠️ Deletion Cancelled\nPlease check the confirmation box to proceed."
    
    processed_dir = Path("processed")
    file_path = processed_dir / filename
    
    if file_path.exists() and file_path.is_file():
        try:
            file_path.unlink()
            updated_list = get_processed_files_list()
            return updated_list, f"### ✅ Success\nFile `{filename}` has been deleted."
        except Exception as e:
            return get_processed_files_list(), f"### ❌ Error\nCould not delete file: {str(e)}"
    
    return get_processed_files_list(), f"### ❌ Error\nFile `{filename}` not found."


# Custom CSS for UI polish
custom_css = """
footer {visibility: hidden}
.gr-button-primary {
    background: linear-gradient(90deg, #4f46e5 0%, #3b82f6 100%);
    border: none;
}
.gr-form {
    background-color: transparent !important;
    border: none !important;
}
"""

# Theme configuration
theme = gr.themes.Soft(
    primary_hue="indigo",
    secondary_hue="slate",
    neutral_hue="slate",
    font=[gr.themes.GoogleFont("Inter"), "ui-sans-serif", "system-ui", "sans-serif"]
).set(
    button_primary_background_fill="*primary_600",
    button_primary_background_fill_hover="*primary_700",
    button_secondary_background_fill="*neutral_200",
    button_secondary_background_fill_hover="*neutral_300"
)

with gr.Blocks(title="CSV Data Processor") as app:
    
    with gr.Row():
        with gr.Column(scale=1):
            gr.Markdown("# 📊 CSV Data Processor")
            gr.Markdown("Transform and analyze your customer data with precision.")
    
    with gr.Tabs() as tabs:
        # ==================== TAB 1: PROCESS DATA ====================
        with gr.Tab("Process Data", id="tab_process"):
            with gr.Row():
                with gr.Column(scale=1):
                    # Input Section
                    with gr.Group():
                        gr.Markdown("### 1. Upload File")
                        file_input = gr.File(
                            label="Drop CSV here or click to upload",
                            file_types=[".csv"],
                            type="filepath",
                            height=100
                        )
                        process_btn = gr.Button("🚀 Process CSV Data", variant="primary", size="lg")

                with gr.Column(scale=1):
                    # Status & Result Section
                    with gr.Group():
                        gr.Markdown("### 2. Results")
                        status_output = gr.Markdown(value="Waiting for input...")
                        file_output = gr.File(label="Download Result", type="filepath", interactive=False)
            
            # Preview Section
            with gr.Row():
                with gr.Column():
                    gr.Markdown("### 3. Data Preview")
                    preview_output = gr.Dataframe(
                        label="Processed Data View",
                        interactive=False,
                        wrap=True
                        # height argument removed for compatibility with new Gradio versions if needed,
                        # but standard Gradio usually supports it. The error was TypeError: Dataframe.__init__() got an unexpected keyword argument 'height'
                        # which suggests the installed Gradio version (6.x) changed the API.
                        # I'll rely on default height or CSS.
                    )

        # ==================== TAB 2: FILE ARCHIVE ====================
        with gr.Tab("File Archive", id="tab_archive"):
            gr.Markdown("### 📂 Manage Processed Files")
            
            with gr.Row():
                # Left Column: File List
                with gr.Column(scale=2):
                    files_dataframe = gr.Dataframe(
                        label="Available Files",
                        headers=["Filename", "Created", "Size"],
                        interactive=False,
                        value=get_processed_files_dataframe(),
                        wrap=True
                    )
                    refresh_btn = gr.Button("🔄 Refresh List", variant="secondary", size="sm")

                # Right Column: Actions
                with gr.Column(scale=1):
                    with gr.Group():
                        gr.Markdown("### Actions")

                        selected_filename = gr.Dropdown(
                            label="Select File to Manage",
                            choices=get_processed_files_dropdown(),
                            interactive=True,
                            value=None
                        )

                        download_file_btn = gr.Button("⬇️ Download", variant="primary")
                        download_file_output = gr.File(label="Download Link", visible=False)

                        gr.HTML("<hr style='margin: 20px 0; opacity: 0.5;'>")

                        gr.Markdown("#### Danger Zone")
                        delete_confirm_checkbox = gr.Checkbox(
                            label="I confirm I want to delete this file",
                            value=False
                        )
                        delete_file_btn = gr.Button("🗑️ Delete File", variant="stop")

                        action_status = gr.Markdown(value="")

                        # Hidden state for file list text (used for logic if needed)
                        files_list_output = gr.Textbox(visible=False, value=get_processed_files_list())

    # ==================== EVENT WIRING ====================
    
    # Helper to update file lists
    def update_files_display():
        return (
            get_processed_files_dataframe(),
            gr.update(choices=get_processed_files_dropdown()),
            get_processed_files_list()
        )

    # Process Button Logic
    process_btn.click(
        fn=process_file_interface,
        inputs=file_input,
        outputs=[file_output, status_output, preview_output, files_list_output]
    ).then(
        fn=update_files_display,
        inputs=None,
        outputs=[files_dataframe, selected_filename, files_list_output]
    )

    # Refresh Button Logic
    refresh_btn.click(
        fn=update_files_display,
        inputs=None,
        outputs=[files_dataframe, selected_filename, files_list_output]
    )

    # Download Logic (Archive Tab)
    def handle_download(filename):
        if not filename:
            return None, "### ⚠️ Warning\nPlease select a file first."
        file_path = download_processed_file(filename)
        if file_path:
            return file_path, f"### ✅ Ready\nReady to download: `{filename}`"
        return None, f"### ❌ Error\nFile `{filename}` not found."
    
    download_file_btn.click(
        fn=handle_download,
        inputs=selected_filename,
        outputs=[download_file_output, action_status]
    )

    # Delete Logic (Archive Tab)
    def handle_delete(filename, confirm, current_list):
        if not filename:
            df, dropdown, _ = update_files_display()
            return current_list, df, dropdown, "### ⚠️ Warning\nPlease select a file first.", gr.update()
        
        if not confirm:
            df, dropdown, _ = update_files_display()
            return current_list, df, dropdown, "### ⚠️ Warning\nPlease confirm deletion.", gr.update()
        
        updated_list, message = delete_processed_file(filename, confirm)
        updated_df, updated_dropdown, _ = update_files_display()

        # Reset selection and confirmation
        return updated_list, updated_df, gr.update(choices=updated_dropdown, value=None), message, gr.update(value=False)

    delete_file_btn.click(
        fn=handle_delete,
        inputs=[selected_filename, delete_confirm_checkbox, files_list_output],
        outputs=[files_list_output, files_dataframe, selected_filename, action_status, delete_confirm_checkbox]
    )

if __name__ == "__main__":
    server_name = os.environ.get("GRADIO_SERVER_NAME", "0.0.0.0")
    server_port = int(os.environ.get("GRADIO_SERVER_PORT", 7860))
    app.launch(
        share=False,
        server_name=server_name,
        server_port=server_port,
        theme=theme,
        css=custom_css
    )

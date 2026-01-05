# CSV Data Processing Web Application

A Gradio web application for processing customer CSV files with automated filtering, grouping, and aggregation.

## Features

- **Column Removal**: Automatically removes unwanted columns (Attempts, Completions, Minutes, ASR %, NER %, Aloc, PPM, PRV, NEPR %, SDR %, MOS, PDD, LCR Depth)
- **Row Filtering**: Removes rows where Vendor OR Country Destination is empty
- **OPS/IVG Vendor Handling**: For vendors containing "OPS" or "IVG":
  - Keeps the row and Revenue value
  - Clears Cost and Profit (sets to 0)
  - This means totals include Revenue from all vendors, but Cost/Profit only from non-OPS/IVG vendors
- **Grouping & Totals**: Groups data by Trunk Group and calculates totals (Revenue, Cost, Profit) for each group
- **Formatting**: Adds 5 empty rows between different Trunk Groups for better readability

## Installation

### Using uv (Recommended)

1. Install [uv](https://github.com/astral-sh/uv) if you haven't already:
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

2. Install dependencies:
```bash
# Install the package and its dependencies from pyproject.toml
uv pip install --system -e .

# Or install dependencies directly
uv pip install --system "gradio>=4.0.0" "pandas>=2.0.0" "numpy>=1.24.0"
```

### Using pip (Alternative)

1. Install required dependencies:
```bash
pip install -r requirements.txt
```

## Usage

1. Start the application:
```bash
python app.py
```

2. Open your web browser and navigate to the URL shown in the terminal (typically `http://localhost:7860`)

3. Upload your CSV file using the file upload component

4. Click "Process CSV" to start processing

5. Download the processed CSV file from the download section

## Input Requirements

Your CSV file must contain the following columns:
- Customer Relationships
- Trunk Group
- Country Destination
- Vendor
- Revenue
- Cost
- Profit

## Output Format

The processed CSV will contain:
- Only the required columns (Customer Relationships, Trunk Group, Country Destination, Vendor, Revenue, Cost, Profit)
- Filtered rows (no empty Vendor/Country Destination)
- OPS/IVG vendors with Revenue preserved but Cost/Profit set to 0
- Totals row after each Trunk Group (Revenue includes all vendors, Cost/Profit excludes OPS/IVG)
- 5 empty rows between each Trunk Group for spacing

## Technical Details

- Built with Gradio for the web interface
- Uses pandas for data processing
- Processes files in-memory for efficiency
- Creates temporary files for download

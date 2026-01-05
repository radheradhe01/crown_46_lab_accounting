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

## Quick Start (One-Line Docker Command)

Run the application with a single Docker command:

```bash
docker build -t csv-processor . && docker run -d -p 9995:7860 --name csv-processor-app --rm -v $(pwd)/processed:/app/processed csv-processor
```

**Command breakdown:**
- `docker build -t csv-processor .`: Builds the Docker image with tag "csv-processor"
- `&&`: Chains commands (runs second only if first succeeds)
- `-d`: Runs container in detached mode (background)
- `-p 9995:7860`: Maps host port 9995 to container port 7860 (access at http://localhost:9995)
- `--name csv-processor-app`: Names the container
- `--rm`: Automatically removes container when stopped
- `-v $(pwd)/processed:/app/processed`: Mounts processed directory for file persistence

**Alternative using Docker Compose:**

```bash
docker compose up -d --build
```

**Access the application:**
Open your browser at `http://localhost:9995`

**Stop the container:**
```bash
docker stop csv-processor-app
```

## Usage

### Local Development

1. Start the application:
```bash
python app.py
```

2. Open your web browser and navigate to the URL shown in the terminal (typically `http://localhost:9995` for Docker, or `http://localhost:7860` for local development)

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

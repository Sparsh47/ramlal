# AI Job Agent 🚀

An automated AI-powered job search agent that parses your resume, generates targeted search queries, finds relevant job listings across multiple platforms, and scores them based on your profile.

## 🌟 Features

- **Resume Intelligence**: Automatically parses `resume.pdf` to extract skills, experience level, and tech stack.
- **Multi-Platform Search**: Searches LinkedIn, Lever, and Greenhouse using AI-generated, optimized search queries.
- **Smart Fetching & Scraping**:
    - Uses **Native APIs** for Lever and Greenhouse for 100% accuracy.
    - **Direct Scraping** for LinkedIn.
    - **Snippet Fallback** for JS-heavy or protected sites (like Wellfound).
- **AI Fit Scoring**: Uses Groq (Llama-3 70B) to score jobs (1-10) and provide reasoning for the match.
- **Stateful Memory**: Remembers previously found jobs in `jobs.xlsx` to skip duplicates and save API tokens.
- **Visual Excel Export**: Generates a color-coded spreadsheet highlighting "Auto-Apply Ready" vs. "Manual Review" roles.

## 🛠 Project Structure

```text
├── main.py              # Main orchestration & state management
├── config/
│   ├── resume_parser.py # PDF extraction & skill profiling
│   ├── tinyfish_client.py # Search, normalization, & platform-specific fetching
│   └── groq_client.py   # LLM interface wrapper
├── lib/
│   ├── query_builder.py # Generates Role + Skill based search queries
│   ├── job_scorer.py    # Fit scoring & reasoning logic
│   └── excel_writer.py  # Excel generation, appending, & color-coding
├── resume.pdf           # Your resume (input)
└── jobs.xlsx            # Generated job leads (output)
```

## 🚀 Getting Started

### 1. Prerequisites
- Python 3.10+
- Groq API Key (Llama-3 access)
- Tinyfish API Key (Search & Fetch access)

### 2. Installation
```bash
# Clone the repository
git clone <your-repo-url>
cd job-agent

# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install requests openpyxl PyMuPDF groq trafilatura html2text pandas
```

### 3. Configuration
Create a `.env` file in the root directory:
```env
TINYFISH_API_KEY=your_tinyfish_key
GROQ_API_KEY=your_groq_key
```

### 4. Run the Agent
Place your resume as `resume.pdf` in the root folder and run:
```bash
python3 main.py
```

## 📊 Output
The agent will generate (or append to) a `jobs.xlsx` file:
- **✅ Yes (Green)**: Full job description parsed successfully; high confidence score.
- **❌ Manual (Yellow)**: Scored based on search snippet only; requires manual page check.

## 📝 Logic Flow
1. Loads existing URLs from `jobs.xlsx` to avoid duplicates.
2. Extracts your profile from `resume.pdf`.
3. Generates 12 diverse search queries.
4. Searches and filters for new unique URLs.
5. Performs quick scoring on snippets.
6. For top matches, attempts to fetch full JDs via APIs or scraping.
7. Performs final re-scoring and appends new leads to Excel.

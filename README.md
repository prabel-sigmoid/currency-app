# Currency Exchange Rate Analyzer

A comprehensive full-stack application designed to track, analyze, and visualize historical currency exchange rates against the US Dollar (USD). It features a robust Python backend,  React frontend, and cloud-native infrastructure for deployment.

## Features

- **Real-time Data Fetching**: Retrieves historical and current exchange rates from the Frankfurter API (European Central Bank).
- **Interactive Visualizations**: Dynamic line charts powered by Recharts for trend analysis.
- **CSV Data Analysis**: Upload custom exchange rate CSV files for processing and storage.
- **Data Persistence**: Integrated PostgreSQL database to store and manage historical data and upload records.
- **Comprehensive Statistics**: Detailed summaries including percentage changes, min/max rates, and performance trends.
- **Export Capabilities**: Download analyzed data as CSV for offline use.
- **Monitoring & Metrics**: Prometheus instrumentation for performance tracking.
- **Cloud Native Infrastructure**: Fully automated deployment using Terraform (GCP/GKE) and Kubernetes manifests.

---

## 🛠️ Tech Stack

### Backend

- **Language**: Python
- **Framework**: FastAPI
- **Database**: PostgreSQL (via `psycopg2`)
- **Monitoring**: Prometheus (via `prometheus-fastapi-instrumentator`)
- **Web Server**: Uvicorn

### Frontend

- **Framework**: [React](https://reactjs.org/)
- **Styling**: [Tailwind CSS](https://tailwindcss.com/)
- **Icons**: [Lucide React](https://lucide.dev/)
- **Charts**: [Recharts](https://recharts.org/)

### DevOps & Infrastructure

- **Infrastructure as Code**: [Terraform](https://www.terraform.io/) (Targeting Google Cloud Platform - GKE)
- **Containerization**: [Docker](https://www.docker.com/)
- **Orchestration**: [Kubernetes](https://kubernetes.io/) (K8s)
- **Package Management**: [Helm](https://helm.sh/)

---

## 📂 Project Structure

```text
.
├── be/                    # Backend (FastAPI)
│   ├── main.py            # API logic and entry point
│   ├── Dockerfile         # Backend containerization
│   └── requirements.txt   # Python dependencies
├── ui/                    # Frontend (React/Vite)
│   ├── src/               # React source files
│   ├── tailwind.config.js # Styling configuration
│   └── Dockerfile         # Frontend containerization
├── tf/                    # Infrastructure (Terraform - GCP)
│   ├── main.tf            # GKE Cluster definition
│   └── variable.tf        # Cloud configuration
├── k8s/                   # Kubernetes Manifests
│   ├── backend.yaml       # API deployment & service
│   ├── frontend.yaml      # UI deployment & service
│   ├── postgres.yaml      # DB statefulset & service
│   └── ingrees.yaml       # Ingress configuration
├── currency-app/          # Helm Chart
│   ├── templates/         # Helm templates
│   └── values.yaml        # Helm values
└── data/                  # Sample data & templates
```

---

## Getting Started

### Prerequisites

- Python 3.9+
- Node.js & npm
- Docker & Docker Compose (optional)
- Terraform (for cloud deployment)

### Local Development

#### 1. Backend Setup

1. Navigate to `be/` directory.
2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Set environment variables for the database:
   ```bash
   export DB_CONFIG_HOST=localhost
   export DB_CONFIG_DATABASE=currency_db
   export DB_CONFIG_USERNAME=postgres
   export DB_CONFIG_PASSWORD=your_password
   export DB_CONFIG_PORT=5432
   ```
5. Run the server:
   ```bash
   uvicorn main:app --reload
   ```

#### 2. Frontend Setup

1. Navigate to `ui/` directory.
2. Install dependencies:
   ```bash
   npm install
   ```
3. Start the development server:
   ```bash
   npm run dev
   ```

---

## API Endpoints

- `GET /currencies`: Returns a list of all supported currency codes.
- `POST /exchange-rates`: Fetches historical rates for selected currencies and date range.
- `POST /analyze-csv`: Processes an uploaded CSV file and stores data in the DB.
- `GET /db-stats`: Provides statistics on stored records and recent uploads.
- `GET /download-template`: Downloads a sample CSV template for uploads.
- `GET /metrics`: Prometheus metrics endpoint.

---

## Deployment

### Infrastructure (Terraform)

1. Navigate to `tf/`.
2. Initialize and apply Terraform:
   ```bash
   terraform init
   terraform apply
   ```

### Kubernetes (K8s)

Deploy to GKE or any K8s cluster:

```bash
kubectl apply -f k8s/
```

### Helm

Deploy using the included Helm chart:

```bash
helm install currency-app ./currency-app
```

---

## 📊 CSV Format for Uploads

Ensure your CSV follows this structure:

```csv
Date,Currency,Rate
2024-01-01,EUR,0.92
2024-01-01,GBP,0.78
2024-01-02,JPY,140.50
```

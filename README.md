# UrbanEye

Land-cover mapping and change detection from satellite imagery.

- `UrbanEye_UNetPP_HighAccuracy.ipynb`: trains the U-Net++ (EfficientNet-B4) model on OpenEarthMap (8 classes) in Google Colab.
- `backend/`: FastAPI server. Runs the model, downloads satellite imagery, and compares dates. See [backend/README.md](backend/README.md).
- `frontend/`: React + Vite web app. Map analysis, change over time, and photo analysis. See [frontend/README.md](frontend/README.md).

## Quick start (Windows PowerShell)

1. Train the model in Colab. Download `MyDrive/UrbanEye/checkpoints/unetpp_b4_oem8_v2/best.pth` and save it as
   `backend/models/unetpp_oem8_best.pth`.
2. Backend (terminal 1):
   ```powershell
   cd backend
   python -m venv .venv; .venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   copy .env.example .env
   uvicorn app.main:app --reload --port 8000
   ```
3. Frontend (terminal 2):
   ```powershell
   cd frontend
   npm install
   npm run dev
   ```
4. Open http://localhost:5173.

The app also runs before the model is trained: the satellite map, dates, and imagery work, and the
header shows "Model not loaded" until the weights file is in place.

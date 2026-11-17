@echo off
echo ============================================================================
echo  BUILDING REACT FRONTEND INTO DJANGO WHITENOISE (backend/frontend_dist)
echo ============================================================================
cd /d "%~dp0frontend"
if not exist "node_modules" (
    echo [1/3] Installing frontend dependencies...
    call npm install
)
echo [2/3] Building React production bundle to ../backend/frontend_dist...
call npm run build

echo ============================================================================
echo  STARTING DJANGO + WHITENOISE SERVER ON http://localhost:8000
echo ============================================================================
cd /d "%~dp0backend"
python manage.py runserver 0.0.0.0:8000

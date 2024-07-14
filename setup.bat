@echo off

:: Check for Python installation
where python >nul 2>nul
if %errorlevel% neq 0 (
    echo Python is not installed. Please install Python from https://www.python.org/downloads/ and try again.
    exit /b 1
)

:: Create a virtual environment
echo Creating a virtual environment...
python -m venv venv

:: Activate the virtual environment
echo Activating the virtual environment...
call venv\Scripts\activate

:: Upgrade pip
echo Upgrading pip...
python -m pip install --upgrade pip

:: Install Flask
echo Installing Flask...
pip install Flask

:: Install additional dependencies if needed
echo Installing additional dependencies...
pip install -r requirements.txt

echo Setup complete. To activate the virtual environment in the future, run:
echo call venv\Scripts\activate

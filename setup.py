"""
Setup script for Face Recognition System
Run this to initialize the system
"""
import os
import sys
import subprocess
from pathlib import Path

def print_header(text):
    """Print formatted header"""
    print("\n" + "="*80)
    print(f"  {text}")
    print("="*80)

def check_python_version():
    """Check if Python version is compatible"""
    print_header("Checking Python Version")
    
    version = sys.version_info
    print(f"Python version: {version.major}.{version.minor}.{version.micro}")
    
    if version.major < 3 or (version.major == 3 and version.minor < 10):
        print("❌ Python 3.10+ is required")
        return False
    
    print("✅ Python version is compatible")
    return True

def check_mysql():
    """Check if MySQL is installed and running"""
    print_header("Checking MySQL")
    
    try:
        result = subprocess.run(
            ["mysql", "--version"],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            print(f"✅ MySQL found: {result.stdout.strip()}")
            return True
        else:
            print("❌ MySQL not found")
            return False
    except FileNotFoundError:
        print("❌ MySQL not installed")
        print("Install MySQL:")
        print("  macOS: brew install mysql")
        print("  Linux: sudo apt-get install mysql-server")
        return False

def create_directories():
    """Create necessary directories"""
    print_header("Creating Directories")
    
    directories = [
        "snapshots",
        "snapshots/events",
        "snapshots/enrollments",
        "snapshots/temp",
        "logs",
        "tests/sample_images"
    ]
    
    base_dir = Path(__file__).parent
    
    for dir_name in directories:
        dir_path = base_dir / dir_name
        dir_path.mkdir(parents=True, exist_ok=True)
        print(f"✅ Created: {dir_name}")

def create_env_file():
    """Create .env file from example if it doesn't exist"""
    print_header("Environment Configuration")
    
    base_dir = Path(__file__).parent
    env_file = base_dir / ".env"
    env_example = base_dir / ".env.example"
    
    if env_file.exists():
        print("⚠️  .env file already exists")
        response = input("Do you want to overwrite it? (y/N): ")
        if response.lower() != 'y':
            print("Keeping existing .env file")
            return
    
    if env_example.exists():
        import shutil
        shutil.copy(env_example, env_file)
        print("✅ Created .env file from .env.example")
        print("⚠️  Please edit .env and update:")
        print("   - MYSQL_PASSWORD")
        print("   - API_KEY")
        print("   - IP_WEBCAM_URL (when ready to use IP webcam)")
    else:
        print("❌ .env.example not found")

def install_dependencies():
    """Install Python dependencies"""
    print_header("Installing Python Dependencies")
    
    print("This may take a few minutes...")
    
    try:
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "--upgrade", "pip"],
            check=True
        )
        print("✅ pip upgraded")
        
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "-r", "requirements.txt"],
            check=True
        )
        print("✅ Dependencies installed")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install dependencies: {e}")
        return False

def create_database():
    """Provide instructions for database creation"""
    print_header("Database Setup")
    
    print("Please run the following SQL commands in MySQL:")
    print("")
    print("mysql -u root -p")
    print("")
    print("CREATE DATABASE face_recognition CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;")
    print("CREATE USER '2cloud'@'localhost' IDENTIFIED BY 'your_password';")
    print("GRANT ALL PRIVILEGES ON face_recognition.* TO '2cloud'@'localhost';")
    print("FLUSH PRIVILEGES;")
    print("EXIT;")
    print("")
    
    response = input("Have you created the database? (y/N): ")
    return response.lower() == 'y'

def test_imports():
    """Test if key dependencies can be imported"""
    print_header("Testing Imports")
    
    imports = [
        ("fastapi", "FastAPI"),
        ("torch", "PyTorch"),
        ("PIL", "Pillow"),
        ("cv2", "OpenCV"),
        ("sqlalchemy", "SQLAlchemy"),
        ("facenet_pytorch", "FaceNet PyTorch")
    ]
    
    all_ok = True
    for module_name, display_name in imports:
        try:
            __import__(module_name)
            print(f"✅ {display_name}")
        except ImportError:
            print(f"❌ {display_name} - Failed to import")
            all_ok = False
    
    return all_ok

def print_next_steps():
    """Print next steps"""
    print_header("Setup Complete! 🎉")
    
    print("\n📋 Next Steps:\n")
    print("1. Edit .env file with your configuration:")
    print("   nano .env")
    print("")
    print("2. Make sure MySQL database is created")
    print("")
    print("3. Start the server:")
    print("   python main.py")
    print("")
    print("4. Access the system:")
    print("   🌐 Web Interface: http://localhost:8000")
    print("   📚 API Docs: http://localhost:8000/docs")
    print("   🧪 Test Interface: http://localhost:8000/test")
    print("")
    print("5. Enroll your first person via test interface or API")
    print("")
    print("6. (Optional) Setup IP Webcam on your mobile phone:")
    print("   - Install 'IP Webcam' app (Android) or 'IP Camera Lite' (iOS)")
    print("   - Update config/ip_webcam_config.py with your camera IP")
    print("")
    print("📚 For more information, see README.md")
    print("")

def main():
    """Main setup function"""
    print("\n" + "🎯"*40)
    print("Face Recognition System - Setup")
    print("🎯"*40)
    
    # Check Python version
    if not check_python_version():
        sys.exit(1)
    
    # Check MySQL
    check_mysql()
    
    # Create directories
    create_directories()
    
    # Create .env file
    create_env_file()
    
    # Install dependencies
    print("\nDo you want to install Python dependencies?")
    response = input("This will run: pip install -r requirements.txt (y/N): ")
    if response.lower() == 'y':
        if not install_dependencies():
            print("\n⚠️  Dependencies installation failed")
            print("Try manually: pip install -r requirements.txt")
    
    # Test imports (if dependencies installed)
    if response.lower() == 'y':
        test_imports()
    
    # Database setup instructions
    create_database()
    
    # Print next steps
    print_next_steps()

if __name__ == "__main__":
    main()

"""
Storage service for snapshots and file management
"""
import os
import shutil
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional
from PIL import Image
import hashlib

from config.settings import SNAPSHOTS_DIR, MAX_SNAPSHOT_AGE_DAYS

logger = logging.getLogger(__name__)


class StorageService:
    """Handle snapshot storage and file management"""
    
    def __init__(self):
        self.snapshots_dir = Path(SNAPSHOTS_DIR)
        self.snapshots_dir.mkdir(exist_ok=True, parents=True)
        
        # Create subdirectories
        self.events_dir = self.snapshots_dir / "events"
        self.enrollments_dir = self.snapshots_dir / "enrollments"
        self.temp_dir = self.snapshots_dir / "temp"
        
        for dir_path in [self.events_dir, self.enrollments_dir, self.temp_dir]:
            dir_path.mkdir(exist_ok=True, parents=True)
        
        logger.info(f"✅ Storage service initialized at {self.snapshots_dir}")
    
    def save_snapshot(
        self,
        image: Image.Image,
        prefix: str = "snapshot",
        person_id: Optional[str] = None,
        camera_id: Optional[str] = None,
        subdirectory: str = "events"
    ) -> tuple[str, str]:
        """
        Save snapshot image
        
        Args:
            image: PIL Image to save
            prefix: Filename prefix
            person_id: Person ID (optional)
            camera_id: Camera ID (optional)
            subdirectory: Subdirectory name (events, enrollments, temp)
            
        Returns:
            (relative_path, full_path) tuple
        """
        try:
            # Generate filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # Create unique filename with hash
            img_hash = hashlib.md5(image.tobytes()).hexdigest()[:8]
            
            components = [prefix, timestamp]
            if person_id:
                components.append(person_id)
            if camera_id:
                components.append(camera_id)
            components.append(img_hash)
            
            filename = "_".join(components) + ".jpg"
            
            # Determine save directory
            if subdirectory == "events":
                save_dir = self.events_dir
            elif subdirectory == "enrollments":
                save_dir = self.enrollments_dir
            elif subdirectory == "spoofing":
                # Create spoofing directory if it doesn't exist
                spoofing_dir = self.snapshots_dir / "spoofing"
                spoofing_dir.mkdir(exist_ok=True, parents=True)
                save_dir = spoofing_dir
            else:
                save_dir = self.temp_dir
            
            # Create date-based subdirectory
            date_dir = save_dir / datetime.now().strftime("%Y-%m-%d")
            date_dir.mkdir(exist_ok=True, parents=True)
            
            # Full path
            full_path = date_dir / filename
            
            # Save image
            image.save(full_path, "JPEG", quality=85, optimize=True)
            
            # Relative path from snapshots root
            relative_path = str(full_path.relative_to(self.snapshots_dir))
            
            logger.info(f"💾 Saved snapshot: {relative_path}")
            
            return relative_path, str(full_path)
        
        except Exception as e:
            logger.error(f"Error saving snapshot: {e}")
            return "", ""
    
    def get_snapshot_url(self, relative_path: str, base_url: str = "http://localhost:8000") -> str:
        """Generate URL for snapshot"""
        if not relative_path:
            return ""
        return f"{base_url}/snapshots/{relative_path}"
    
    def cleanup_old_snapshots(self, max_age_days: int = MAX_SNAPSHOT_AGE_DAYS):
        """Delete snapshots older than max_age_days"""
        try:
            cutoff_date = datetime.now() - timedelta(days=max_age_days)
            deleted_count = 0
            
            for snapshot_type_dir in [self.events_dir, self.temp_dir]:
                if not snapshot_type_dir.exists():
                    continue
                
                for date_dir in snapshot_type_dir.iterdir():
                    if not date_dir.is_dir():
                        continue
                    
                    try:
                        dir_date = datetime.strptime(date_dir.name, "%Y-%m-%d")
                        if dir_date < cutoff_date:
                            shutil.rmtree(date_dir)
                            deleted_count += 1
                            logger.info(f"🗑️  Deleted old snapshots: {date_dir}")
                    except ValueError:
                        continue
            
            if deleted_count > 0:
                logger.info(f"✅ Cleaned up {deleted_count} old snapshot directories")
            
            return deleted_count
        
        except Exception as e:
            logger.error(f"Error cleaning up snapshots: {e}")
            return 0
    
    def get_storage_stats(self) -> dict:
        """Get storage statistics"""
        try:
            def get_dir_size(path: Path) -> int:
                total = 0
                for entry in path.rglob('*'):
                    if entry.is_file():
                        total += entry.stat().st_size
                return total
            
            events_size = get_dir_size(self.events_dir)
            enrollments_size = get_dir_size(self.enrollments_dir)
            temp_size = get_dir_size(self.temp_dir)
            
            total_size = events_size + enrollments_size + temp_size
            
            return {
                "total_size_mb": round(total_size / (1024 * 1024), 2),
                "events_size_mb": round(events_size / (1024 * 1024), 2),
                "enrollments_size_mb": round(enrollments_size / (1024 * 1024), 2),
                "temp_size_mb": round(temp_size / (1024 * 1024), 2),
                "snapshots_dir": str(self.snapshots_dir)
            }
        
        except Exception as e:
            logger.error(f"Error getting storage stats: {e}")
            return {}

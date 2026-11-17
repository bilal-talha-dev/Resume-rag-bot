import os
import subprocess
from pathlib import Path
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Builds the React frontend (frontend/) into backend/frontend_dist/ for WhiteNoise serving."

    def handle(self, *args, **options):
        backend_dir = Path(__file__).resolve().parent.parent.parent.parent
        frontend_dir = backend_dir.parent / "frontend"

        if not frontend_dir.exists():
            self.stderr.write(self.style.ERROR(f"Frontend directory not found at {frontend_dir}"))
            return

        self.stdout.write(self.style.SUCCESS(f"Building React frontend in {frontend_dir}..."))
        npm_cmd = "npm.cmd" if os.name == "nt" else "npm"

        if not (frontend_dir / "node_modules").exists():
            self.stdout.write("Running npm install...")
            subprocess.run([npm_cmd, "install"], cwd=str(frontend_dir), check=True)

        self.stdout.write("Running npm run build -> backend/frontend_dist/...")
        subprocess.run([npm_cmd, "run", "build"], cwd=str(frontend_dir), check=True)
        self.stdout.write(
            self.style.SUCCESS(
                "Frontend built into backend/frontend_dist/! Run 'python manage.py runserver' to serve."
            )
        )

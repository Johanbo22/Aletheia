import sys
from pathlib import Path
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer

project_root = Path(__file__).resolve().parent.parent
sys.path.append(str(project_root))

from ui.dialogs import ProgressDialog

def main() -> None:
    app = QApplication(sys.argv)
    style_path = project_root / "ui" / "styles" / "dialogs.css"
    if style_path.exists():
        app.setStyleSheet(style_path.read_text(encoding="utf-8"))
    else:
        print(f"Warning: Could not find stylesheet at {style_path}")

    dialog = ProgressDialog(title="Testing Progress UI", message="Processing dataset...")
    dialog.set_indeterminate(True)
    dialog.set_status("Negotiating connection...")
    dialog.show()

    current_progress = 0
    phase = "connecting"
    
    def simulate_work() -> None:
        """Simulates an ongoing process updating the dialog state in a loop."""
        nonlocal current_progress, phase
        
        if phase == "connecting":
            current_progress += 1
            if current_progress > 40:
                phase = "processing"
                current_progress = 0
                dialog.set_indeterminate(False)
                dialog.set_message("Processing dataset...")
        
        elif phase == "processing":
            current_progress += 2
            
            if current_progress <= 100:
                dialog.update_progress(current_progress, f"Processed {current_progress} out of 100 items...")
            
            if current_progress == 90:
                dialog.set_message("Finalizing data operations...")
                dialog.set_status("Almost done...")
                
            if current_progress >= 130: 
                phase = "connecting"
                current_progress = 0
                dialog.set_indeterminate(True)
                dialog.set_message("Reconnecting to data source...")
                dialog.set_status("Negotiating connection...")
    
    timer = QTimer()
    timer.timeout.connect(simulate_work)
    timer.start(50)
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
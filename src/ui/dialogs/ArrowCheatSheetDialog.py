from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QDialog, QLabel, QVBoxLayout, QWidget

class ArrowCheatSheetDialog(QDialog):
    """
    A non modal floating tool window that provides a cheat sheet for arrow prop dict keys and values
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Arrow Properties Cheat Sheet")

        self.setWindowFlags(Qt.WindowType.Tool)
        self.setModal(False)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)

        help_label = QLabel()
        help_label.setWordWrap(True)
        help_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextBrowserInteraction)

        html_content = """
                <style>
                    table { border-collapse: collapse; width: 100%; margin-top: 10px; }
                    th { text-align: left; padding: 8px; border-bottom: 2px solid #888888; font-size: 13px; }
                    td { padding: 8px; border-bottom: 1px solid #666666; font-size: 13px; }
                    code { font-family: 'Courier New', Courier, monospace; color: #007acc; font-weight: bold; }
                    h3 { margin-bottom: 2px; font-size: 15px; }
                    p { margin-top: 0px; color: #888888; font-size: 12px; }
                </style>
                <h3>Supported Customization Keys</h3>
                <p>Ensure your text is formatted as a valid dictionary.</p>
                <table>
                    <tr>
                        <th>Key</th>
                        <th>Valid Values / Examples</th>
                    </tr>
                    <tr>
                        <td><b>arrowstyle</b></td>
                        <td><code>'-'</code>, <code>'->'</code>, <code>'-['</code>, <code>'|-|'</code>, <code>'simple'</code>, <code>'fancy'</code></td>
                    </tr>
                    <tr>
                        <td><b>connectionstyle</b></td>
                        <td><code>'arc3,rad=0.2'</code>, <code>'angle3,angleA=0,angleB=90'</code>, <code>'bar'</code></td>
                    </tr>
                    <tr>
                        <td><b>color</b></td>
                        <td><code>'red'</code>, <code>'#FF0000'</code>, <code>'black'</code>, <code>'blue'</code></td>
                    </tr>
                    <tr>
                        <td><b>lw</b> or <b>linewidth</b></td>
                        <td><code>1.5</code>, <code>2.0</code> <i>(numeric float)</i></td>
                    </tr>
                    <tr>
                        <td><b>alpha</b></td>
                        <td><code>0.0</code> to <code>1.0</code> <i>(numeric float)</i></td>
                    </tr>
                    <tr>
                        <td style="border-bottom: none;"><b>shrinkA</b> / <b>shrinkB</b></td>
                        <td style="border-bottom: none;"><code>2</code>, <code>5</code> <i>(points to shrink)</i></td>
                    </tr>
                </table>
                """
        help_label.setText(html_content)
        layout.addWidget(help_label)

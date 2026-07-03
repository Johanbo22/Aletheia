from PyQt6.QtCore import QRectF, Qt
from PyQt6.QtGui import QColor, QFontMetrics, QPainter

from ui.help_animation_engine import HelpAnimationEngine

class Animation(HelpAnimationEngine):
    """
    Animation illustrating a Regex Replace operation.

    Demonstrates a regex pattern ('^INV-') highlights the matched strings and removes it
    """

    def __init__(self) -> None:
        super().__init__(duration_ms=6000)

        self.c_bg = QColor("#2b2b2b")
        self.c_table_bg = QColor("#1e1e1e")
        self.c_header_bg = QColor("#333333")
        self.c_border = QColor("#444444")
        self.c_text = QColor("#e0e0e0")

        self.c_focus_col = QColor("#2b4a6b")
        self.c_match_bg = QColor("#8b3a3a")
        self.c_match_text = QColor("#ffffff")
        self.c_success_bg = QColor("#2d5a2d")
        self.c_success_text = QColor("#ccffcc")
        self.c_panel_bg = QColor("#3a3a3a")

        self.headers = ["ID", "Invoice Code"]
        self.target_col_idx = 1

        self.data_rows = [
            ["1", "INV-1001"],
            ["2", "INV-1002"],
            ["3", "INV-1003"],
        ]
        self.match_str = "INV-"

        self.row_height = 32
        self.col_widths = [60, 160]
        self.table_width = sum(self.col_widths)

        self.start_x = (self.width() - self.table_width) / 2
        self.start_y = 120

    def draw_animation(self, painter: QPainter, progress: float) -> None:
        painter.fillRect(self.rect(), self.c_bg)

        panel_prog = self.get_eased_progress(progress, 0.1, 0.2)
        match_prog = self.get_eased_progress(progress, 0.2, 0.4)
        replace_prog = self.get_eased_progress(progress, 0.4, 0.6)
        success_prog = self.get_eased_progress(progress, 0.6, 0.8)

        self._draw_regex_panel(painter, panel_prog)

        current_x = self.start_x
        painter.setFont(self.font_bold)

        for i, header_text in enumerate(self.headers):
            w = self.col_widths[i]
            rect = QRectF(current_x, self.start_y - self.row_height, w, self.row_height)

            bg = self.c_focus_col if (i == self.target_col_idx and panel_prog > 0) else self.c_header_bg

            painter.setBrush(bg)
            painter.setPen(self.c_border)
            painter.drawRect(rect)

            painter.setPen(self.c_text)
            text_rect = rect.adjusted(5, 0, -5, 0)
            painter.drawText(text_rect, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, header_text)

            current_x += w

        painter.setFont(self.font_main)
        for r_idx, row in enumerate(self.data_rows):
            y = self.start_y + (r_idx * self.row_height)
            current_x = self.start_x

            for c_idx, text in enumerate(row):
                w = self.col_widths[c_idx]
                rect = QRectF(current_x, y, w, self.row_height)

                bg_color = self.c_table_bg
                text_color = self.c_text

                if c_idx == self.target_col_idx and success_prog > 0:
                    flash = 1.0 - abs(success_prog - 0.5) * 2
                    bg_color = self.lerp_color(self.c_table_bg, self.c_success_bg, flash)
                    text_color = self.lerp_color(self.c_text, self.c_success_text, flash)

                painter.setBrush(bg_color)
                painter.setPen(self.c_border)
                painter.drawRect(rect)
                text_rect = rect.adjusted(5, 0, -5, 0)

                if c_idx == self.target_col_idx and replace_prog < 1.0:
                    self._draw_regex_cell(
                        painter, text_rect, text, match_prog, replace_prog, text_color
                    )
                elif c_idx == self.target_col_idx and replace_prog == 1.0:
                    new_text = text.replace(self.match_str, "")
                    painter.setPen(text_color)
                    painter.drawText(text_rect, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, new_text)
                else:
                    painter.setPen(text_color)
                    painter.drawText(text_rect, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, text)

                current_x += w

    def _draw_regex_panel(self, painter: QPainter, progress: float) -> None:
        """Draws the floating information panel indicating the regex rule."""
        if progress <= 0:
            return

        panel_w = 260
        panel_h = 40
        panel_x = self.width() / 2 - panel_w / 2
        panel_y = 20 + (1.0 - progress) * -50

        rect = QRectF(panel_x, panel_y, panel_w, panel_h)
        painter.setBrush(self.c_panel_bg)
        painter.setPen(self.c_border)
        painter.drawRoundedRect(rect, 4, 4)

        painter.setPen(self.c_text)
        painter.setFont(self.font_main)

        painter.setOpacity(progress)
        text_rect = rect.adjusted(10, 0, -10, 0)
        painter.drawText(text_rect, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, "Regex: '^INV-'")
        painter.drawText(text_rect, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight, "Replace: ''")
        painter.setOpacity(1.0)

    def _draw_regex_cell(
            self,
            painter: QPainter,
            rect: QRectF,
            text: str,
            match_prog: float,
            replace_prog: float,
            base_color: QColor
    ) -> None:
        """
        Handles the granular rendering of the text fading and sliding logic.
        """
        fm = QFontMetrics(painter.font())

        if not text.startswith(self.match_str):
            painter.setPen(base_color)
            painter.drawText(rect, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, text)
            return

        match_part = self.match_str
        rest_part = text[len(self.match_str):]
        match_w = fm.horizontalAdvance(match_part)

        if match_prog > 0 and replace_prog == 0:
            highlight_bg = self.lerp_color(self.c_table_bg, self.c_match_bg, match_prog)
            highlight_rect = QRectF(rect.left(), rect.top() + 4, match_w, rect.height() - 8)
            painter.setBrush(highlight_bg)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRect(highlight_rect)

        if replace_prog > 0:
            painter.setOpacity(1.0 - replace_prog)
            painter.setPen(self.c_match_text)
            painter.drawText(rect, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, match_part)
            painter.setOpacity(1.0)

            shift = match_w * replace_prog
            rest_rect = rect.adjusted(match_w - shift, 0, 0, 0)
            painter.setPen(base_color)
            painter.drawText(rest_rect, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, rest_part)
        else:
            text_color = self.lerp_color(base_color, self.c_match_text, match_prog)
            painter.setPen(text_color)
            painter.drawText(rect, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, match_part)

            rest_rect = rect.adjusted(match_w, 0, 0, 0)
            painter.setPen(base_color)
            painter.drawText(rest_rect, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, rest_part)

import weakref
from typing import Optional, TYPE_CHECKING

from core.global_signals import ToastLevel, global_signals

if TYPE_CHECKING:
    from core.data_handler import DataHandler
    from core.subset_manager import SubsetManager
    from ui.data_tab import DataTab
    from ui.status_bar import StatusBar

class BaseDataController:
    """
    Foundation class for all DataTab sub-controllers
    Provides access to the view, data handler, subset and status bar instances
    """

    def __init__(self,
                 data_handler: "DataHandler",
                 status_bar: "StatusBar",
                 view: "DataTab",
                 subset_manager: Optional["SubsetManager"] = None,
                 ) -> None:
        self.data_handler = data_handler
        self.status_bar = status_bar
        self._view = weakref.ref(view)
        self.subset_manager = subset_manager

    @property
    def view(self) -> "DataTab":
        view_instance = self._view()
        if view_instance is None:
            raise RuntimeError("DataTab has been garbage collected")
        return view_instance

    @staticmethod
    def no_data_loaded_toast() -> None:
        """Trigger a global warning toast if a user attempts an operation with no data."""
        global_signals.request_toast(
            "No Data", "Please load data first", ToastLevel.WARNING
        )

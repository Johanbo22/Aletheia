# Object Name Reference Sheet

This file is a reference sheet for the reusable ObjectNames and properties that are in Aletheia's styling directory.
This file does not contain any objectNames or properties that are unique to their own widget. This will only contain the
objectNames that are designed to be reused.
This reference sheet does not cover the general styling associated with a widget. Those styles are defined in their
associated stylesheets.

Each objectName is sorted into a group based on the type of widget, or it's context. The objectName will be assigned a
role description to highlight it's usage and is separated into the following structure:

## [GroupName]

{
objectName: The objectName;
description: A small description of the objectName's function;
usage: How the objectName should be used;
limitations: Any limitations put on the objectName's usage. If there are none a value of NULL is assigned;
cssFile: The file which the objectName is styled in;
}
Example:

## [QPushButton]

{
objectName: MainActionButton;
description: A button that has the highest order of significance;
usage: A major action button used to do a certain operation that is of a higher level than other buttons i the current
interface context;
limitations: Only one of these buttons should be associated with a dialog, a popup window or the surrounding context;
cssFile: pushbutton;
}

# Groups

## [QPushButton]

{
objectName: MainActionButton;
description: A button that has the highest order of significance;
usage: A major action button used to do a certain operation that is of a higher level than other buttons i the current
interface context;
limitations: Only one of these buttons should be associated with a dialog, a popup window or the surrounding context;
cssFile: pushbutton;
}
{
objectName: DestructiveButton;
description: A button meant to signify a destructive action;
usage: This button is meant to be used for actions that causes a mutation upon the data or object;
limitations: Should only be used when the action causes immediate changes to the current instance of data or object. Do
not use if the resulting consequence is a preview or non-final change;
cssFile: pushbutton;
}

## ScrollArea

{
objectName: ScrollContent;
description: Applied to scroll areas;
usage: Used on ALL scroll area QWidgets;
limation: NULL;
cssFile: scrollarea;
}
{
objectName: TransparentScrollContent;
description: Applied to scroll content container widgets;
usage: Used on ALL scroll content QWidgets;
limation: NULL;
cssFile: scrollarea;
}

## Labels

{
propertyName: info_text;
description: Smaller italic text;
usage: Used to highlight information;
limitation: NULL;
cssFile: styleClassProperties;
}
{
propertyName: warning_info_text;
description: Smaller italic orange text;
usage: Used to highlight information that has a warning associated with it;
limitation: NULL;
cssFile: styleClassProperties;
}
{
propertyName: muted_text;
description: Smaller italic darker grey text;
usage: Used to highlight information where the information is not essential;
limitation: NULL;
cssFile: styleClassProperties;
}
{
propertyName: optional_badge;
description: A badge like info text;
usage: To siginify that some is optional. To be used instead of (Optional);
limitation: NULL;
cssFile: styleClassProperties;
}
{
objectName: app_version_label;
description: A small pill with the version number;
usage: Used to display the application version;
limitation: NULL;
cssFile: landing_page;
}

## Tables

{
objectName: MainDataHeader;
description: A broader header section for tables;
usage: Assigned to HeaderView() to only style the headers of tables;
limitation: Not to be used on the table itself;
cssFile: data_table_style;
}

## ToolBoxes

{
objectName: plot_type_toolbox;
description: A toolbox widget with similar styling to the QTabBar;
usage: Used for grouping tools into a more manageable setting;
limitation: A certain amount of associated tools must be required to use this widget and its styling;
cssFile: plot_tab_style;
}

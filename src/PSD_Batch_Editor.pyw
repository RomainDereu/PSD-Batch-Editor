# PSD Batch Editor
# Copyright (c) 2023-2024 Romain Dereu
# This code is licensed under MIT license (see LICENSE.txt for details)
import sys
import os
import configparser
from collections import namedtuple
from abc import ABC, abstractmethod

# Numpy is used for the display of the table model
import pandas as pd

# psd_tools is used for the analysis and printing of the files
from psd_tools import PSDImage
from psd_tools.constants import Resource

# Localization tool
import gettext

# Graphical Libraries
from PyQt6 import QtCore
from PyQt6.QtWidgets import QApplication, QMainWindow, QPushButton, QLabel, \
                            QGridLayout, QWidget, QComboBox, QTabWidget, \
                            QTableView, QFileDialog, QMessageBox, QCheckBox, \
                            QSpinBox, QHeaderView, QLineEdit, QSizePolicy
from PyQt6.QtGui import QAction
from PyQt6.QtCore import QAbstractTableModel, Qt
# All the settings the program needs to fetch in the config file
# Setups gettext with the current locale
# Language settings are modified in ChangeLanguage


class SetupSettings:
    def __init__(self):
        # Defining the paths of other files that will be accessed
        self.soft_path = os.path.dirname(__file__)
        # Main configuration file
        self.config_path = self.soft_path + "\\config.ini"
        # QSS style sheet
        self.qss_sheet_path = self.soft_path + "\\style.qss"
        self.active_config = configparser.ConfigParser()
        with open(self.config_path) as configfile:
            self.active_config.read_file(configfile)

        # Local information for gettext
        appname = 'PSDBatchEditor'
        localedir = self.soft_path + '/locales'
        self.current_language_setting = self.active_config[
                                                    "Default"]["soft_lang"]
        self.current_folder = self.active_config[
                                                "Default"]["current_folder"]
        self.current_language_name = ""

        # Gettext setup
        self.en_i18n = gettext.translation(appname, localedir, 
                                    fallback=True, languages=['en'])
        self.ja_i18n = gettext.translation(appname, localedir, 
                                    fallback=True, languages=['ja'])

    def setLanguage(self, wanted_language):
        global _
        # Language specific settings
        if(wanted_language == "en"):
            self.active_config["Default"]["soft_lang"] = "en"
            self.en_i18n.install()
            _ = self.en_i18n.gettext
            self.current_language_name = _("English")

        elif(wanted_language == "ja"):
            self.active_config["Default"]["soft_lang"] = "ja"
            self.ja_i18n.install()
            _ = self.ja_i18n.gettext
            self.current_language_name = _("Japanese")

        with open(self.config_path, "w") as configfile:
            self.active_config.write(configfile)


# Fetches all the settings. Instantiated when analyze_image is run
class CurrentSettings():
    def __init__(self):
        self.reset_settings()


    def reset_settings(self):
        # File names to be searched
        self.file_name_filter = ""
        # color modes (RGB, CMYK etc)
        self.color_modes_filter = []
        # All the resolutions are integers
        self.resolution_filter  = []
        # Layer names to be searched
        self.layer_names_filter = ""
        self.show_hidden_layers_filter = []
        # Layer names to be searched
        self.show_layer_names_filter = True


    # The settings are fetched from widgets in the 
    def fetchsettings(self):
        # deleting any existing settings
        self.reset_settings()

        # reading the file name selected
        self.file_name_filter = window.file_tab.create_tab\
                                .file_name_filter_ui.this_widget.text()

       # reading the color mode settings
        for item in window.file_tab.create_tab.color_profile_widgets_ui:
            if(item.this_widget.isChecked()):
                self.color_modes_filter.append(
                    item.this_widget.text())
                
        # reading the resolution settings
        for item in  window.file_tab.create_tab.height_width_info:
            self.resolution_filter.append(
            item.value())

        # reading the layer settings
        # layer names filter
        self.layer_names_filter = window.file_tab.create_tab\
                                .layer_name_field_ui.this_widget.text()
        # hidden layers
        if window.file_tab.create_tab.hidden_layers_ui.this_widget.isChecked():
            self.show_hidden_layers_filter = _("Yes")
        else:
            self.show_hidden_layers_filter = ""            
        # show layer names
        self.show_layer_names_filter = window.file_tab.create_tab\
                            .layer_names_shown_ui.this_widget.isChecked()

# The class in which images are analyzed
class AnalyzeImage():
    def __init__(self):
        self.all_psd_files = []
        # The list of the columns is also used in filterread 
        self.column_names = [_("File Name"),  _("Width in px"), 
                             _("Height in px"),_("Color Mode"), 
                             _("Layer list"), _("Has hidden layers")]
        # The final data is stored here
        self.hashed_data = pd.DataFrame(columns = self.column_names)
        # Checks if the program has been run
        # Useful for language changes
        self.has_been_run = False

    def findPSDImages(self):
        # Deleting the list of psd file if the function has been run before
        self.all_psd_files = []
        if os.walk(setup_settings.current_folder):
            for subdir, dirs, files in os.walk(setup_settings.current_folder):
                for file_path in files:
                    absolute_file_path = subdir + os.sep + file_path
                    if absolute_file_path.endswith(".psd"):
                        self.all_psd_files.append((file_path, 
                                                   absolute_file_path))

    # Transforms the raw data from PSD tools into readable data
    def colorDataDecoder(self, raw_profile):
        match raw_profile:
            case 0:
                return (_("Bitmap"))
            case 1:
                return (_("Grayscale"))
            case 2:
                return (_("Indexed"))
            case 3:
                return (_("RGB"))
            case 4:
                return (_("CMYK"))
            case 7:
                return (_("Multi Channel"))
            case 8:
                return (_("Duo Tone"))
            case 9:
                return (_("Color Lab"))
            
    def checkLayers(self, psd_file):
        layer_names = ""
        has_hidden_layers = _("No")
        for layer in psd_file:
        # The last layer name doesn't need a linebreak
            if layer == psd_file[-1]:
                layer_names += layer.name
            else:
                layer_names += layer.name + "\n"      
            if layer.visible == False:
                has_hidden_layers = _("Yes")
        return(layer_names, has_hidden_layers)


    # The main function ran by the launch button
    def run(self):
        self.findPSDImages()
        if (self.all_psd_files == []):
            # Displays an error message if no folders are selected
            warning_message = QMessageBox()
            warning_message.setWindowTitle(_("Select Folder"))
            warning_message.setText(_(
                "Please select a folder containing PSD files"))
            warning_message.exec()

        else:
            # Getting all the information that will be displayed
            for file in self.all_psd_files:
                this_psd_path = file[1]
                this_psd = PSDImage.open(this_psd_path)
                image_profile = self.colorDataDecoder(this_psd.color_mode)
                image_width = this_psd.size[0]
                image_height = this_psd.size[1]
                # image_layer_information is used for all layer info
                # it is not directly used in the table
                image_layer_information = self.checkLayers(this_psd)
                image_layer_names = image_layer_information[0]
                image_hidden_layers = image_layer_information[1]
                self.hashed_data.loc[file[1]] = [file[0], 
                    image_width, image_height, image_profile, 
                    image_layer_names, image_hidden_layers]

            # The abstract table is now written in the CreateResultsMenu,
            # Which is the QGridLayout containing the results
            self.filterapply()
            # Has been run is changed to show that the table needs
            # to be translated
            self.has_been_run = True

    # Used to write the data to the table 
    # or to reload after a language change
    def filterapply(self):
            if(analyze_image.all_psd_files == []):
                analyze_image.run()
            else:
                # Reading the filter values
                self.filterread()
                results_table_filtered = ResultsDisplayAbstractTable(
                                        self.filt_data)
                window.results_menu.results_field.this_widget.\
                setModel(results_table_filtered)
                # Resizing the columns of the table
                window.results_menu.results_field.resize_columns()


    def filterremove(self):
        no_filter_data = ResultsDisplayAbstractTable(self.hashed_data)
        window.results_menu.results_field.this_widget.setModel(no_filter_data)
        # Resizing the columns of the table
        window.results_menu.results_field.resize_columns()

    def filterread(self):
            # fetchsettings reads the values stored the the settings tab
            current_settings.fetchsettings()
            # The data is then filtered according to the settings
            # filter_list lists the settings to apply.
            # the order of items follows that of column_names 
            # A copy of the data is made to revert at any moment
            self.filt_data = self.hashed_data

            # Filtering the file name
            self.filt_data = self.filt_data[self.filt_data[_("File Name")]
                                .str.contains(current_settings.file_name_filter)]    

                
            # Filtering the color modes
            self.filt_data = self.filt_data[self.filt_data[_("Color Mode")]
                                            .isin(current_settings.color_modes_filter)]            
            # Filtering the width
            self.filt_data = self.filt_data[self.filt_data[_("Width in px")]
                .between(current_settings.resolution_filter[2], 
                current_settings.resolution_filter[3])]
            # Filtering the height
            self.filt_data = self.filt_data[self.filt_data[_("Height in px")]
                .between(current_settings.resolution_filter[0], 
                current_settings.resolution_filter[1])]

            # Filtering the layer names
            self.filt_data = self.filt_data[self.filt_data[_("Layer list")]
                        .str.contains(current_settings.layer_names_filter)]
            
            # Filtering whether hidden layers should be shown or not
            self.filt_data = self.filt_data[
                self.filt_data[_("Has hidden layers")]
                    .str.contains(current_settings.show_hidden_layers_filter)]            

# The model through which the data of the PSD files is displayed
class ResultsDisplayAbstractTable(QAbstractTableModel):
    def __init__(self, data):
        super().__init__()
        self._data = data

    def data(self, index, role):
        if role == Qt.ItemDataRole.DisplayRole:
            value = self._data.iloc[index.row(), index.column()]
            return str(value)
        
        elif role == Qt.ItemDataRole.TextAlignmentRole:
            return Qt.AlignmentFlag.AlignCenter
    
    def rowCount(self, index):
        return self._data.shape[0]

    def columnCount(self, index):
        return self._data.shape[1]
    
    def headerData(self, section: int, 
                   orientation: Qt.Orientation, role: int):
        if role == Qt.ItemDataRole.DisplayRole:
            if orientation == Qt.Orientation.Horizontal:
                return str(self._data.columns[section])
        

# The following code is linked to the UI
# MainWindow creates the main window and calls each Tab instance    
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        # Setting up the main window
        self.setWindowTitle(_("PSD Batch Editor"))
        # Window Settings
        x, y, w, h = 0, 0, 1500, 800
        self.setGeometry(x, y, w, h)
        layout = QGridLayout()
        widget = QWidget()
        widget.setLayout(layout)
        self.setCentralWidget(widget)
        tabwidget = QTabWidget() 
        # Setting up the resultsmenu
        self.results_menu =  CreateResultsMenu()
        # Setting up the tabs 
        # Filters tab
        self.file_tab = NewTab(tab_layout = layout, 
                    widget_text = _("Filters"), 
                    create_tab = CreateFileFilterTab(CreateTab), 
                    tabs_widget = tabwidget)
        # App Settings
        self.app_settings_tab = NewTab(tab_layout = layout, 
                    widget_text = _("App Settings"), 
                    create_tab = CreateAppsSettingsTab(CreateTab), 
                    tabs_widget = tabwidget)

        
        layout.addLayout(self.results_menu,0,0)
        layout.addWidget(tabwidget,0,1)


# The results Menu that will contain the main data
class CreateResultsMenu(QGridLayout):
    def __init__(self):
        super().__init__()
        self.choose_folder_ui = NewLabel(tab_layout = super(), 
            widget_text = _("Choose your Folder"), col_num = 0, row_num = 0)
        self.openfolder_ui = NewPushButton(tab_layout = super(), 
            widget_text = _("Select Folder"), row_num = 0, col_num =1)
        self.openfolder_ui.this_widget.clicked.connect(
                                                    lambda: self.getFolder())

        self.launchapp_ui = NewPushButton(tab_layout = super(), 
            widget_text = _("Launch"), row_num = 0, col_num =2)
        self.launchapp_ui.this_widget.clicked.connect(
                                                lambda: analyze_image.run())
        self.results_field = NewTableView(tab_layout = super(),
            widget_text = "", row_num=1, col_num=0, row_span=30, col_span=4)
        self.results_field.this_widget.setMinimumWidth(1000)
        
        # Resizing the results to be the whole frame
        super().setColumnStretch(0,3)

    def getFolder(self):
        setup_settings.current_folder = QFileDialog.getExistingDirectory()
        if setup_settings.current_folder != "":
            self.choose_folder_ui.this_widget.setText(
                                            setup_settings.current_folder)
        else:
            self.choose_folder_ui.this_widget.setText(_("Choose your Folder"))

# CreateTab is the Metaclass to create Tabs displayed on the right
class CreateTab(QWidget):
    def __init__(self):
        super().__init__()
        self.tab_layout = QGridLayout()
        self.tab_layout.setSpacing(20)
        self.tab_layout.setContentsMargins(10,10,10,10)
        self.setLayout(self.tab_layout)
        
class CreateFileFilterTab(CreateTab):
    def __init__(self, QWidget):
        super().__init__()

        # defining the row of each widget
        filter_row_indexes = ["file_name_title", "file_name", "",
                                "color_profile_title","color_profile",
                                "",
                                "height_title", "height", 
                                "width_title","width", "",
                                "layer_name_title", "layer_name",
                                "hidden_layers",
                                "layer_show_title", "layer_show",
                                "execution_buttons"]
        
        # minimum height for all rows. titles have shorter rows
        for idx, items in enumerate(filter_row_indexes):
            if "title" in items:
                self.tab_layout.setRowMinimumHeight(idx, 5) 
            elif items == "":
                self.tab_layout.setRowMinimumHeight(idx, 50) 
            elif items == "execution_buttons":
                self.tab_layout.setRowMinimumHeight(idx, 100) 
            else:
                self.tab_layout.setRowMinimumHeight(idx, 10)
        
        # File Name
        NewTitle(tab_layout = self.tab_layout, 
                 widget_text = _("File Name Contains"), 
                 row_num =filter_row_indexes.index("file_name_title"), 
                 col_num = 0, row_span=1, col_span=6)
        
        NewLabel(tab_layout = self.tab_layout, 
                widget_text = _("Select files containing the string"),
                row_num =filter_row_indexes.index("file_name"),
                col_num = 0, col_span = 3 )
        
        self.file_name_filter_ui = NewLineEdit(tab_layout = self.tab_layout,
            row_num =filter_row_indexes.index("file_name"),
            col_num= 3, col_span = 3)
        


        # Color Profile
        NewTitle(tab_layout = self.tab_layout, 
                 widget_text = _("Color Profile"), 
                 row_num =filter_row_indexes.index("color_profile_title"), 
                 col_num = 0, row_span=1, col_span=6)

        # Checkboxes of all the Color Profiles Available
        self.color_profile_widgets_ui = []
        self.color_profile_text = [ _("RGB"),
                                    _("CMYK"),
                                    _("Bitmap"),
                                    _("Grayscale"),
                                    _("Multi Channel"),
                                    _("Duotone")]
        # Automatically populating the options for the color profiles
        for idx, item in enumerate(self.color_profile_text):
            self.color_profile_widgets_ui.append(NewCheckBox(
                 tab_layout = self.tab_layout, 
                 widget_text = item, 
                 row_num = filter_row_indexes.index("color_profile"), 
                 col_num = idx))
        
        # Choosing the image height that will be displayed
        NewTitle(tab_layout = self.tab_layout, 
                 widget_text = _('Height'), 
                 row_num = filter_row_indexes.index("height_title"), 
                 col_num = 0, row_span=1, col_span=6)
        
        NewLabel(tab_layout = self.tab_layout, 
                 widget_text = _('From'), 
                 row_num = filter_row_indexes.index("height"), 
                 col_num = 0)
        
        NewLabel(tab_layout = self.tab_layout, 
                 widget_text = _('To'), 
                 row_num = filter_row_indexes.index("height"), 
                 col_num = 3)
        
        #Spinboxes containing the values
        self.min_height_resolution_ui= NewPxSpinBox(tab_layout = self.tab_layout, 
                        row_num = filter_row_indexes.index("height"),  
                        col_num= 1)
        
        self.max_height_resolution_ui= NewPxSpinBox(tab_layout = self.tab_layout,
                        spin_box_value = 10000,
                        row_num = filter_row_indexes.index("height"),  
                        col_num= 4)
        
        # Choosing the image height that will be displayed
        NewTitle(tab_layout = self.tab_layout, 
                 widget_text = _('Width'), 
                 row_num = filter_row_indexes.index("width_title"),  
                 col_num = 0, row_span=1, col_span=6)
        
        NewLabel(tab_layout = self.tab_layout, 
                 widget_text = _('From'), 
                 row_num = filter_row_indexes.index("width"),  
                 col_num = 0)

        #Spinboxes containing the values
        self.min_width_resolution_ui= NewPxSpinBox(tab_layout = self.tab_layout, 
                row_num = filter_row_indexes.index("width"),   
                col_num= 1)
        
        NewLabel(tab_layout = self.tab_layout, 
                 widget_text = _('To'), 
                 row_num = filter_row_indexes.index("width"),   
                 col_num = 3)
        
        self.max_width_resolution_ui= NewPxSpinBox(tab_layout = self.tab_layout,
                spin_box_value = 10000,
                row_num = filter_row_indexes.index("width"),   
                col_num= 4)
        
        #Gathering all the height and width info
        self.height_width_info = [
            self.min_height_resolution_ui.this_widget,
            self.max_height_resolution_ui.this_widget,
            self.min_width_resolution_ui.this_widget,
            self.max_width_resolution_ui.this_widget,            
        ]

        # Layers have several settings
        NewTitle(tab_layout = self.tab_layout, 
                 widget_text = _("Layer settings"), 
                 row_num =filter_row_indexes.index("layer_name_title"), 
                 col_num = 0, row_span=1, col_span=6)

        # Search by layer name 
        NewLabel(tab_layout = self.tab_layout, 
                widget_text = _("Select files with the following layer name"),
                row_num =filter_row_indexes.index("layer_name"),
                col_num = 0, col_span = 3 )

        self.layer_name_field_ui = NewLineEdit(tab_layout = self.tab_layout,
            row_num =filter_row_indexes.index("layer_name"),
            col_num= 3, col_span = 3 )
        
        # Should hidden layers be shown or not
        NewLabel(tab_layout = self.tab_layout, 
                widget_text = _("Show only files with hidden layers"),
                row_num =filter_row_indexes.index("hidden_layers"),
                col_num = 0, col_span = 3 )

        # This box is unchecked as all files are shown by default   
        self.hidden_layers_ui = NewCheckBox(tab_layout = self.tab_layout,
            row_num =filter_row_indexes.index("hidden_layers"),
            col_num= 4, is_checked= False)
        
        # Should layer names be shown
        NewLabel(tab_layout = self.tab_layout, 
                widget_text = _("Show all layer names"),
                row_num =filter_row_indexes.index("layer_show"),
                col_num = 0, col_span = 3 )
        
        self.layer_names_shown_ui = NewCheckBox(tab_layout = self.tab_layout,
            row_num =filter_row_indexes.index("layer_show"),
            col_num= 4)
        
        # Apply the changes to the current table
        self.apply_filter = NewPushButton(
                tab_layout = self.tab_layout, 
                widget_text = _("Apply Filter"), 
                row_num =filter_row_indexes.index("execution_buttons"),  
                col_num =0, col_span=2)
        
        # Filtering the table according to the settings
        self.apply_filter.this_widget.clicked.connect(
         lambda: analyze_image.filterapply())
        
        # Undoing the settings
        self.remove_filter = NewPushButton(
                tab_layout = self.tab_layout, 
                widget_text = _("Reset all filters"), 
                row_num =filter_row_indexes.index("execution_buttons"),   
                col_num =4, col_span=2)
        # Filtering the table according to the settings
        self.remove_filter.this_widget.clicked.connect(
         lambda: analyze_image.filterremove())
        
        
class CreateAppsSettingsTab(CreateTab):
    def __init__(self, QWidget):
        super().__init__()
        # defining the row of each widget
        sett_row_indexes = ["", "change_lang_title", "change_lang",
                                "about_title", "about", "pad_label"]
        
       # minimum height for all rows. titles have shorter rows
        for idx, items in enumerate(sett_row_indexes):
            if "pad_label" in items:
                self.tab_layout.setRowMinimumHeight(idx, 500) 
        
        # Language change
        NewTitle(tab_layout = self.tab_layout, 
            widget_text = _("Change the language"), 
            row_num = sett_row_indexes.index("change_lang_title"), 
            col_num = 0, row_span=1, col_span=4)

        list_lang_ui = NewComboBox(tab_layout = self.tab_layout, 
            widget_text = [_("English"),_("Japanese")],
            row_num = sett_row_indexes.index("change_lang"),
            col_num =1)
        self.apply_lang_ui = NewPushButton(tab_layout = self.tab_layout, 
            widget_text = _("Change language"), 
            row_num = sett_row_indexes.index("change_lang"),
            col_num =2)
        self.apply_lang_ui.this_widget.clicked.connect(
            lambda: ChangeLanguage(list_lang_ui.currentText()))
        
        # About
        NewTitle(tab_layout = self.tab_layout, 
            widget_text = _("About PSD Batch Editor"), 
            row_num = sett_row_indexes.index("about_title"), 
            col_num = 1, col_span=2)
        
        NewLabel(tab_layout = self.tab_layout, 
            widget_text = _("\nPSD Batch Editor\n\
Copyright (c) 2023-2024 Romain Dereu\n\
https://github.com/RomainDereu/PSD-Batch-Editor\n\n\n\
Contact me for bug reports / feature requests"), 
            row_num = sett_row_indexes.index("about"), 
            col_num = 0, col_span=3)
        
        # Bottom padding for reading claridy
        NewTitle(tab_layout = self.tab_layout, 
                 row_num =sett_row_indexes.index("pad_label"), 
                 col_num = 0)

# NewWidget is the Metaclass to create all widgets
class NewWidget():
    thiswidgetsinfo = namedtuple("thiswidgetsinfo", 
                    ["this_widget", "widget_type", "widget_text", "box_items"])
    global all_widgets_info 
    global all_tabs_list
    

    def __init__(self, row_span=1, col_span=1, widget_text=None,
                **widget_parameters):
        # the parent layout and the text
        self.tab_layout = widget_parameters["tab_layout"]
        # The following have default values since not necessary
        # The position on the layout. Not used for tabs
        # row and col spans default to 1 unless specified otherwise
        self.row_num = widget_parameters.get("row_num")
        self.col_num = widget_parameters.get("col_num")
        # widget_text, row_span and col_span
        # have a default value and are not always necessary
        if(widget_parameters.get("widget_text")):
            self.widget_text = widget_parameters["widget_text"]
        else:
            self.widget_text = widget_text        

        if (widget_parameters.get("row_span")):
            self.col_span = widget_parameters.get("row_span")
        else:
            self.row_span = row_span

        if (widget_parameters.get("col_span")):
            self.col_span = widget_parameters.get("col_span")
        else:
            self.col_span = col_span


        # Only for tabs
        self.create_tab = widget_parameters.get("create_tab")
        self.tabs_widget = widget_parameters.get("tabs_widget")

    # Will be called for each widget instantiation
    def addwidget(self):
        self.tab_layout.addWidget(self.this_widget, 
                                  self.row_num, 
                                  self.col_num,
                                  self.row_span,
                                  self.col_span,
                                  QtCore.Qt.AlignmentFlag.AlignJustify)
    
    def gettingWidgetInfo(self):
        # This function is different is some child classes
        this_widget_info = self.thiswidgetsinfo(
                                     self.this_widget, 
                                     self.widget_type,
                                     self.widget_text,
                                     None)

        all_widgets_info.append(this_widget_info)

    def currentText(self):    
        return self.this_widget.currentText()
    
    def finalSettings(self, widget_type):
        self.widget_type = widget_type
        self.addwidget()
        self.gettingWidgetInfo()



# The following classes are children from New Tab
# There is one for each type of widget     
class NewTab(NewWidget):
    def __init__(self, **widget_parameters):
        super().__init__(**widget_parameters)
        self.this_widget = self.create_tab
        # self.row_num is the layout of the window
        self.tabs_widget.addTab(self.this_widget, _(self.widget_text))
        self.widget_type = "Tab"
        self.gettingWidgetInfo()

    def gettingWidgetInfo(self):
        # In Tabs, col_num holds the tab name and row_num the tab widget
        NewWidget.tabs_widget = self.tabs_widget
        global all_tabs_list
        all_tabs_list.append(self.widget_text)

        this_widget_info = self.thiswidgetsinfo(
                                     self.this_widget, 
                                     self.widget_type,
                                     self.widget_text,
                                     None)

        all_widgets_info.append(this_widget_info)


class NewLabel(NewWidget):
    def __init__(self, **widget_parameters):
        super().__init__(**widget_parameters)
        self.this_widget = QLabel(_(self.widget_text))
        self.finalSettings("QLabel")

# Used for Titles in the right part of the screen
class NewTitle(NewLabel):
        def __init__(self, **widget_parameters):
           super().__init__(**widget_parameters)
           # Objectname is used for the QSS Styling
           self.this_widget.setObjectName("Title")


class NewLineEdit(NewWidget):
    def __init__(self, **widget_parameters):
        super().__init__(**widget_parameters)
        self.this_widget = QLineEdit(_(self.widget_text))

        self.finalSettings("QLineEdit")

class NewCheckBox(NewWidget):
    def __init__(self, is_checked= True, **widget_parameters):
        super().__init__(**widget_parameters)           
        self.this_widget = QCheckBox(_(self.widget_text))
        # The state can be changed with is_checked
        if(is_checked == True):
            self.this_widget.setChecked(True)
        else:
            self.this_widget.setChecked(False) 
        self.finalSettings("QCheckBox")


class NewPushButton(NewWidget):
    def __init__(self, **widget_parameters):
        super().__init__(**widget_parameters)
        self.this_widget = QPushButton(_(self.widget_text))
        self.this_widget.setMinimumWidth(150)
        self.finalSettings("QPushButton")

class NewComboBox(NewWidget):
    def __init__(self, **widget_parameters):
        super().__init__(**widget_parameters)
        self.this_widget = QComboBox()
        for x in self.widget_text:
            self.this_widget.addItem(_(x))
        self.finalSettings("QComboBox")

class NewTableView(NewWidget):
    def __init__(self, **widget_parameters):
        super().__init__(**widget_parameters)
        self.this_widget = QTableView()
        # applying setting changes such as language
        self.finalSettings("QTableView")


    def resize_columns(self):
        self.this_widget.resizeColumnsToContents()
        # The title column is the longest one.
        # Other columns are the same width
        width_title_column = 350
        width_normal_columns = 120
        # the height of the rows
        height_all_rows = 10
        for idx, column in enumerate(analyze_image.column_names):
            if idx == 0:
                self.this_widget.setColumnWidth(idx, width_title_column)
            else:
                self.this_widget.setColumnWidth(idx, width_normal_columns)                
        # Rows need to be taller if layer names are shown
        self.rowstocontent(height_all_rows)

    # the row height can be changed by the user
    def rowstocontent(self, row_height):
        if current_settings.show_layer_names_filter == False:
            for row in range(len(analyze_image.hashed_data.index)):
                self.this_widget.setRowHeight(row, row_height)
        else:
            self.this_widget.resizeRowsToContents()

class NewSpinBox(NewWidget):
    def __init__(self, spin_box_value = 0, **widget_parameters):
        super().__init__(**widget_parameters)
        self.this_widget = QSpinBox()
        # Max value defined for size
        self.this_widget.setMaximum(10000)
        self.this_widget.setValue(spin_box_value)
        self.finalSettings("QSpinBox")

class NewPxSpinBox(NewSpinBox):
        def __init__(self, **widget_parameters):
           super().__init__(**widget_parameters)
           # Max value defined for the GUI Size
           self.this_widget.setMaximum(100000000)
           self.this_widget.setSizePolicy(QSizePolicy.Policy.Expanding, 
                                          QSizePolicy.Policy.Expanding)
           self.this_widget.setSuffix(" px")

# Changes language on the go without needing to reload the application
class ChangeLanguage():
    def __init__(self, wanted_lang_full):
        global all_widgets_info
        # Applying the language (checking for no change first)
        if wanted_lang_full == setup_settings.current_language_name:
            return
            
        elif wanted_lang_full == _("English"):
            setup_settings.setLanguage("en")

        elif wanted_lang_full == _("Japanese"):
            setup_settings.setLanguage("ja")

        # Reloading analyze_image
        # This is necessary since all column names are changed 
        global analyze_image
        if(analyze_image.has_been_run == True):
            analyze_image = AnalyzeImage()
            analyze_image.all_psd_files == []
            analyze_image.run()

        # Replacing all the Widgets containing text
        for x in all_widgets_info:
            if(x.widget_type == "QLabel") or \
            (x.widget_type == "QPushButton") or (x.widget_type == "QCheckBox"):
                x.this_widget.setText(_(x.widget_text))
            elif(x.widget_type == "QComboBox"):
                x.this_widget.clear()
                for value in x.widget_text:
                    x.this_widget.addItem(_(value))
            for count, values in enumerate(all_tabs_list):
                NewWidget.tabs_widget.setTabText(count, _(values))

        # Update of the window title
        if hasattr(window, "show"):
            window.setWindowTitle(_("PSD Batch Editor"))

if __name__ == '__main__':
    _ = gettext.gettext
    setup_settings = SetupSettings()
    setup_settings.setLanguage(setup_settings.current_language_setting)
    # Used for translating and getting widget infos
    all_widgets_info = []
    all_tabs_list = []
    # Loading the UI
    app = QApplication(sys.argv)
    window = MainWindow()
    # Instantiation of the analyze image object
    analyze_image = AnalyzeImage()
    current_settings = CurrentSettings()
    window.show()
    # Calling the style sheet
    with open(setup_settings.qss_sheet_path) as qss_file:
        _style = qss_file.read()
        app.setStyleSheet(_style)
    app.exec()
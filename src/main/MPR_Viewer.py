import sys
import SimpleITK as sitk
import numpy as np
from PyQt5.QtWidgets import QApplication, QVBoxLayout, QHBoxLayout, QGridLayout, QPushButton, QWidget, QFileDialog, \
    QSlider, QStatusBar, QGroupBox, QLabel, QComboBox
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QCursor  # Add this import
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
import matplotlib.pyplot as plt
import pydicom
import os
import vtk
from matplotlib import cm #for providing color maps
from vtkmodules.util import numpy_support
import pydicom  # Reading DICOM files

class MRIViewer(QWidget):
    def __init__(self):
        super().__init__()
        self.data = None
        self.slices = [0, 0, 0]
        self.marked_points = [[], [], []]
        self.zoom_level = 1.0
        self.brightness = 0
        self.contrast = 1
        self.panning = False
        self.pan_start = None
        self.current_colormap = 'gray'
        self.cine_running = False

        self.initUI()

    def initUI(self):
        # Basic UI setup
        self.setWindowTitle("MRI Viewer with Segmentation")
        self.setGeometry(100, 100, 1400, 800)
    
        # Main layout is horizontal to put controls on left
        self.main_layout = QHBoxLayout()
        
        # Create left control panel
        self.control_panel = QWidget()
        self.control_layout = QVBoxLayout()
        self.control_panel.setLayout(self.control_layout)
        self.control_panel.setMaximumWidth(300)
        
        # Load button
        self.load_button = QPushButton('Load MRI Scan', self)
        self.load_button.clicked.connect(self.load_mri)
        self.control_layout.addWidget(self.load_button)
        
        # Play/Pause button
        self.play_pause_button = QPushButton("Play/Pause", self)
        self.play_pause_button.clicked.connect(self.toggle_playback)
        self.control_layout.addWidget(self.play_pause_button)

        # Add Colormap selection dropdown
        colormap_layout = QVBoxLayout()
        colormap_layout.addWidget(QLabel("Colormap"))
        self.colormap_combo = QComboBox()
        self.colormap_combo.addItems(['gray', 'viridis', 'plasma', 'inferno', 'magma', 'cividis', 'jet'])
        self.colormap_combo.currentTextChanged.connect(self.update_colormap)
        colormap_layout.addWidget(self.colormap_combo)
        self.control_layout.addLayout(colormap_layout)

        # Reset button
        self.reset_button = QPushButton("Reset View", self)
        self.reset_button.clicked.connect(self.reset_view)
        self.control_layout.addWidget(self.reset_button)
        
        # Create groups for brightness and contrast controls
        self.create_adjustment_controls()
        
        # Add stretch to push controls to top
        self.control_layout.addStretch()
        
        # Status bar at bottom of control panel
        self.status_bar = QStatusBar()
        self.control_layout.addWidget(self.status_bar)
        
        # Add control panel to main layout
        self.main_layout.addWidget(self.control_panel)
        
        # Create right panel for viewports
        self.viewport_panel = QWidget()
        self.viewport_layout = QVBoxLayout()
        self.viewport_panel.setLayout(self.viewport_layout)
        
        # Initialize canvases for viewports
        self.axial_fig, self.axial_ax = plt.subplots()
        self.coronal_fig, self.coronal_ax = plt.subplots()
        self.sagittal_fig, self.sagittal_ax = plt.subplots()

        # Create canvas for each figure
        self.axial_canvas = FigureCanvas(self.axial_fig)
        self.coronal_canvas = FigureCanvas(self.coronal_fig)
        self.sagittal_canvas = FigureCanvas(self.sagittal_fig)
        # Connect zoom events
        self.axial_canvas.mpl_connect('scroll_event', lambda event: self.wheel_zoom(event, 0))
        self.coronal_canvas.mpl_connect('scroll_event', lambda event: self.wheel_zoom(event, 1))
        self.sagittal_canvas.mpl_connect('scroll_event', lambda event: self.wheel_zoom(event, 2))
       
        # Initialize crosshair positions
        self.crosshair_x = 0
        self.crosshair_y = 0
        self.crosshair_z = 0

        # Connect events for crosshairs
        self.axial_canvas.mpl_connect('motion_notify_event', self.update_crosshairs)
        self.coronal_canvas.mpl_connect('motion_notify_event', self.update_crosshairs)
        self.sagittal_canvas.mpl_connect('motion_notify_event', self.update_crosshairs)

        # Initialize crosshair lines
        self.axial_vline = self.axial_ax.axvline(0, color='r', linestyle='--')
        self.axial_hline = self.axial_ax.axhline(0, color='r', linestyle='--')
        self.coronal_vline = self.coronal_ax.axvline(0, color='r', linestyle='--')
        self.coronal_hline = self.coronal_ax.axhline(0, color='r', linestyle='--')
        self.sagittal_vline = self.sagittal_ax.axvline(0, color='r', linestyle='--')
        self.sagittal_hline = self.sagittal_ax.axhline(0, color='r', linestyle='--')

        # Initialize sliders for each view as horizontal
        self.axial_slider = QSlider(Qt.Horizontal)
        self.coronal_slider = QSlider(Qt.Horizontal)
        self.sagittal_slider = QSlider(Qt.Horizontal)

        # Connect sliders to update functions
        self.axial_slider.valueChanged.connect(self.update_axial_slice)
        self.coronal_slider.valueChanged.connect(self.update_coronal_slice)
        self.sagittal_slider.valueChanged.connect(self.update_sagittal_slice)

        # Create a grid layout for the 3 viewports
        self.grid_layout = QGridLayout()

        # Create a group for each viewport and slider
        self.axial_group = self.create_viewport_group("Axial View", self.axial_canvas, self.axial_slider)
        self.coronal_group = self.create_viewport_group("Coronal View", self.coronal_canvas, self.coronal_slider)
        self.sagittal_group = self.create_viewport_group("Sagittal View", self.sagittal_canvas, self.sagittal_slider)

        # Add groups to the grid layout
        self.grid_layout.addWidget(self.axial_group, 0, 0)
        self.grid_layout.addWidget(self.sagittal_group, 0, 1)
        self.grid_layout.addWidget(self.coronal_group, 1, 0)

        self.viewport_layout.addLayout(self.grid_layout)
        
        # Add viewport panel to main layout
        self.main_layout.addWidget(self.viewport_panel)
        
        # Connect mouse click events to update crosshairs
        self.axial_canvas.mpl_connect('button_press_event', self.update_crosshairs_on_click)
        self.coronal_canvas.mpl_connect('button_press_event', self.update_crosshairs_on_click)
        self.sagittal_canvas.mpl_connect('button_press_event', self.update_crosshairs_on_click)

        # Playback timer
        self.playback_timer = QTimer()
        self.playback_timer.timeout.connect(self.update_slices)
        self.is_playing = False

        self.scan_array = None  # Initialize scan_array
        
        self.setLayout(self.main_layout)

        # Show Volume Rendering button
        render_button = QPushButton("Show Volume Rendering")
        render_button.clicked.connect(self.show_volume_rendering)
        self.control_layout.addWidget(render_button)

        # Set focus policy to handle key events
        self.setFocusPolicy(Qt.StrongFocus)

    def create_adjustment_controls(self):
        """Create brightness and contrast control groups."""
        # Initialize sliders
        self.brightness_sliders = [QSlider(Qt.Horizontal) for _ in range(3)]
        self.contrast_sliders = [QSlider(Qt.Horizontal) for _ in range(3)]
        
        views = ["Axial", "Coronal", "Sagittal"]
        
        # Create a group box for each view's controls
        for i, view in enumerate(views):
            group = QGroupBox(f"{view} View Controls")
            layout = QVBoxLayout()
            
            # Brightness controls - Remap to wider range
            brightness_label = QLabel("Brightness: 0")
            self.brightness_sliders[i].setRange(-150, 150)  # Wider range for more control
            self.brightness_sliders[i].setValue(0)
            self.brightness_sliders[i].valueChanged.connect(lambda value, idx=i, label=brightness_label: self.update_brightness(value, idx, label))
            
            # Contrast controls - Remap to percentage
            contrast_label = QLabel("Contrast")
            self.contrast_sliders[i].setRange(1, 200)  # Range from 1% to 300%
            self.contrast_sliders[i].setValue(100)  # Default 100%
            self.contrast_sliders[i].valueChanged.connect(lambda value, idx=i, label=contrast_label: self.update_contrast(value, idx, label))
            
            # Add to layout
            layout.addWidget(brightness_label)
            layout.addWidget(self.brightness_sliders[i])
            layout.addWidget(contrast_label)
            layout.addWidget(self.contrast_sliders[i])
            
            group.setLayout(layout)
            self.control_layout.addWidget(group)

    def update_brightness(self, value, idx, label):
        """Update brightness value and label."""
        label.setText(f"Brightness: {value}")
        self.update_display(idx)

    def update_contrast(self, value, idx, label):
        """Update contrast value and label."""
        label.setText(f"Contrast: {value}%")
        self.update_display(idx)


    def create_viewport_group(self, title, canvas, slider):
        """Create a group box containing the viewport and horizontal slider."""
        group = QGroupBox(title)
        layout = QVBoxLayout()
        
        # Add the canvas
        layout.addWidget(canvas)
        
        # Create a container for the slider with some padding
        slider_container = QWidget()
        slider_layout = QVBoxLayout()
        slider_layout.addWidget(slider)
        slider_container.setLayout(slider_layout)
        slider_container.setMaximumHeight(50)  # Limit the height of slider container
        
        # Add the slider container below the canvas
        layout.addWidget(slider_container)
        
        group.setLayout(layout)
        return group
    
    def update_crosshairs_on_click(self, event):
        """Update crosshairs based on mouse click in the viewports."""
        if event.inaxes is None or self.scan_array is None:
            return

        # Preserve current view limits
        if event.inaxes == self.axial_ax:
            xlim, ylim = self.axial_ax.get_xlim(), self.axial_ax.get_ylim()
        elif event.inaxes == self.coronal_ax:
            xlim, ylim = self.coronal_ax.get_xlim(), self.coronal_ax.get_ylim()
        elif event.inaxes == self.sagittal_ax:
            xlim, ylim = self.sagittal_ax.get_xlim(), self.sagittal_ax.get_ylim()

        if event.inaxes == self.axial_ax:  # Axial view clicked
            self.crosshair_x = int(event.xdata)
            self.crosshair_y = int(event.ydata)
            self.axial_slider.setValue(self.crosshair_z)
            self.sagittal_slider.setValue(self.crosshair_x)
            self.coronal_slider.setValue(self.crosshair_y)

        elif event.inaxes == self.coronal_ax:  # Coronal view clicked
            self.crosshair_x = int(event.xdata)
            self.crosshair_z = self.scan_array.shape[0] - 1 - int(event.ydata)
            self.sagittal_slider.setValue(self.crosshair_x)
            self.axial_slider.setValue(self.crosshair_z)

        elif event.inaxes == self.sagittal_ax:  # Sagittal view clicked
            self.crosshair_y = int(event.xdata)
            self.crosshair_z = self.scan_array.shape[0] - 1 - int(event.ydata)
            self.coronal_slider.setValue(self.crosshair_y)
            self.axial_slider.setValue(self.crosshair_z)

        # Update the slices in all views
        self.update_all_slices()

        # Restore view limits
        if event.inaxes == self.axial_ax:
            self.axial_ax.set_xlim(xlim)
            self.axial_ax.set_ylim(ylim)
            self.axial_canvas.draw_idle()
        elif event.inaxes == self.coronal_ax:
            self.coronal_ax.set_xlim(xlim)
            self.coronal_ax.set_ylim(ylim)
            self.coronal_canvas.draw_idle()
        elif event.inaxes == self.sagittal_ax:
            self.sagittal_ax.set_xlim(xlim)
            self.sagittal_ax.set_ylim(ylim)
            self.sagittal_canvas.draw_idle()


    def zoom(self, event):
        # Zoom factor
        base_scale = 1.1

        # Get the current axis
        current_axis = event.inaxes

        if current_axis is None:
            return

        # Get the current x and y limits
        cur_xlim = current_axis.get_xlim()
        cur_ylim = current_axis.get_ylim()

        # Get the current cursor position
        xdata = event.xdata
        ydata = event.ydata

        if xdata is None or ydata is None:
            return

        # Calculate zoom factor based on scroll direction
        if event.button == 'up':
            scale_factor = 1 / base_scale
        elif event.button == 'down':
            scale_factor = base_scale
        else:
            scale_factor = 1

        # Set new limits
        new_width = (cur_xlim[1] - cur_xlim[0]) * scale_factor
        new_height = (cur_ylim[1] - cur_ylim[0]) * scale_factor

        rel_x = (cur_xlim[1] - xdata) / (cur_xlim[1] - cur_xlim[0])
        rel_y = (cur_ylim[1] - ydata) / (cur_ylim[1] - cur_ylim[0])

        current_axis.set_xlim([xdata - new_width * (1 - rel_x), xdata + new_width * rel_x])
        current_axis.set_ylim([ydata - new_height * (1 - rel_y), ydata + new_height * rel_y])

        # Redraw the figure
        current_axis.figure.canvas.draw()

    def load_mri(self):
        """Load MRI data from a file."""
        file_path, _ = QFileDialog.getOpenFileName(self, "Open MRI File", "", "NIfTI files (*.nii *.nii.gz);;All files (*)")
        if file_path:
            self.data = sitk.GetArrayFromImage(sitk.ReadImage(file_path))
            self.scan_array = self.data  # Ensure scan_array is also set
            print(f"Loaded MRI data with shape: {self.data.shape}")
            
            # Set slider maximum values based on the scan shape
            self.axial_slider.setMaximum(self.scan_array.shape[0] - 1)  # Axial axis
            self.coronal_slider.setMaximum(self.scan_array.shape[1] - 1)  # Coronal axis
            self.sagittal_slider.setMaximum(self.scan_array.shape[2] - 1)

            # Set initial crosshair positions
            self.crosshair_x = self.scan_array.shape[2] // 2
            self.crosshair_y = self.scan_array.shape[1] // 2
            self.crosshair_z = self.scan_array.shape[0] // 2

            # Update sliders and displays
            self.axial_slider.setValue(self.crosshair_z)
            self.coronal_slider.setValue(self.crosshair_y)
            self.sagittal_slider.setValue(self.crosshair_x)

            self.update_all_slices()

            # Display initial slices in 2D views
            self.update_axial_slice(self.axial_slider.value())
            self.update_coronal_slice(self.coronal_slider.value())
            self.update_sagittal_slice(self.sagittal_slider.value())

            # Update status bar
            self.status_bar.showMessage(f"Loaded {file_path}")
    
    def load_dicom(self, file_path):
        dicom_data = pydicom.dcmread(file_path)
        if 'PixelData' in dicom_data:
            return dicom_data.pixel_array
        else:
            print("DICOM file does not contain pixel data.")
            return None

    def update_crosshairs(self, event):
        if event.button == 1:  # Only update on left-click
            if event.inaxes == self.axial_ax:
                self.crosshair_x = event.xdata
                self.crosshair_y = event.ydata
                self.sagittal_slider.setValue(int(self.crosshair_x))
                self.coronal_slider.setValue(int(self.crosshair_y))
            elif event.inaxes == self.coronal_ax:
                self.crosshair_x = event.xdata
                self.crosshair_z = self.scan_array.shape[0] - 1 - event.ydata
                self.sagittal_slider.setValue(int(self.crosshair_x))
                self.axial_slider.setValue(int(self.crosshair_z))
            elif event.inaxes == self.sagittal_ax:
                self.crosshair_y = event.xdata
                self.crosshair_z = self.scan_array.shape[0] - 1 - event.ydata
                self.coronal_slider.setValue(int(self.crosshair_y))
                self.axial_slider.setValue(int(self.crosshair_z))
            else:
                return

            self.update_all_slices()

    def update_axial_slice(self, value):
        self.crosshair_z = value
        if self.scan_array is not None:
            self.show_axial_slice(self.scan_array, value)

    def update_coronal_slice(self, value):
        self.crosshair_y = value
        if self.scan_array is not None:
            self.show_coronal_slice(self.scan_array, value)

    def update_sagittal_slice(self, value):
        self.crosshair_x = value
        if self.scan_array is not None:
            self.show_sagittal_slice(self.scan_array, value)

    def update_all_slices(self):
        self.update_axial_slice(self.crosshair_z)
        self.update_coronal_slice(self.crosshair_y)
        self.update_sagittal_slice(self.crosshair_x)

    def show_axial_slice(self, scan, slice_index):
        self.axial_ax.clear()
        slice_data = scan[slice_index, :, :]
        self.display_slice(self.axial_ax, slice_data, "Axial View", 0)
        self.axial_ax.set_xlim(self.axial_ax.get_xlim())
        self.axial_ax.set_ylim(self.axial_ax.get_ylim())
        self.axial_vline = self.axial_ax.axvline(self.crosshair_x, color='r', linestyle='--')
        self.axial_hline = self.axial_ax.axhline(self.crosshair_y, color='r', linestyle='--')
        # Add point at crosshair intersection
        self.axial_ax.plot(self.crosshair_x, self.crosshair_y, 'ro', markersize=5)
        self.axial_canvas.draw()

    def show_coronal_slice(self, scan, slice_index):
        if scan is None:
            return
        self.coronal_ax.clear()
        slice_data = scan[:, slice_index, :]
        slice_data_flipped = np.flipud(slice_data)
        self.display_slice(self.coronal_ax, slice_data_flipped, "Coronal View", 1)
        self.coronal_ax.set_xlim(self.coronal_ax.get_xlim())
        self.coronal_ax.set_ylim(self.coronal_ax.get_ylim())
        self.coronal_vline = self.coronal_ax.axvline(self.crosshair_x, color='r', linestyle='--')
        self.coronal_hline = self.coronal_ax.axhline(self.scan_array.shape[0] - 1 - self.crosshair_z, color='r',
                                                     linestyle='--')
        # Add point at crosshair intersection
        self.coronal_ax.plot(self.crosshair_x, self.scan_array.shape[0] - 1 - self.crosshair_z, 'ro', markersize=5)
        self.coronal_canvas.draw()

    def show_sagittal_slice(self, scan, slice_index):
        if scan is None:
            return
        self.sagittal_ax.clear()
        slice_data = scan[:, :, slice_index]
        slice_data_flipped = np.flipud(slice_data)
        self.display_slice(self.sagittal_ax, slice_data_flipped, "Sagittal View", 2)
        self.sagittal_ax.set_xlim(self.sagittal_ax.get_xlim())
        self.sagittal_ax.set_ylim(self.sagittal_ax.get_ylim())
        self.sagittal_vline = self.sagittal_ax.axvline(self.crosshair_y, color='r', linestyle='--')
        self.sagittal_hline = self.sagittal_ax.axhline(self.scan_array.shape[0] - 1 - self.crosshair_z, color='r',
                                                       linestyle='--')
        # Add point at crosshair intersection
        self.sagittal_ax.plot(self.crosshair_y, self.scan_array.shape[0] - 1 - self.crosshair_z, 'ro', markersize=5)
        self.sagittal_canvas.draw()

    def display_slice(self, ax, slice_data, title, idx):
        """Display slice data with remapped brightness and contrast adjustments."""
        if slice_data is None:
            return

        # Normalize the data to 0-1 range
        normalized_data = (slice_data - np.min(slice_data)) / (np.max(slice_data) - np.min(slice_data))
        
        # Get brightness and contrast values
        brightness = self.brightness_sliders[idx].value() / 150.0  # Normalize to [-1, 1]
        contrast = self.contrast_sliders[idx].value() / 100.0  # Convert percentage to multiplier
        
        # Apply contrast first
        contrasted = np.clip((normalized_data - 0.5) * contrast + 0.5, 0, 1)
        
        # Then apply brightness
        adjusted = np.clip(contrasted + brightness, 0, 1)
        
        # Convert to 0-255 range for display
        display_data = (adjusted * 255).astype(np.uint8)
        
        # Show adjusted image with the selected colormap
        ax.imshow(display_data, cmap=self.current_colormap)
        ax.set_title(title)
        ax.axis('on')

    def update_display(self, idx):
        """Update display of the selected view."""
        if idx == 0:
            self.update_axial_slice(self.axial_slider.value())
        elif idx == 1:
            self.update_coronal_slice(self.coronal_slider.value())
        elif idx == 2:
            self.update_sagittal_slice(self.sagittal_slider.value())

    def update_colormap(self, colormap_name):
        self.current_colormap = colormap_name
        self.update_all_slices()

    def toggle_playback(self):
        """Toggle playback of the slices."""
        if self.is_playing:
            self.playback_timer.stop()
            self.play_pause_button.setText("Play")
        else:
            self.playback_timer.start(30)  # Update every 100ms
            self.play_pause_button.setText("Pause")
        self.is_playing = not self.is_playing

    def update_slices(self):
        """Update the slices during playback."""
        if not self.is_playing:
            return

        # Increment sliders and check if max value is reached
        current_axial_value = self.axial_slider.value()
        if current_axial_value < self.axial_slider.maximum():
            self.axial_slider.setValue(current_axial_value + 1)
            self.coronal_slider.setValue(self.coronal_slider.value() + 1)
            self.sagittal_slider.setValue(self.sagittal_slider.value() + 1)
        else:
            # Reset to first slice if max is reached
            self.axial_slider.setValue(0)
            self.coronal_slider.setValue(0)
            self.sagittal_slider.setValue(0)

    def reset_view(self):
        """Reset all controls to their default values."""
        if self.scan_array is not None:
            # Reset crosshair positions to center of volume
            self.crosshair_x = self.scan_array.shape[2] // 2
            self.crosshair_y = self.scan_array.shape[1] // 2
            self.crosshair_z = self.scan_array.shape[0] // 2

            # Reset sliders to center positions
            self.axial_slider.setValue(self.crosshair_z)
            self.coronal_slider.setValue(self.crosshair_y)
            self.sagittal_slider.setValue(self.crosshair_x)

            # Reset brightness and contrast sliders
            for brightness_slider in self.brightness_sliders:
                brightness_slider.setValue(0)  # Reset to default brightness
            
            for contrast_slider in self.contrast_sliders:
                contrast_slider.setValue(100)  # Reset to default contrast (100%)
            
            self.current_colormap = 'gray'  # Reset to default colormap

            # Update all views
            self.update_all_slices()
            
            # Update status bar
            self.status_bar.showMessage("View reset to default")
    
    def wheel_zoom(self, event, view_index):
        """
        Handle zoom events for all three views
        
        Parameters:
        event: matplotlib event object
        view_index: int, indicates which view (0=axial, 1=coronal, 2=sagittal)
        """
        if event.inaxes is None:
            return  # Ensure that the mouse is over an axes

        # Get the current axis based on view_index
        ax = event.inaxes
        
        # Determine zoom factor - smaller factors for smoother zoom
        base_scale = 1.1
        if event.button == 'up':
            scale_factor = base_scale
        elif event.button == 'down':
            scale_factor = 1 / base_scale
        else:
            return

        # Get the current x and y limits
        x_min, x_max = ax.get_xlim()
        y_min, y_max = ax.get_ylim()
        
        # Get mouse location in data coordinates
        x_data = event.xdata
        y_data = event.ydata
        
        # Calculate new limits while maintaining aspect ratio
        x_range = x_max - x_min
        y_range = y_max - y_min
        
        # Calculate relative position of mouse within the view
        rel_x = (x_data - x_min) / x_range
        rel_y = (y_data - y_min) / y_range
        
        # Calculate new ranges
        new_x_range = x_range / scale_factor
        new_y_range = y_range / scale_factor
        
        # Calculate new limits centered on mouse position
        new_x_min = x_data - rel_x * new_x_range
        new_x_max = new_x_min + new_x_range
        new_y_min = y_data - rel_y * new_y_range
        new_y_max = new_y_min + new_y_range
        
        # Set new limits
        ax.set_xlim(new_x_min, new_x_max)
        ax.set_ylim(new_y_min, new_y_max)

        if view_index == 0:  # Axial view
            self.axial_vline.set_xdata([self.crosshair_x, self.crosshair_x])
            self.axial_hline.set_ydata([self.crosshair_y, self.crosshair_y])
            self.axial_canvas.draw_idle()
        elif view_index == 1:  # Coronal view
            self.coronal_vline.set_xdata([self.crosshair_x, self.crosshair_x])
            self.coronal_hline.set_ydata([self.scan_array.shape[0] - 1 - self.crosshair_z,
                                          self.scan_array.shape[0] - 1 - self.crosshair_z])
            self.coronal_canvas.draw_idle()
        elif view_index == 2:  # Sagittal view
            self.sagittal_vline.set_xdata([self.crosshair_y, self.crosshair_y])
            self.sagittal_hline.set_ydata([self.scan_array.shape[0] - 1 - self.crosshair_z,
                                           self.scan_array.shape[0] - 1 - self.crosshair_z])
            self.sagittal_canvas.draw_idle()
    

    def show_volume_rendering(self):
        """Show volume rendering of the MRI scan."""
        if self.data is None:
            print("No data loaded!")
            return

        # Create a VTK image data object
        image_data = vtk.vtkImageData()
        image_data.SetDimensions(self.data.shape[2], self.data.shape[1], self.data.shape[0])

        # Convert the NumPy array to VTK format
        vtk_data_array = numpy_support.numpy_to_vtk(self.data.ravel(), deep=True, array_type=vtk.VTK_FLOAT)
        image_data.GetPointData().SetScalars(vtk_data_array)

        # Set up volume rendering pipeline
        volume_mapper = vtk.vtkGPUVolumeRayCastMapper()
        volume_mapper.SetInputData(image_data)

        volume_property = vtk.vtkVolumeProperty()
        volume_property.ShadeOn()
        volume_property.SetInterpolationTypeToLinear()

        # Set color and opacity functions
        color_function = vtk.vtkColorTransferFunction()
        color_function.AddRGBPoint(np.min(self.data), 0.0, 0.0, 0.0)
        color_function.AddRGBPoint(np.max(self.data), 1.0, 1.0, 1.0)
        volume_property.SetColor(color_function)

        opacity_function = vtk.vtkPiecewiseFunction()
        opacity_function.AddPoint(np.min(self.data), 0.0)
        opacity_function.AddPoint(np.max(self.data), 1.0)
        volume_property.SetScalarOpacity(opacity_function)

        volume = vtk.vtkVolume()
        volume.SetMapper(volume_mapper)
        volume.SetProperty(volume_property)

        # Renderer and window
        renderer = vtk.vtkRenderer()
        renderer.AddVolume(volume)
        renderer.SetBackground(0, 0, 0)

        render_window = vtk.vtkRenderWindow()
        render_window.AddRenderer(renderer)

        render_interactor = vtk.vtkRenderWindowInteractor()
        render_interactor.SetRenderWindow(render_window)

        render_window.Render()
        render_interactor.Start()

    def keyPressEvent(self, event):
        """Handle key press events for panning."""
        step_size = 10  # Define the step size for panning
        if event.key() == Qt.Key_Left:
            self.pan_view(-step_size, 0)
        elif event.key() == Qt.Key_Right:
            self.pan_view(step_size, 0)
        elif event.key() == Qt.Key_Up:
            self.pan_view(0, -step_size)
        elif event.key() == Qt.Key_Down:
            self.pan_view(0, step_size)

    def pan_view(self, dx, dy):
        """Pan the view by the given delta x and delta y."""
        # Get the current mouse position
        mouse_pos = QApplication.instance().widgetAt(QCursor.pos())
        
        if mouse_pos == self.axial_canvas:
            self.pan_specific_view(self.axial_ax, dx, dy)
        elif mouse_pos == self.coronal_canvas:
            self.pan_specific_view(self.coronal_ax, dx, dy)
        elif mouse_pos == self.sagittal_canvas:
            self.pan_specific_view(self.sagittal_ax, dx, dy)

    def pan_specific_view(self, ax, dx, dy):
        """Pan a specific view by the given delta x and delta y."""
        xlim = ax.get_xlim()
        ylim = ax.get_ylim()
        new_xlim = (xlim[0] + dx, xlim[1] + dx)
        new_ylim = (ylim[0] + dy, ylim[1] + dy)
        ax.set_xlim(new_xlim)
        ax.set_ylim(new_ylim)
        ax.figure.canvas.draw_idle()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    viewer = MRIViewer()
    viewer.show()
    sys.exit(app.exec_())


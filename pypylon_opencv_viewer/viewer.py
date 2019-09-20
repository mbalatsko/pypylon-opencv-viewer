import cv2

import ipywidgets as widgets
import warnings
from pypylon.genicam import LogicalErrorException
from pypylon import pylon
import numpy as np
import re
import os
import datetime


class BaslerOpenCVViewer:
    """Easy to use Jupyter notebook interface connecting Basler Pylon images grabbing with openCV image processing.
    Allows to specify interactive Jupyter widgets to manipulate Basler camera features values, grab camera image and at
    once get an OpenCV window on which raw camera output is displayed or you can specify an image processing function,
    which takes on the input raw camera output image and display your own output.
    """

    WIDGET_TYPES = {
        'int': widgets.IntSlider,
        'float': widgets.FloatSlider,
        'bool': widgets.Checkbox,
        'int_text': widgets.BoundedIntText,
        'float_text': widgets.BoundedFloatText,
        'choice_text': widgets.ToggleButtons,
    }

    def __init__(self, camera):
        """

        Parameters
        ----------
        camera : camera
            Basler Pylon opened camera instance.
        """
        if not camera.IsOpen():
            raise ValueError("Camera object {} is closed.".format(camera))
        self._camera = camera

        self._interact_camera_widgets = {}
        self._dependecies = {}
        self._default_user_set = None
        self._disable_updates = False
        self._default_layout = {"width": '100%', "height": '50px', "align_items": "center"}
        self._default_style = {'description_width': 'initial'}
        self._features_layout = []
        self._actions_layout = [("StatusLabel"), ("SaveConfig", "LoadConfig", "ContinuousShot", "SingleShot"), ("UserSet")]
        self._impro_function = None
        self._impro_own_window = False

    def set_camera(self, camera):
        """ Sets Basler Pylon opened camera instance.

        Parameters
        ----------
        camera : camera
            Basler Pylon opened camera instance.

        Returns
        -------
        None
        """
        if not camera.IsOpen():
            raise ValueError()
        self._camera = camera

    def set_configuration(self, configuration):
        """ Give configuration for creating interactive panel inside Jupyter notebook using ipywidgets to control Bastler camera

        Parameters
        ----------
        configuration: dict with items:
            features : list of dicts (required)
                List of widgets configuration stored in
                dictionaries with items:
                    name : str (required)
                        Camera pylon feature name, example: "GainRaw"
                    type : str (required)
                        widget input type, allowed values are {"int", "float", "bool", "int_text", "float_text", "choice_text"}
                    value : number or bool (optional, default: current camera feature value)
                        widget input value
                    max : number (optional, default: camera feature max value)
                        maximum widget input value, only numeric widget types
                    min : number (optional, default: camera feature min value)
                        minimum widget input value, only numeric widget types
                    step : number (optional, default: camera feature increment)
                        step of allowed input value
                    options: list, mandatory for type "choice_text",
                        sets values in list as options for ToggleButtons
                    unit: str (optional, default empty)
                        string shown at the end of label in the form "Label [unit]:"
                    dependency: dict, (optional, default empty)
                        defines how other widgets must be set to be this widget enabled
                    layout : dict (optional, default: {"width": '100%', "height": '50px', "align_items": "center"})
                        values are passed to widget's layout
                    style: dict, (optional, default {'description_width': 'initial'})
                        values are passed to widget's style 

                Example:
                "features": {
                    "name": "GainRaw",
                    "type": "int",
                    "value": 20,
                    "max": 63,
                    "min": 10,
                    "step": 1,
                    "layout": {"width":"99%", "height": "50px") 
                            "style": {"button_width": "90px"}
                    }
            features_layout: list of tuples (optional, default is one widget per row)
                List of features' widgets' name for reordering. Each tuple represents one row
                Example:
                    "features_layout": [
                        ("Height", "Width"), 
                        ("OffsetX", "CenterX"),     
                        ("ExposureAuto", "ExposureTimeAbs"),
                        ("AcquisitionFrameCount", "AcquisitionLineRateAbs")
                    ],
            actions_layout: list of tuples (optional, default is one widget per row)
                List of actions' widgets' name for reordering. Each tuple represents one row.
                Available widgets are StatusLabel, SaveConfig, LoadConfig, ContinuousShot, SingleShot, "UserSet"
                Example: 
                    "action_layout": [
                        ("StatusLabel"), 
                        ("SaveConfig", "LoadConfig", "ContinuousShot", "SingleShot"), 
                        ("UserSet")
                    ]
            default_user_set: string (optional, default is None)
                If value is None, widget for selecting UserSet is displayed. 
                Otherwise is set to given value in ["UserSet1", "UserSet2", "UserSet3"] 
                Example: 
                    "default_user_set": "UserSet3"
        Returns
        -------
        None
        """


        new_interact_camera_widgets = {}
        dependencies = {}
        if(not isinstance(configuration, dict)):
            raise ValueError("Given configuration must be dict type")
        
        if("features" in configuration):
            for feature in configuration["features"]:
                self._process_feature(feature, new_interact_camera_widgets, dependencies)
        else:
            warnings.warn("Configuration does not contain attribute 'features'")
        
        if("features_layout" in configuration):
            self._features_layout = configuration["features_layout"]
        if("actions_layout" in configuration):
            self._actions_layout = configuration["actions_layout"]
        if("default_user_set" in configuration):
            self._default_user_set = configuration["default_user_set"]

        self._add_user_actions_to_widgets()
        self._dependecies = dependencies
        self._interact_camera_widgets = new_interact_camera_widgets

        for trigger in self._dependecies.keys():
            if(trigger not in self._interact_camera_widgets):
                raise ValueError(f"Unknown widget {trigger} listed in dependecies")
            self._interact_camera_widgets[trigger].observe(lambda x, trigger=trigger: self._event_handler_for_dependencies(trigger, x), names='value')
            self._event_handler_for_dependencies(trigger, {"new": self._interact_camera_widgets[trigger].value})

    def _process_feature(self, feature, new_interact_camera_widgets, dependencies):
        widget_kwargs = {}

        if(not isinstance(feature, dict)):
            raise ValueError("Feature is not dict type")
        feature_name = feature.get('name')
        if(feature_name is None):
            raise ValueError("'name' attribute can't be None")
        
        feature_dep = feature.get('dependency', None)
        if(feature_dep is not None):
            if not isinstance(feature_dep, dict):
                raise ValueError("Dependency must be dict type")
            for f, c in feature_dep.items():
                if(f not in dependencies):
                    dependencies[f] = {}
                dependencies[f][feature_name] = c

        type_name = feature.get('type')
        if type_name is None:
            raise ValueError("'type' attribute can't be None")

        widget_obj = self.WIDGET_TYPES.get(type_name)
        if widget_obj is None:
            raise ValueError("Widget type name '{}' is not valid.".format(type_name))
        
        if(type_name in ['int', 'float', 'int_text', 'float_text']): 
            try:
                pylon_feature = getattr(self._camera, feature_name)
            except LogicalErrorException:
                raise ValueError("Camera doesn't have attribute '{}'".format(feature_name)) from None
            widget_kwargs['value'] = feature.get('value', pylon_feature.GetValue())
            step = feature.get('step')
            if step is None:
                try:
                    step = pylon_feature.GetInc().GetValue()
                except:
                    step = 1
            widget_kwargs['step'] = step

            max_value = feature.get('max', pylon_feature.GetMax())
            max_value = (pylon_feature.GetMax(), max_value)[max_value <= pylon_feature.GetMax()]
            widget_kwargs['max'] = max_value

            min_value = feature.get('min', pylon_feature.GetMin())
            min_value = (pylon_feature.GetMin(), min_value)[min_value <= pylon_feature.GetMin()]
            widget_kwargs['min'] = min_value

        elif(type_name == "bool"):
            try:
                pylon_feature = getattr(self._camera, feature_name)
            except LogicalErrorException:
                raise ValueError("Camera doesn't have attribute '{}'".format(feature_name)) from None
            widget_kwargs['value'] = feature.get('value', pylon_feature.GetValue())

        elif(type_name == "choice_text"):
            try:
                pylon_feature = getattr(self._camera, feature_name)
            except LogicalErrorException:
                raise ValueError("Camera doesn't have attribute '{}'".format(feature_name)) from None
            widget_kwargs['value'] = feature.get('value', pylon_feature.GetValue())
            if('options' not in feature or not isinstance(feature['options'], list)):
                raise ValueError("Widget 'choice_text' has mandatory attribute 'options' (list)")
            elif(not feature.get('options')):
                raise ValueError("Attribute 'options' cannot be empty")
            
            widget_kwargs['options'] = feature.get('options')
            if(widget_kwargs['value'] not in widget_kwargs['options']):
                warnings.warn("Current value of feature '{}' is '{}', but this value is not in options.".format(feature_name, widget_kwargs['value']))
                widget_kwargs['value'] = widget_kwargs['options'][0]
        
        elif(type_name == "h_box"):
            content = feature.get('content')
            if(content is None):
                raise ValueError("Attribute 'content' cannot be empty for type 'h_box'")
            for content_feature in content:
                self._process_feature(content_feature, new_interact_camera_widgets, dependencies)

        widget_kwargs['description'] = re.sub('([a-z])([A-Z])', r'\1 \2', feature_name)
        if('unit' in feature):
            widget_kwargs['description'] += " ["+feature['unit']+"]"
        if(type_name != "bool"):
            widget_kwargs['description'] += ":"

        style_dict = feature.get('style')
        if(style_dict is not None):
            if(not isinstance(style_dict, dict)):
                raise ValueError("Attribute 'style' must be dict type")
        else:
            style_dict = {}
        widget_kwargs['style'] = {**self._default_style, **style_dict}
        
        layout_dict = feature.get('layout')
        if(layout_dict is not None):
            if(not isinstance(layout_dict, dict)):
                raise ValueError("Attribute 'layout' must be dict type")
        else:
            layout_dict = {}
        widget_kwargs['layout'] = widgets.Layout(**{**self._default_layout, **layout_dict})

        new_interact_camera_widgets[feature_name] = widget_obj(**widget_kwargs)


    def _event_handler_for_dependencies(self, trigger, change):        
        for feature, condition in self._dependecies[trigger].items():
            self._interact_camera_widgets[feature].disabled = (change['new'] != condition)

    def _button_clicked(self, button):        
        if(button.description == "Load configuration"):
            self._interact_action_widgets["StatusLabel"].value = f"Status: Loading configuration from {self._camera.UserSetSelector.GetValue()}"
            self._camera.UserSetLoad()
            self._update_values_from_camera()
            self._interact_action_widgets["StatusLabel"].value = f"Status: Configuration was loaded from {self._camera.UserSetSelector.GetValue()}"
        elif(button.description == "Save configuration"):
            self._interact_action_widgets["StatusLabel"].value = f"Status: Saving configuration to {self._camera.UserSetSelector.GetValue()}"
            self._camera.UserSetSave()
            self._interact_action_widgets["StatusLabel"].value = f"Status: Configuration was saved to {self._camera.UserSetSelector.GetValue()}"
        elif(button.description == "Continuous shot"):
            self._run_continuous_shot(window_size=self._window_size, image_folder=self._image_folder)
        elif(button.description == "Single shot"):
            self._run_single_shot(window_size=self._window_size, image_folder=self._image_folder)

    def _add_user_actions_to_widgets(self):
        self._interact_action_widgets = {}
        if(self._default_user_set is None):
            self._interact_action_widgets["UserSet"] = widgets.ToggleButtons(options=['UserSet1', 'UserSet2', 'UserSet3'], 
                                                                            value=self._camera.UserSetSelector.GetValue(),
                                                                            description='User Set', 
                                                                            layout=widgets.Layout(**self._default_layout),
                                                                            style={**self._default_style, **{"button_width": "120px"}})
            self._interact_action_widgets["UserSet"].observe(lambda x: self._camera.UserSetSelector.SetValue(x['new']), names='value')
        else:
            self._camera.UserSetSelector.SetValue(self._default_user_set)
        self._interact_action_widgets["LoadConfig"] = widgets.Button(description='Load configuration',
                                                                    button_style='warning', 
                                                                    icon='cloud-upload',
                                                                    tooltip='Load configuration from selected UserSet',
                                                                    layout=widgets.Layout(**self._default_layout),
                                                                    style={**self._default_style, **{"button_width": "100px"}})
        self._interact_action_widgets["LoadConfig"].on_click(self._button_clicked)
        self._interact_action_widgets["SaveConfig"] = widgets.Button(description='Save configuration',
                                                                    button_style='warning',
                                                                    icon='save',
                                                                    tooltip='Save configuration to selected UserSet',
                                                                    layout=widgets.Layout(**self._default_layout),
                                                                    style={**self._default_style, **{"button_width": "100px"}})
        self._interact_action_widgets["SaveConfig"].on_click(self._button_clicked)
        self._interact_action_widgets["ContinuousShot"] = widgets.Button(description='Continuous shot',
                                                                    button_style='success',
                                                                    icon='film',
                                                                    tooltip='Grab and display continuous stream',
                                                                    layout=widgets.Layout(**self._default_layout),
                                                                    style={**self._default_style, **{"button_width": "100px"}})
        self._interact_action_widgets["ContinuousShot"].on_click(self._button_clicked)
        
        self._interact_action_widgets["SingleShot"] = widgets.Button(description='Single shot',
                                                                    button_style='success',
                                                                    icon='image',
                                                                    tooltip='Grab one image and display',
                                                                    layout=widgets.Layout(**self._default_layout),
                                                                    style={**self._default_style, **{"button_width": "100px"}})
        self._interact_action_widgets["SingleShot"].on_click(self._button_clicked)
        self._interact_action_widgets["StatusLabel"] = widgets.Label(value="Status: Connection was established",
                                                                layout=widgets.Layout(**{**self._default_layout}),
                                                                style=self._default_style)

    def set_impro_function(self, impro_function, own_window=False):
        """ Sets image processing function in wich grabbed image would be passed. 

        Parameters
        ----------
        impro_function : function
            Image processing function which takes one positional argument: grabbed OpenCV image.
            Given function must either return processed image (for default own_window=False) 
            or display it using cv2.namedWindow (for own_window=True)
        own_window: bool (default False)
            Specify whenever impro_function opens own cv2.namedWindow

        Returns
        -------
        None
        """
        if impro_function is not None and not callable(impro_function):
            raise ValueError("Object {} is not callable.".format(impro_function))
        self._impro_function = impro_function
        self._impro_own_window = own_window

    def _order_widgets_to_rows(self, rows, wdgts):
        items_rearranged = []
        row_widgets = []
        h_box_layout = widgets.Layout(display='flex', flex_flow='row', justify_items='center', justify_content="flex-start", width='100%')
        for items_in_row in rows:
            for item in items_in_row:
                if(item not in wdgts):
                    break
            else:
                items_rearranged.extend(items_in_row)
                row_widgets.append(widgets.HBox([wdgts[item] for item in items_in_row], layout=h_box_layout))       

        return row_widgets + [w for key, w in wdgts.items() if key not in items_rearranged] 

    def show_interactive_panel(self, window_size=None, image_folder='.'):
        """ Creates Jupyter notebook widgets with all specified features value controls and displays it. 

        Parameters
        ----------
        window_size : tuple (width, height) (optional)
            Size of displaying OpenCV window(raw camera output), if image processing function is not specified.
        image_folder : str
            Path to image folder to save grabbed image
        """
  
        self._window_size = window_size
        self._image_folder = image_folder
        if self._camera is None or not self._camera.IsOpen():
            raise ValueError("Camera object {} is closed.".format(self._camera))
        
        row_widgets = []
        row_widgets.extend(self._order_widgets_to_rows(
                rows=self._actions_layout,
                wdgts=self._interact_action_widgets))
        row_widgets.extend(self._order_widgets_to_rows(
                rows=self._features_layout,
                wdgts=self._interact_camera_widgets))
        
        ui = widgets.VBox(row_widgets,
                layout=widgets.Layout(display='flex', flex_flow='column', align_items='center', align_content="center",  width='100%')
                )
        w = widgets.interactive_output(self._update_values_from_widgets, {**self._interact_camera_widgets})
        display(w, ui)

    def _update_values_from_widgets(self, **kwargs):
        if(not self._disable_updates):
            for widget_name, value in kwargs.items():
                if(not self._interact_camera_widgets[widget_name].disabled):
                    setattr(self._camera, widget_name, value)

    def _update_values_from_camera(self):
        self._disable_updates = True
        for widget_name, widget in self._interact_camera_widgets.items():
            widget.value = getattr(self._camera, widget_name).GetValue()
        self._disable_updates = False

    def _run_continuous_shot(self, grab_strategy=pylon.GrabStrategy_LatestImageOnly,
                                        window_size=None, image_folder='.'):
        self._camera.StopGrabbing()

        # converting to opencv bgr format
        converter = pylon.ImageFormatConverter()
        converter.OutputPixelFormat = pylon.PixelType_BGR8packed
        converter.OutputBitAlignment = pylon.OutputBitAlignment_MsbAligned

        if(not self._impro_own_window):
            cv2.namedWindow('camera_image', cv2.WINDOW_NORMAL | cv2.WINDOW_GUI_NORMAL)
            if(window_size is not None):
                cv2.resizeWindow('camera_image', window_size[0], window_size[1])

        self._camera.StartGrabbing(grab_strategy)
        try:
            while(self._camera.IsGrabbing()):
                grab_result = self._camera.RetrieveResult(5000, pylon.TimeoutHandling_ThrowException)

                if grab_result.GrabSucceeded():
                    # Access the image data
                    image = converter.Convert(grab_result)
                    img = image.GetArray()

                    if(self._impro_own_window):
                        self._impro_function(img)
                    elif(self._impro_function is not None):
                        img = self._impro_function(img)
                        if(not isinstance(img, np.ndarray)):
                            cv2.destroyAllWindows()
                            raise ValueError("The given impro_function must return a numpy array when own_window=False")
                        cv2.imshow('camera_image', img)
                    else:
                        cv2.imshow('camera_image', img)
                    k = cv2.waitKey(1) & 0xFF
                    if(k == ord('s') and self._impro_own_window is False):
                        path = os.path.join(image_folder, 'BaslerGrabbedImage-' +
                            str(int(datetime.datetime.now().timestamp()))+'.png')
                        cv2.imwrite(path, img)
                        self._interact_action_widgets["StatusLabel"].value = f"Status: Grabbed image was saved to {path}"
                    elif k == ord('q'):
                        break
                grab_result.Release()
        finally:
            cv2.destroyAllWindows()
            self._camera.StopGrabbing()

    def _run_single_shot(self, window_size=None, image_folder='.'):
        self._camera.StopGrabbing()

        # converting to opencv bgr format
        converter = pylon.ImageFormatConverter()
        converter.OutputPixelFormat = pylon.PixelType_BGR8packed
        converter.OutputBitAlignment = pylon.OutputBitAlignment_MsbAligned

        if(not self._impro_own_window):
            cv2.namedWindow('camera_image', cv2.WINDOW_NORMAL | cv2.WINDOW_GUI_NORMAL)
            if(window_size is not None):
                cv2.resizeWindow('camera_image', window_size[0], window_size[1])

        grab_result = self._camera.GrabOne(10000)
        if(not grab_result.GrabSucceeded()):
            self._interact_action_widgets["StatusLabel"].value = f"Status: The single shot action has failed."
            cv2.destroyAllWindows()
            return
        else:
            self._interact_action_widgets["StatusLabel"].value = f"Status: The single shot was successfully grabbed."
        image = converter.Convert(grab_result)
        img = image.GetArray()

        if(self._impro_own_window):
            self._impro_function(img)
        elif(self._impro_function is not None):
            img = self._impro_function(img)
            if(not isinstance(img, np.ndarray)):
                cv2.destroyAllWindows()
                raise ValueError("The given impro_function must return a numpy array when own_window=False")
            cv2.imshow('camera_image', img)
        else:
            cv2.imshow('camera_image', img)
        while True:
            k = cv2.waitKey(1) & 0xFF
            if(k == ord('s') and self._impro_own_window is False):
                path = os.path.join(image_folder, 'BaslerGrabbedImage-' +
                    str(int(datetime.datetime.now().timestamp()))+'.png')
                cv2.imwrite(path, img)
                self._interact_action_widgets["StatusLabel"].value = f"Status: The grabbed image was saved to {path}"
            elif k == ord('q'):
                break
        cv2.destroyAllWindows()

    def save_image(self, filename):
        """Saves grabbed image or impro function return value, if specified

        Parameters
        ----------
        filename : str
            Filename of grabbed image

        Returns
        -------
        None
        """
        if self._camera is None or not self._camera.IsOpen():
            raise ValueError("Camera object {} is closed.".format(self._camera))

        converter = pylon.ImageFormatConverter()
        converter.OutputPixelFormat = pylon.PixelType_BGR8packed
        converter.OutputBitAlignment = pylon.OutputBitAlignment_MsbAligned

        grab_result = self._camera.GrabOne(5000)
        image = converter.Convert(grab_result)
        img = image.GetArray()
        if self._impro_function:
            img = self._impro_function(img)
        cv2.imwrite(filename, img)

    def get_image(self):
        """Returns grabbed image or impro function return value, if specified

        Returns
        -------
        openCV image
        """
        if self._camera is None or not self._camera.IsOpen():
            raise ValueError("Camera object {} is closed.".format(self._camera))

        converter = pylon.ImageFormatConverter()
        converter.OutputPixelFormat = pylon.PixelType_BGR8packed
        converter.OutputBitAlignment = pylon.OutputBitAlignment_MsbAligned

        grab_result = self._camera.GrabOne(5000)
        image = converter.Convert(grab_result)
        img = image.GetArray()
        if self._impro_function:
            img = self._impro_function(img)
        return img

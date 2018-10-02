import cv2

from ipywidgets import interact_manual
import ipywidgets as widgets

from pypylon import pylon
from IPython.display import clear_output, display
import re


class BaslerOpenCVViewer:
    """Easy to use Jupyter notebook interface connecting Basler Pylon images grabbing with openCV image processing.
    Allows to specify interactive Jupyter widgets to manipulate Basler camera features values, grab camera image and at
    once get an OpenCV window on which raw camera output is displayed or you can specify an image processing function,
    which takes on the input raw camera output image and display your own output.
    """

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

        self._interact_widgets = {}
        self._impro_function = None

    def set_camera(self, camera):
        """ Sets Basler Pylon opened camera instance.
        Parameters
        ----------
        camera : camera
            Basler Pylon opened camera instance.
        """
        if not camera.IsOpen():
            raise ValueError()
        self._camera = camera

    def set_features(self, features):
        """ Creates Jupyter notebook widgets inside Viewer for pylon camera features values manipulation.

        Parameters
        ----------
        features : list of dicts
            List of widgets configuration
            Dict structure:
              name : str (required)
                Camera pylon feature name, example: "GainRaw"
              type : str (optional, default: "int")
                widget input type, allowed values ["int", "float", "bool", "int_text", "float_text"]
              value : number or bool (optional, default: current camera feature value)
                widget input value
              max : number (optional, default: camera feature max value)
                maximum widget input value, only numeric widget types
              min : number (optional, default: camera feature min value)
                minimum widget input value, only numeric widget types
              step : number (optional, default:camera feature increment, if not exist =1)
                step of allowed input value
              layout : widgets.Layout default: widgets.Layout(width='99%', height='50px')
                Defines a layout that can be expressed using CSS.

            Example:
                {
                    "name": "GainRaw",
                    "type": "int",
                    "value": 20,
                    "max": 63,
                    "min": 10,
                    "step": 1,
                    "layout": widgets.Layout(width='99%', height='50px')
                }
        """

        new_interact_widgets = {}

        for feature in features:
            widget_kwargs = {}

            if not isinstance(feature, dict):
                raise ValueError("Feature is not dict type")
            feature_name = feature.get('name')
            if feature_name is None:
                raise ValueError("'name' attribute can't be None")
            pylon_feature = getattr(self._camera, feature_name)

            widget_kwargs['description'] = re.sub('([a-z])([A-Z])', r'\1 \2', feature_name) + " :"

            type_name = feature.get('type', 'int')
            widget_obj = self._resolve_widget_type(type_name)

            value = feature.get('value', pylon_feature.GetValue())
            widget_kwargs['value'] = value

            if type_name != 'bool':
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

                layout = feature.get('layout', widgets.Layout(width='99%', height='50px'))
                widget_kwargs['layout'] = layout
            style = {'description_width': 'initial'}
            new_interact_widgets[feature_name] = widget_obj(style=style, **widget_kwargs)

        self._interact_widgets = new_interact_widgets

    def set_impro_function(self, impro_function):
        """ Sets image processing function in wich grabbed image would be passed.

        Parameters
        ----------
        impro_function : function
            Image processing function which takes one positional argument: grabbed OpenCV image
        """
        if impro_function is None or not callable(impro_function):
            raise ValueError("Object {} is not callable.".format(impro_function))
        self._impro_function = impro_function

    def run_interaction_continuous_shot(self, grab_strategy=pylon.GrabStrategy_LatestImageOnly,
                                        window_size=None):
        """ Creates Jupyter notebook widgets with all specified features value controls. Push the button 'Run interact'
        to run continuous image grabbing and applying image processing function, if specified. To close openCV windows push 'q'
        button on your keyboard.

        Parameters
        ----------
        grab_strategy : pylon grab strategy
            Pylon image grab strategy
        window_size : tuple (width, height)
            Size of displaying OpenCV window(raw camera output), if image processing function is not specified.
        """
        if self._camera is None or not self._camera.IsOpen():
            raise ValueError("Camera object {} is closed.".format(self._camera))

        if window_size is not None and not len(window_size) == 2:
            raise ValueError("Argument 'window_size' has to be None or tuple of length 2.")

        interact_manual(self._continuous_interaction_function_wrap(grab_strategy, window_size),
                        **self._interact_widgets)

    def run_interaction_single_shot(self, window_size=None):
        """ Creates Jupyter notebook widgets with all specified features value controls. Push the button 'Run interact'
        to grab one image and apply image processing function, if specified. To close openCV windows push 'q' button on
        your keyboard.

        Parameters
        ----------
        window_size : tuple (width, height)
            Size of displaying OpenCV window(raw camera output), if image processing function is not specified.
        """
        if self._camera is None or not self._camera.IsOpen():
            raise ValueError("Camera object {} is closed.".format(self._camera))

        if window_size is not None and not len(window_size) == 2:
            raise ValueError("Argument 'window_size' has to be None or tuple of length 2.")

        interact_manual(self._single_interaction_function_wrap(window_size),
                        **self._interact_widgets)

    def _continuous_interaction_function_wrap(self, grab_strategy, window_size):
        """ Creates Jupyter notebook interact function, which sets up camera with input parameters and runs image
        processing function on continuously grabbing images, if specified, if not displays continuously grabbing raw
        amera images.

        Parameters
        ----------
        grab_strategy : pylon grab strategy
            Pylon image grab strategy
        window_size : tuple (width, height)
            Size of displaying OpenCV window(raw camera output), if image processing function is not specified.
        """
        def camera_configuration(**kwargs):
            self._camera.StopGrabbing()

            converter = pylon.ImageFormatConverter()

            for feature, value in kwargs.items():
                setattr(self._camera, feature, value)

            # converting to opencv bgr format
            converter.OutputPixelFormat = pylon.PixelType_BGR8packed
            converter.OutputBitAlignment = pylon.OutputBitAlignment_MsbAligned

            if self._impro_function is None:
                cv2.namedWindow('camera_image', cv2.WINDOW_NORMAL | cv2.WINDOW_GUI_NORMAL)
                if window_size is not None:
                    cv2.resizeWindow('camera_image', window_size[0], window_size[1])

            self._camera.StartGrabbing(grab_strategy)

            while self._camera.IsGrabbing():
                grab_result = self._camera.RetrieveResult(5000, pylon.TimeoutHandling_ThrowException)

                if grab_result.GrabSucceeded():
                    # Access the image data
                    image = converter.Convert(grab_result)
                    img = image.GetArray()

                    if self._impro_function is not None:
                        self._impro_function(img)
                    else:
                        cv2.imshow('camera_image', img)
                    k = cv2.waitKey(1) & 0xFF
                    if k == ord('q'):
                        break
                    display('Resulting Frame rate: ' + str(round(self._camera.ResultingFrameRateAbs.GetValue(), 1)) + ' fps')
                    clear_output(wait=True)
                grab_result.Release()
            cv2.destroyAllWindows()
            self._camera.StopGrabbing()
            return

        return camera_configuration

    def _single_interaction_function_wrap(self, window_size):
        """ Creates Jupyter notebook interact function, which sets up camera with input parameters and runs image processing
        function on one grabbed image, if specified, if not displays grabbed raw camera image.

        Parameters
        ----------
        window_size : tuple (width, height)
            Size of displaying OpenCV window(raw camera output), if image processing function is not specified.
        """
        def camera_configuration(**kwargs):
            self._camera.StopGrabbing()

            converter = pylon.ImageFormatConverter()

            for feature, value in kwargs.items():
                setattr(self._camera, feature, value)

            # converting to opencv bgr format
            converter.OutputPixelFormat = pylon.PixelType_BGR8packed
            converter.OutputBitAlignment = pylon.OutputBitAlignment_MsbAligned

            if self._impro_function is None:
                cv2.namedWindow('camera_image', cv2.WINDOW_NORMAL | cv2.WINDOW_GUI_NORMAL)
                if window_size is not None:
                    cv2.resizeWindow('camera_image', window_size[0], window_size[1])

            grab_result = self._camera.GrabOne(5000)
            image = converter.Convert(grab_result)
            img = image.GetArray()

            if self._impro_function is not None:
                self._impro_function(img)
            else:
                cv2.imshow('camera_image', img)
            while True:
                k = cv2.waitKey(1) & 0xFF
                if k == ord('q'):
                    break
            cv2.destroyAllWindows()
            return
        return camera_configuration

    def save_image(self, filename, path='.'):
        """Saves grabbed image

        Parameters
        ----------
        filename : str
            Filename of grabbed image
        path : str
            Path to saved image

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
        cv2.imwrite(path + '/' + filename, img)

    def get_image(self):
        """Returns grabbed image

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
        return img


    def _resolve_widget_type(self, widget_type_name):
        """Converts widget type name into widget object

        Parameters
        ----------
        widget_type_name : str
            Widget type name, allowed values ["int", "float", "bool", "int_text", "float_text"]

        Returns
        -------
        Widget class object
        """
        if widget_type_name == 'int':
            return widgets.IntSlider
        elif widget_type_name == 'float':
            return widgets.FloatSlider
        elif widget_type_name == 'bool':
            return widgets.Checkbox
        elif widget_type_name == 'int_text':
            return widgets.BoundedIntText
        elif widget_type_name == 'float_text':
            return widgets.BoundedFloatText
        else:
            raise ValueError("Widget type nae '{}' is not valid.".format(widget_type_name))


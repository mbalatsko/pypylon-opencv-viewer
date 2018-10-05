# Basler PyPylon OpenCV viewer for Jupyter Notebook

[![PyPI version](https://badge.fury.io/py/pypylon-opencv-viewer.svg)](https://badge.fury.io/py/pypylon-opencv-viewer)
[![Downloads](https://pepy.tech/badge/pypylon-opencv-viewer)](https://pepy.tech/project/pypylon-opencv-viewer)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Easy to use Jupyter notebook viewer connecting Basler Pylon images grabbing with OpenCV image processing.
Allows to specify interactive Jupyter widgets to manipulate Basler camera features values, grab camera image and at
once get an OpenCV window on which raw camera output is displayed or you can specify an image processing function,
which takes on the input raw camera output image and display your own output.

## Installation

```bash
pip install pypylon-opencv-viewer
```

## Usage

To start working, launch Jupyter notebook and connect to Basler camera. Here is an example how you can do it:
```python
from pypylon import pylon 

# Pypylon get camera by serial number
serial_number = '22716154'
info = None
for i in pylon.TlFactory.GetInstance().EnumerateDevices():
    if i.GetSerialNumber() == serial_number:
        info = i
        break
else:
    print('Camera with {} serial number not found'.format(serial_number))

# VERY IMPORTANT STEP! To use Basler PyPylon OpenCV viewer you have to call .Open() method on you camera
if info is not None:
    camera = pylon.InstantCamera(pylon.TlFactory.GetInstance().CreateDevice(info)) 
```

Now we can start working with our viewer. Basically we need 3 things: connected camera, features we want to work with
(you can find them in [official Basler documentation](https://docs.baslerweb.com/#t=en%2Ffeatures.htm&rhsearch=sdk), for
 now this library supports only boolean and numeric features) and image processing function we want to apply on grabbing
 images. Image processing function is not a requirement, you don't have to specify one, in this case you'll get raw
 camera output.
 
#### List of features
 
Features - list of dicts.

Dict structure:
1. `name`  - camera pylon feature name, example: "GainRaw" (required)
1. `type` - widget input type, allowed values `int`, `float`, `bool`, `int_text`, `float_text` (optional, default: "int")
1. `value` - widget input value (optional, default: current camera feature value)
1. `max` - maximum widget input value, only numeric widget types (optional, default: camera feature max value)
1. `min` - minimum widget input value, only numeric widget types (optional, default: camera feature min value)
1. `step` - step of allowed input value (optional, default: camera feature increment, if not exist =1)

Example configuration you can see below:

```python
# List of features to create wigets
features = [
    {
        "name": "GainRaw",
        "type": "int"
    },
    {
        "name": "Height",
        "type": "int_text",
        "max": 1000,
        "min": 100,
        "step": "5"
    },
    {
        "name": "Width",
        "type": "int_text",
        "max": 1000,
        "min": 100,
        "step": "5"
    },
    {
        "name": "AcquisitionFrameRateEnable",
        "type": "bool"
    },
    {
        "name": "AcquisitionFrameRateAbs",
        "type": "int",
        "max": 60,
        "min": 10
    }
]
```

#### Example image processing function
Just example image processing function, which negatives the image. Image has to be the only argument in it. 
If you want some image to be shown, you have to do it yourself inside the function. DON'T DESTROY
ALL OpenCV windows or wait for key pressed in it.

```python
import numpy as np
import cv2

def impro(img):
    cv2.namedWindow('1', cv2.WINDOW_NORMAL | cv2.WINDOW_GUI_NORMAL)
    cv2.resizeWindow('1', 1080, 720)
    cv2.imshow("1", np.hstack([img, (255-img)]))
```

#### Viewer
We have prepared all required parts. Now we just set them to the viewer object and launch image grabbing:
`run_interaction_continuous_shot` for continuous or `run_interaction_single_shot` for single shot.
Also you can press 'S' button to save raw camera image to `image_folder`.
```python
from pypylon_opencv_viewer import BaslerOpenCVViewer
    
viewer = BaslerOpenCVViewer(camera)
viewer.set_features(features)
viewer.set_impro_function(impro)
viewer.run_interaction_continuous_shot(image_folder='~/Documents/images')
```

Now we see some similar image, we can setup camera features values. Push `Run interaction` to let it go.
To close OpenCV windows just push 'Q' on your keyboard. You don't have to launch this cell once more to try the same 
procedure with the image, just change wanted values and push the button. That's it!
![Basler OpenCV viewer](https://raw.githubusercontent.com/mbalatsko/pypylon-opencv-viewer/master/images/wiget.PNG)
![Basler OpenCV viewer](https://raw.githubusercontent.com/mbalatsko/pypylon-opencv-viewer/master/images/opened.PNG)

#### Save or get image from camera

In previous steps we set up camera features parameters using widgets. Now we can save camera image on disc or get 
raw openCV image.

```python
# Save image
viewer.save_image('~/Documents/images/grabbed.png')

# Get grabbed image
img = viewer.get_image()
```
